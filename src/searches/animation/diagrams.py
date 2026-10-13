"""Terminal-cell problem views, separate from search problem definitions."""

import json
from dataclasses import dataclass

from rich.text import Text

from searches.problems.bridges import BRIDGES, BridgesProblem
from searches.problems.examples import ROMANIA_EDGES
from searches.problems.puzzle import PuzzleProblem
from searches.problems.tsp import TSP_EDGES, TravellingSalespersonProblem

STYLES = {
    "C": "bold white on dark_red",
    "F": "bold yellow",
    "V": "bright_blue",
    "P": "bold bright_green",
    " ": "dim",
}


def state_label(state, ascii_only=False) -> str:
    def value(item):
        if isinstance(item, frozenset):
            return sorted(item)
        if isinstance(item, tuple):
            return [value(part) for part in item]
        return item

    if isinstance(state, str):
        return state
    return json.dumps(value(state), ensure_ascii=ascii_only, separators=(",", ":"))


class Canvas:
    def __init__(self, width, height, ascii_only=False):
        self.width, self.height = width, height
        self.ascii_only = ascii_only
        self.cells = [[(" ", "") for _ in range(width)] for _ in range(height)]

    def put(self, x, y, text, style=""):
        if not 0 <= y < self.height:
            return
        for i, char in enumerate(text):
            if 0 <= x + i < self.width:
                self.cells[y][x + i] = (char, style)

    def connect(self, a, b, style="dim", directed=False, lane=0):
        x1, y1 = a
        x2, y2 = b
        horizontal, vertical = ("-", "|") if self.ascii_only else ("─", "│")
        middle = (y1 + y2) // 2 + lane
        for y in range(min(y1, middle), max(y1, middle) + 1):
            self.put(x1, y, vertical, style)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.put(x, middle, horizontal, style)
        for y in range(min(y2, middle), max(y2, middle) + 1):
            self.put(x2, y, vertical, style)
        if directed and y1 != y2:
            self.put(
                x2,
                y2 - 1 if y2 > y1 else y2 + 1,
                ("v" if y2 > y1 else "^") if self.ascii_only else ("↓" if y2 > y1 else "↑"),
                style,
            )

    def text(self) -> Text:
        text = Text(no_wrap=True)
        for row in self.cells:
            # Group adjacent cells to reduce terminal writes and SVG spans.
            buffer = []
            current_style = row[0][1]
            for char, style in row:
                if style != current_style:
                    text.append("".join(buffer), current_style)
                    buffer = []
                    current_style = style
                buffer.append(char)
            text.append("".join(buffer), current_style)
            text.append("\n")
        return text


@dataclass(frozen=True)
class GraphLayout:
    positions: dict
    labels: dict
    edges: tuple  # (source, target, cost, edge label)
    directed: bool = True


