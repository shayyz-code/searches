import subprocess
import sys
from time import monotonic

import pytest

from searches import SearchLimits, search
from searches.animation.app import PagedPane, SearchAnimation
from searches.animation.diagrams import (
    board_text,
    connection_lines,
    graph_layout,
    is_tile_move,
    render_graph,
    state_label,
)
from searches.animation.model import WalkthroughModel
from searches.problems import PROBLEMS, get_problem


async def until(pilot, predicate, timeout=5):
    deadline = monotonic() + timeout
    while not predicate():
        if monotonic() >= deadline:
            pytest.fail("Timed out waiting for walkthrough state")
        await pilot.pause(0.02)


@pytest.mark.asyncio
async def test_controls_completion_and_replay():
    app = SearchAnimation("letter_graph", get_problem("letter_graph"), "bfs", autoplay=False)
    async with app.run_test(size=(132, 44)) as pilot:
        await until(pilot, lambda: app.channel.waiting)
        assert app.model.steps == 0
        await pilot.press("n")
        await until(pilot, lambda: app.model.steps == 1 and app.channel.waiting)
        await pilot.pause(0.1)
        assert app.model.steps == 1 and app.paused
        await pilot.press("equals")
        assert app.speed == 4
        await pilot.press("minus")
        assert app.speed == 2
        await pilot.press("space")
        await until(pilot, lambda: app.model.steps >= 2)
        await pilot.press("space")
        assert app.paused
        await pilot.press("f")
        await until(pilot, lambda: app.model.result is not None)
        assert app.model.result.path == ("A", "C", "H", "O")
        assert app.model.result.cost == 3
        assert app.channel.max_buffered <= app.channel.capacity
        assert app.is_running
        await pilot.press("r")
        assert app.replay_index == 0
        await pilot.press("n")
        assert app.replay_index == 1
        await pilot.press("q")
    assert app.return_value.status == "found"


@pytest.mark.asyncio
async def test_resize_scroll_and_early_quit():
    app = SearchAnimation(
        "romania", get_problem("romania"), "astar", autoplay=False, ascii_only=True
    )
    async with app.run_test(size=(132, 44)) as pilot:
        await until(pilot, lambda: app.channel.waiting)
        pane = app.query_one("#diagram", PagedPane)
        pane.focus()
        await pilot.press("down", "right")
        offsets = pane.row_offset, pane.column
        await pilot.resize_terminal(80, 24)
        await pilot.pause()
        assert app.query_one("#body").has_class("compact")
        assert (pane.row_offset, pane.column) == offsets
        await pilot.resize_terminal(40, 12)
        await pilot.pause()
        assert app.too_small
        await pilot.press("n")
        assert app.model.steps == 0
        await pilot.resize_terminal(132, 44)
        await pilot.pause()
        assert not app.too_small and app.paused
        await pilot.press("q")
    assert app.return_value is None
    assert app.channel.cancelled
    assert all(worker.is_finished for worker in app.workers)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,algorithm,limits,status",
    [
        ("puzzle_walkthrough", "dfs", SearchLimits(depth_limit=5), "found"),
        ("bridges_i1", "ucs", SearchLimits(), "no_solution"),
        ("tsp", "astar", SearchLimits(), "found"),
        ("weighted_graph", "ucs", SearchLimits(max_expansions=1), "cutoff"),
    ],
)
async def test_problem_walkthroughs(name, algorithm, limits, status):
    app = SearchAnimation(name, get_problem(name), algorithm, autoplay=False, limits=limits)
    async with app.run_test(size=(132, 44)) as pilot:
        await until(pilot, lambda: app.channel.waiting)
        await pilot.press("f")
        await until(pilot, lambda: app.model.result is not None)
        assert app.model.result.status == status
        if status == "cutoff":
            assert app.model.result.cutoff_reason == "expansions"
        assert len(app.model.history) == len(app.model.result.visit_order)
        await pilot.press("q")


