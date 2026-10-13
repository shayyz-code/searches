"""Textual walkthrough, with a worker-owned search and UI-owned rendering."""

from queue import Empty
from time import monotonic

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from searches.algorithms import search
from searches.animation.channel import AnimationCancelled, EventChannel
from searches.animation.diagrams import (
    board_text,
    connection_lines,
    graph_layout,
    render_graph,
    selected_description,
    state_label,
)
from searches.animation.model import WalkthroughModel
from searches.problems.puzzle import PuzzleProblem


class PagedPane(Widget, can_focus=True):
    """Viewport-only rows: never instantiate a widget for every search state."""

    BINDINGS = [
        ("up", "up", ""),
        ("down", "down", ""),
        ("pageup", "page_up", ""),
        ("pagedown", "page_down", ""),
        ("home", "home", ""),
        ("end", "end", ""),
        ("left", "left", ""),
        ("right", "right", ""),
    ]

    def __init__(self, title, provider, total, *, two_lines=False, **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.provider = provider
        self.total = total
        self.two_lines = two_lines
        self.row_offset = 0
        self.column = 0

    @property
    def page_size(self):
        return max(1, (self.size.height - 2) // (2 if self.two_lines else 1))

    def render(self):
        total = self.total()
        self.row_offset = max(0, min(self.row_offset, max(0, total - 1)))
        end = min(total, self.row_offset + self.page_size)
        title = f"{self.title_text} {self.row_offset + 1 if total else 0}-{end}/{total}"
        text = Text(no_wrap=True)
        text.append(title + "\n", style="bold cyan")
        for line in self.provider(self.row_offset, self.page_size):
            if isinstance(line, str):
                line = Text(line)
            for part in line.split("\n"):
                text.append_text(part[self.column : self.column + max(1, self.size.width)])
                text.append("\n")
        return text

    def move(self, amount):
        self.row_offset = max(0, min(max(0, self.total() - 1), self.row_offset + amount))
        self.refresh()

    def action_up(self):
        self.move(-1)

    def action_down(self):
        self.move(1)

    def action_page_up(self):
        self.move(-self.page_size)

    def action_page_down(self):
        self.move(self.page_size)

    def action_home(self):
        self.row_offset = 0
        self.refresh()

    def action_end(self):
        self.row_offset = max(0, self.total() - self.page_size)
        self.refresh()

    def action_left(self):
        self.column = max(0, self.column - 5)
        self.refresh()

    def action_right(self):
        self.column += 5
        self.refresh()


class DiagramPane(PagedPane):
    def __init__(self, **kwargs):
        self.content = Text("")
        super().__init__("Diagram / boards", self.lines, self.line_count, **kwargs)

    def lines(self, offset, count):
        return self.content.split("\n")[offset : offset + count]

    def line_count(self):
        return self.content.plain.count("\n") + 1


class SearchFailed(Message):
    def __init__(self, error):
        super().__init__()
        self.error = error


class SearchAnimation(App):
    """One application instance corresponds to one real algorithm execution."""

    ENABLE_COMMAND_PALETTE = False
    CSS = """
    Screen { background: #101826; color: #edf2f7; }
    #title { height: 2; color: #70d6ff; text-style: bold; }
    #selected { height: 3; }
    #body { height: 1fr; layout: horizontal; overflow-y: auto; scrollbar-size: 0 0; }
    #left { width: 64%; height: 1fr; }
    #right { width: 36%; height: 1fr; }
    #diagram { height: 1fr; }
    #connections { height: 5; }
    #stats { height: 6; }
    #frontier, #history { height: 1fr; min-height: 3; }
    #sequence { height: 5; display: none; }
    #legend { height: 1; color: #cad3df; }
    #controls { height: 2; color: #70d6ff; }
    PagedPane, DiagramPane { padding: 0 1; }
    PagedPane:focus, DiagramPane:focus { background: #203047; }
    #body.compact { layout: vertical; }
    #body.compact #left { width: 100%; height: 23; }
    #body.compact #right { width: 100%; height: 30; }
    """
    BINDINGS = [
        ("space", "pause", "Pause/resume"),
        ("n", "step", "Step"),
        ("plus,equals", "faster", "Faster"),
        ("minus", "slower", "Slower"),
        ("f", "fast", "Fast-forward"),
        ("r", "replay", "Replay solution"),
        ("q,ctrl+c", "leave", "Quit"),
    ]

    def __init__(
        self, problem_name, problem, algorithm, *, ascii_only=False, autoplay=True, **search_options
    ):
        super().__init__()
        self.problem_name, self.problem, self.algorithm = problem_name, problem, algorithm
        self.search_options = search_options
        self.ascii_only = ascii_only
        self.model = WalkthroughModel(algorithm)
        self.channel = EventChannel()
        self.paused = not autoplay
        self.fast = False
        self.speed = 2.0
        self.too_small = False
        self.next_due = monotonic() + 0.5
        self.last_frame = monotonic()
        self.phase_started = monotonic()
        self.replay_index = None
        self.error = None
        self.layout = (
            None if isinstance(problem, PuzzleProblem) else graph_layout(problem_name, problem)
        )
        self.connections = (
            list(connection_lines(self.layout, ascii_only))
            if self.layout
            else [
                "Successors are legal blank moves; unrelated selections redraw.",
                "Preview lists every generated successor, including duplicates.",
            ]
        )
        self.dirty = True
        self.batch_processed = 0
        self.last_draw_steps = 0

    def compose(self) -> ComposeResult:
        yield Static(id="title", markup=False)
        yield Static(id="selected", markup=False)
        with Container(id="body"):
            with Container(id="left"):
                yield DiagramPane(id="diagram")
                yield PagedPane(
                    "Connections / costs",
                    self.connection_page,
                    lambda: len(self.connections),
                    id="connections",
                )
            with Container(id="right"):
                yield Static(id="stats", markup=False)
                yield PagedPane(
                    "Frontier (next first)",
                    self.frontier_page,
                    lambda: len(self.model.frontier),
                    two_lines=True,
                    id="frontier",
                )
                yield PagedPane(
                    "Visited (latest first)",
                    self.history_page,
                    lambda: len(self.model.history),
                    two_lines=True,
                    id="history",
                )
                yield PagedPane(
                    "Solution sequence",
                    self.sequence_page,
                    lambda: len(self.model.result.path) if self.model.result else 0,
                    id="sequence",
                )
        yield Static(
            "C current | F frontier | V visited | P solution",
            id="legend",
            markup=False,
        )
        yield Static(
            "Space pause | N step | +/- speed | F fast | R replay | Q quit\n"
            "Tab pane | arrows/PgUp/PgDn scroll | F batches; no events dropped",
            id="controls",
            markup=False,
        )

    def on_mount(self):
        self.on_resize()
        self.search_worker = self.compute()
        self.set_interval(0.02, self.tick)
        self.refresh_views()

    @work(thread=True, exit_on_error=False)
    def compute(self):
        try:
            search(self.problem, self.algorithm, on_event=self.channel, **self.search_options)
        except AnimationCancelled:
            pass
        except Exception as error:
            self.post_message(SearchFailed(error))

    def on_search_failed(self, message):
        self.error = message.error
        self.channel.cancel()
        self.exit()

    def on_unmount(self):
        self.channel.cancel()

    def on_resize(self, event=None):
        if not self.is_mounted:
            return
        size = event.size if event is not None else self.size
        self.too_small = size.width < 60 or size.height < 18
        self.query_one("#body").set_class(size.width < 100, "compact")
        self.query_one("#body").display = not self.too_small
        self.query_one("#controls", Static).update(
            "Resize >=60x18 | Q quit\nSpace pause | N step | F fast"
            if self.too_small
            else "Space pause | N step | +/- speed | F fast | R replay | Q quit\n"
            "Tab pane | arrows/PgUp/PgDn scroll | F batches; no events dropped"
        )
        if self.too_small:
            with self.channel.condition:
                self.channel.credits = 0
        self.dirty = True

    def connection_page(self, offset, count):
        return self.connections[offset : offset + count]

    def node_row(self, rank, node, stale=False):
        first = f"{rank}. #{node.node_id} {state_label(node.state, self.ascii_only)}"
        if stale:
            first += " (stale)"
        second = (
            f"   d={node.depth} g={node.g:g} "
            f"h={node.h if node.h is not None else '-'} "
            f"f={node.f if node.f is not None else '-'}"
        )
        return Text(first + "\n" + second)

    def frontier_page(self, offset, count):
        return [
            self.node_row(offset + i + 1, node, self.model.is_stale(node))
            for i, node in enumerate(self.model.frontier_page(offset, count))
        ]

    def history_page(self, offset, count):
        return [
            self.node_row(len(self.model.history) - index, self.model.history[-1 - index])
            for index in range(offset, min(len(self.model.history), offset + count))
        ]

    def sequence_page(self, offset, count):
        if not self.model.result:
            return []
        result = self.model.result
        return [
            f"{i}. {state_label(result.path[i], self.ascii_only)} "
            f"{result.actions[i - 1] if i else '(start)'}"
            for i in range(offset, min(len(result.path), offset + count))
        ]

    def tick(self):
        now = monotonic()
        deadline = now + 0.008
        previous_steps = self.model.steps
        while monotonic() < deadline:
            try:
                event = self.channel.events.get_nowait()
            except Empty:
                break
            self.model.apply(event)
            if event.kind in ("selected", "expanded"):
                self.phase_started = now
            self.dirty = True
        self.batch_processed = self.model.steps - previous_steps
        if self.model.result:
            if (
                self.replay_index is not None
                and not self.paused
                and not self.too_small
                and now >= self.next_due
            ):
                self.advance_solution(32 if self.fast else 1)
                self.next_due = now + (0.05 if self.fast else max(0.05, 1 / self.speed))
        elif (
            not self.paused
            and not self.too_small
            and self.channel.waiting
            and self.channel.events.empty()
            and now >= self.next_due
        ):
            self.channel.grant(32 if self.fast else 1)
            self.next_due = now + (0.05 if self.fast else max(0.05, 1 / self.speed))
        tile_animation = (
            isinstance(self.problem, PuzzleProblem) and not self.paused and not self.fast
        )
        at_boundary = self.channel.waiting and self.channel.events.empty()
        if (self.dirty or tile_animation) and (
            now - self.last_frame >= 0.05 or (not self.fast and at_boundary and self.dirty)
        ):
            self.refresh_views()
            self.last_frame = now
            self.dirty = False

    def refresh_views(self):
        mode = (
            f"FAST-FORWARD +{self.model.steps - self.last_draw_steps} steps/frame"
            if self.fast
            else "PAUSED"
            if self.paused
            else f"PLAYING target {self.speed:g}/s (one step/frame)"
        )
        outcome = ""
        if self.model.result:
            result = self.model.result
            outcome = f" | {result.status}"
            if result.cutoff_reason:
                outcome += f"/{result.cutoff_reason}"
            if result.cost is not None:
                outcome += f" cost={result.cost:g} depth={result.depth}"
            if self.replay_index is None:
                mode = "COMPLETE - inspect or R replay"
        self.query_one("#title", Static).update(
            f"SEARCH WALKTHROUGH | {self.problem_name} | {self.algorithm.upper()}\n"
            f"{mode}{outcome} | selections={self.model.steps} events={self.model.event_count}"
        )
        description = selected_description(self.problem, self.model, self.ascii_only)
        if self.too_small:
            description = (
                "Terminal too small: resize to at least 60 x 18. Playback waits.\n"
                "Q quits; Space changes pause state."
            )
        elif self.replay_index is not None:
            node = self.model.solution_nodes[self.replay_index]
            description = (
                f"Solution replay: move {self.replay_index}/{len(self.model.result.actions)} "
                f"depth={node.depth} g={node.g:g} h={node.h} f={node.f}\n"
                + state_label(self.model.result.path[self.replay_index], self.ascii_only)
            )
        self.query_one("#selected", Static).update(description)
        stats = self.model.stats
        if stats:
            self.query_one("#stats", Static).update(
                f"Expanded {stats.expanded} | Generated {stats.generated}\n"
                f"Frontier {len(self.model.frontier)} | Peak {stats.peak_frontier}\n"
                f"Retained states {stats.retained_states}\n"
                f"Search-only time {stats.elapsed_seconds:.6f}s\n"
                "UCS f=g; greedy f=h; A* f=g+h\n"
                "Queue includes stale entries until popped."
            )
        if self.layout:
            content = render_graph(
                self.layout,
                self.problem,
                self.model,
                self.ascii_only,
                replay_index=self.replay_index,
            )
        else:
            content = self.puzzle_content()
        self.query_one("#diagram", DiagramPane).content = content
        for pane in self.query(PagedPane):
            pane.refresh()
        self.query_one("#sequence").display = bool(
            self.model.result and self.model.result.status == "found"
        )
        self.last_draw_steps = self.model.steps

    def puzzle_content(self):
        model = self.model
        board = model.current.state if model.current else self.problem.initial
        phase = (
            1.0
            if self.paused or self.fast
            else min(1.0, max(0.0, (monotonic() - self.phase_started) / 0.15))
        )
        if self.replay_index is not None:
            board = model.result.path[self.replay_index]
            previous = model.result.path[max(0, self.replay_index - 1)]
            selected = board_text(previous, self.ascii_only, board, phase)
        else:
            selected = board_text(board, self.ascii_only)
        content = Text("Selected board          Goal board\n", style="bold cyan")
        goal = board_text(self.problem.goal, self.ascii_only)
        for left, right in zip(selected.split("\n"), goal.split("\n"), strict=True):
            content.append_text(left)
            content.append("    ")
            content.append_text(right)
            content.append("\n")
        if model.transitions and self.replay_index is None:
            # Every generated board stays available below the animated preview.
            preview_index = int(max(0, monotonic() - self.phase_started) / 0.18) % len(
                model.transitions
            )
            transition = model.transitions[preview_index]
            content.append(
                f"Legal successor preview: {transition.target.action} ({transition.disposition})\n",
                style="bold yellow",
            )
            preview_phase = (
                1
                if self.fast or self.paused
                else ((monotonic() - self.phase_started) % 0.18) / 0.15
            )
            content.append_text(
                board_text(board, self.ascii_only, transition.target.state, min(1, preview_phase))
            )
            for event in model.transitions:
                content.append(
                    f"{event.target.action}: {state_label(event.target.state, self.ascii_only)} "
                    f"({event.disposition})\n"
                )
        return content

    def action_pause(self):
        self.paused = not self.paused
        if self.paused:
            with self.channel.condition:
                self.channel.credits = 0
        else:
            self.next_due = monotonic()
        self.dirty = True

    def action_step(self):
        self.paused = True
        self.fast = False
        if self.too_small:
            return
        if self.replay_index is not None:
            self.advance_solution(1)
        elif self.model.result is None:
            with self.channel.condition:
                self.channel.credits = 0
            self.channel.grant(1)
        self.dirty = True

    def action_faster(self):
        self.speed = min(64, self.speed * 2)
        self.dirty = True

    def action_slower(self):
        self.speed = max(0.25, self.speed / 2)
        self.dirty = True

    def action_fast(self):
        self.fast = not self.fast
        self.paused = False
        self.next_due = monotonic()
        self.dirty = True

    def action_replay(self):
        if self.model.result and self.model.result.status == "found":
            self.replay_index = 0
            self.paused = False
            self.fast = False
            self.phase_started = monotonic()
            self.next_due = monotonic() + 1 / self.speed
            self.dirty = True

    def advance_solution(self, amount):
        self.replay_index = min(len(self.model.result.path) - 1, self.replay_index + amount)
        self.phase_started = monotonic()
        if self.replay_index == len(self.model.result.path) - 1:
            self.paused = True
        self.dirty = True

    def action_leave(self):
        self.channel.cancel()
        self.exit(self.model.result)


def run_animation(problem_name, problem, algorithm, *, ascii_only=False, **options):
    app = SearchAnimation(problem_name, problem, algorithm, ascii_only=ascii_only, **options)
    result = app.run()
    if app.error is not None:
        raise app.error
    if result is None:
        raise AnimationCancelled()
    return result