def graph_layout(name, problem) -> GraphLayout:
    if name == "numbered_graph":
        positions = {
            1: (35, 1),
            2: (13, 6),
            3: (35, 6),
            4: (57, 6),
            5: (5, 12),
            6: (21, 12),
            7: (49, 12),
            8: (65, 12),
        }
    elif name == "letter_graph":
        positions = {
            "A": (38, 1),
            "B": (14, 6),
            "C": (38, 6),
            "D": (62, 6),
            "E": (6, 11),
            "F": (22, 11),
            "G": (34, 11),
            "H": (46, 11),
            "I": (58, 11),
            "J": (70, 11),
            "K": (2, 16),
            "L": (14, 16),
            "M": (26, 16),
            "N": (34, 16),
            "O": (42, 16),
            "P": (50, 16),
            "Q": (62, 16),
            "R": (70, 16),
            "S": (2, 22),
            "T": (14, 22),
            "U": (50, 22),
        }
    elif name == "weighted_graph":
        positions = {
            1: (35, 1),
            2: (12, 6),
            3: (35, 6),
            4: (58, 6),
            5: (5, 13),
            6: (35, 13),
            8: (65, 13),
        }
    elif name == "romania":
        positions = {
            "Arad": (8, 9),
            "Zerind": (8, 5),
            "Oradea": (17, 1),
            "Sibiu": (28, 9),
            "Timisoara": (8, 16),
            "Lugoj": (17, 20),
            "Mehadia": (17, 24),
            "Dobreta": (17, 28),
            "Craiova": (30, 28),
            "Rimnicu Vilcea": (30, 17),
            "Pitesti": (42, 23),
            "Fagaras": (42, 11),
            "Bucharest": (52, 28),
            "Giurgiu": (52, 33),
            "Urziceni": (62, 23),
            "Hirsova": (73, 23),
            "Eforie": (73, 29),
            "Vaslui": (65, 15),
            "Iasi": (65, 8),
            "Neamt": (58, 3),
        }
        labels = {city: city[:3].upper() for city in positions}
        labels.update({"Oradea": "ORA", "Rimnicu Vilcea": "RIM", "Bucharest": "BUC"})
        return GraphLayout(
            positions, labels, tuple((a, b, c, "") for a, b, c in ROMANIA_EDGES), False
        )
    elif isinstance(problem, TravellingSalespersonProblem):
        positions = {"A": (35, 1), "B": (65, 8), "C": (55, 21), "D": (15, 21), "E": (5, 8)}
        return GraphLayout(
            positions,
            {x: x for x in positions},
            tuple((a, b, c, "") for a, b, c in TSP_EDGES),
            False,
        )
    elif isinstance(problem, BridgesProblem):
        positions = {"rb1": (35, 1), "i1": (5, 12), "i2": (65, 12), "rb2": (35, 23)}
        return GraphLayout(
            positions,
            {x: x for x in positions},
            tuple((a, b, 1, edge) for edge, a, b in BRIDGES),
            False,
        )
    else:
        positions = {"S": (12, 1), "A": (12, 8), "B": (45, 8), "G": (45, 17)}
    known = {problem.initial, problem.goal}
    known.update(problem.adjacency)
    known.update(b for neighbors in problem.adjacency.values() for b, _ in neighbors)
    positions = {state: point for state, point in positions.items() if state in known}
    edges = tuple((a, b, c, "") for a, neighbors in problem.adjacency.items() for b, c in neighbors)
    return GraphLayout(positions, {x: str(x) for x in positions}, edges)


def location(problem, state):
    return (
        state[0] if isinstance(problem, (TravellingSalespersonProblem, BridgesProblem)) else state
    )