@pytest.mark.asyncio
async def test_large_search_processes_all_events_and_can_pause():
    # Real puzzle exploration plus a bounded synthetic stress case for controls.
    graph = get_problem("puzzle_main")
    limits = SearchLimits(max_expansions=1500)
    expected = []
    plain = search(graph, "bfs", limits=limits, on_event=expected.append)
    app = SearchAnimation("puzzle_main", graph, "bfs", autoplay=False, limits=limits)
    async with app.run_test(size=(132, 44)) as pilot:
        await until(pilot, lambda: app.channel.waiting)
        await pilot.press("f")
        await until(pilot, lambda: app.model.steps > 64)
        await pilot.press("space")
        await until(pilot, lambda: app.channel.waiting and app.channel.events.empty())
        count = app.model.steps
        await pilot.pause(0.1)
        assert app.model.steps == count
        await pilot.press("n")
        await until(pilot, lambda: app.model.steps == count + 1)
        await pilot.press("f")
        await until(pilot, lambda: app.model.result is not None, timeout=15)
        assert app.model.result.path == plain.path
        assert app.model.event_count == len(expected)
        assert len(app.model.history) == 1501
        assert app.channel.max_buffered <= 256
        await pilot.press("q")


@pytest.mark.asyncio
async def test_normal_playback_displays_each_step_at_high_speed(monkeypatch):
    app = SearchAnimation("numbered_graph", get_problem("numbered_graph"), "bfs", autoplay=False)
    frames = []
    original = app.refresh_views

    def capture():
        frames.append(app.model.steps)
        original()

    monkeypatch.setattr(app, "refresh_views", capture)
    async with app.run_test(size=(132, 44)) as pilot:
        await until(pilot, lambda: app.channel.waiting)
        app.speed = 64
        await pilot.press("space")
        await until(pilot, lambda: app.model.result is not None)
        await pilot.pause(0.1)
        assert set(range(9)) <= set(frames)
        assert not app.fast
        await pilot.press("q")


@pytest.mark.asyncio
async def test_worker_error_restores_app_and_preserves_error():
    app = SearchAnimation(
        "romania", get_problem("romania"), "bfs", limits=SearchLimits(depth_limit=3)
    )
    async with app.run_test(size=(132, 44)) as pilot:
        await until(pilot, lambda: app.error is not None)
        assert isinstance(app.error, ValueError)
    assert app.channel.cancelled


@pytest.mark.parametrize("name", PROBLEMS)
def test_all_diagrams_and_ascii(name):
    problem = get_problem(name)
    model = WalkthroughModel("astar")
    search(problem, "astar", limits=SearchLimits(max_expansions=5), on_event=model.apply)
    if name.startswith("puzzle"):
        content = board_text(problem.initial, True)
        for transition in problem.successors(problem.initial):
            assert is_tile_move(problem.initial, transition.state)
            assert board_text(problem.initial, True, transition.state, 0.5).plain != content.plain
    else:
        layout = graph_layout(name, problem)
        content = render_graph(layout, problem, model, True)
        lines = list(connection_lines(layout, True))
        assert len(layout.edges) > 0
        assert all("cost=" in line for line in lines[: len(layout.edges)])
        if name == "romania":
            assert len(layout.positions) == 20
        if name.startswith("bridges"):
            assert len(layout.edges) == 7
    content.plain.encode("ascii")


def test_composite_states_and_nonadjacent_boards():
    assert state_label(("A", frozenset({"C", "A", "B"}))) == '["A",["A","B","C"]]'
    assert not is_tile_move((1, 2, 3, 4, 5, 6, 7, 8, 0), (0, 1, 2, 3, 4, 5, 6, 7, 8))


def test_plain_compare_does_not_import_animation():
    code = (
        "from searches.comparisons import compare; import sys; "
        "compare(['weighted_graph'], repeats=1); "
        "assert 'textual' not in sys.modules; "
        "assert 'searches.animation.app' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