def render_graph(layout, problem, model, ascii_only=False, replay_index=None) -> Text:
    canvas = Canvas(
        max(x for x, y in layout.positions.values()) + 10,
        max(y for x, y in layout.positions.values()) + 3,
        ascii_only,
    )
    route = model.route()
    if replay_index is not None:
        route = route[: replay_index + 1]
    selected_edges = set()
    for left, right in zip(route, route[1:], strict=False):
        selected_edges.add(
            (location(problem, left.state), location(problem, right.state), right.action)
        )
    solution_edges = set()
    if model.result and model.result.status == "found":
        path = model.result.path
        if replay_index is not None:
            path = path[: replay_index + 1]
        for a, b, action in zip(path, path[1:], model.result.actions, strict=False):
            solution_edges.add((location(problem, a), location(problem, b), action))
    used = model.current.state[1] if isinstance(problem, BridgesProblem) and model.current else 0

    def edge_priority(index_edge):
        _, (a, b, _, edge_label) = index_edge
        return any(
            ((x, y) == (a, b) or (not layout.directed and (x, y) == (b, a)))
            and (not edge_label or action == edge_label)
            for x, y, action in solution_edges | selected_edges
        )

    for index, (a, b, cost, edge_label) in sorted(enumerate(layout.edges), key=edge_priority):

        def contains(edges, a=a, b=b, edge_label=edge_label):
            return any(
                ((x, y) == (a, b) or (not layout.directed and (x, y) == (b, a)))
                and (not edge_label or action == edge_label)
                for x, y, action in edges
            )

        style = (
            "bright_green"
            if contains(solution_edges)
            else "cyan"
            if contains(selected_edges)
            else "dim"
        )
        if isinstance(problem, BridgesProblem) and used & (1 << index):
            style = "cyan"
        # Parallel bridges use visibly distinct horizontal lanes.
        lane = index % 2 if edge_label else 0
        canvas.connect(layout.positions[a], layout.positions[b], style, layout.directed, lane)
        x1, y1 = layout.positions[a]
        x2, y2 = layout.positions[b]
        label = f"{edge_label}:{cost:g}" if edge_label else f"{cost:g}"
        canvas.put((x1 + x2) // 2, (y1 + y2) // 2 + lane, label, style)
    frontier_locations = {location(problem, s) for s in model.frontier_states}
    visited_locations = {location(problem, s) for s in model.visited}
    path_locations = (
        {location(problem, s) for s in path}
        if model.result and model.result.status == "found"
        else set()
    )
    current = location(problem, model.current.state) if model.current else None
    if replay_index is not None:
        current = location(problem, model.result.path[replay_index])
    for state, (x, y) in layout.positions.items():
        marker = (
            "P"
            if state in path_locations
            else "C"
            if state == current
            else "F"
            if state in frontier_locations
            else "V"
            if state in visited_locations
            else " "
        )
        tags = marker + ("C" if marker == "P" and state == current else "")
        label = f"[{tags}:{layout.labels[state]}]"
        canvas.put(max(0, x - len(label) // 2), y, label, STYLES[marker])
    return canvas.text()


def connection_lines(layout, ascii_only=False):
    arrow = "->" if layout.directed else "--"
    for a, b, cost, label in layout.edges:
        yield (
            f"{label + ': ' if label else ''}{layout.labels[a]} {arrow} "
            f"{layout.labels[b]}  cost={cost:g}"
        )
    if any(str(state) != label for state, label in layout.labels.items()):
        yield ""
        yield "Full names:"
        for state, label in layout.labels.items():
            yield f"{label} = {state}"


def is_tile_move(start, end):
    if len(start) != 9 or len(end) != 9:
        return False
    blank_a, blank_b = start.index(0), end.index(0)
    ra, ca = divmod(blank_a, 3)
    rb, cb = divmod(blank_b, 3)
    return (
        abs(ra - rb) + abs(ca - cb) == 1
        and all(
            a == b
            for i, (a, b) in enumerate(zip(start, end, strict=True))
            if i not in (blank_a, blank_b)
        )
        and start[blank_b] == end[blank_a]
    )


def board_text(board, ascii_only=False, target=None, phase=1.0) -> Text:
    canvas = Canvas(19, 10, ascii_only)
    horizontal, vertical = ("-", "|") if ascii_only else ("─", "│")
    for row in range(0, 10, 3):
        canvas.put(0, row, "+" + horizontal * 5 + "+" + horizontal * 5 + "+" + horizontal * 5 + "+")
    for y in range(10):
        for x in (0, 6, 12, 18):
            canvas.put(x, y, "+" if y % 3 == 0 else vertical)
    moving = target is not None and is_tile_move(board, target) and phase < 1
    if target is not None and phase >= 1:
        board = target
    source = target.index(0) if moving else None
    destination = board.index(0) if moving else None
    for i, tile in enumerate(board):
        row, col = divmod(i, 3)
        if tile and i != source:
            canvas.put(col * 6 + 3, row * 3 + 1, str(tile), "bold white")
    if moving:
        sr, sc = divmod(source, 3)
        dr, dc = divmod(destination, 3)
        canvas.put(
            round((sc + (dc - sc) * phase) * 6 + 3),
            round((sr + (dr - sr) * phase) * 3 + 1),
            str(board[source]),
            "bold yellow",
        )
    return canvas.text()


def selected_description(problem, model, ascii_only=False):
    node = model.current
    if node is None:
        return "Initial state"
    text = (
        f"Selected #{node.node_id}: {state_label(node.state, ascii_only)} | "
        f"depth={node.depth} g={node.g:g}"
    )
    if node.f is not None:
        text += f" h={node.h if node.h is not None else '-'} f={node.f:g}"
    if isinstance(problem, TravellingSalespersonProblem):
        text += "\nRoute: " + " -> ".join(n.state[0] for n in model.route())
        text += " | visited cities: " + ", ".join(sorted(node.state[1]))
    elif isinstance(problem, BridgesProblem):
        text += "\nUsed bridges: " + ", ".join(
            e for i, (e, _, _) in enumerate(BRIDGES) if node.state[1] & (1 << i)
        )
    elif isinstance(problem, PuzzleProblem):
        text += "\nBranch selection redraw (not a tile move). Successor previews show legal moves."
    return text
