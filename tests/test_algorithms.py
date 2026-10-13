"""Behavioral checks against explicit paths and independent shortest-path oracles."""

from itertools import count

import pytest

from searches import SearchLimits, Transition, search
from searches.algorithms import ALGORITHMS
from searches.problems import get_problem
from searches.problems.graph import GraphProblem


def assert_valid_path(problem, result):
    assert result.path[0] == problem.initial
    assert problem.is_goal(result.path[-1])
    total = 0
    for a, action, b in zip(result.path, result.actions, result.path[1:], strict=False):
        edges = [t for t in problem.successors(a) if t.state == b and t.action == action]
        assert edges
        total += edges[0].cost
    assert result.cost == total
    assert result.depth == len(result.path) - 1


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_start_at_goal(algorithm):
    result = search(GraphProblem({}, "G", "G"), algorithm, limits=SearchLimits(max_expansions=0))
    assert result.status == "found"
    assert result.path == ("G",)
    assert result.cost == 0
    assert result.stats.expanded == 0


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_cycles_and_unreachable(algorithm):
    problem = get_problem("cyclic_graph")
    result = search(problem, algorithm)
    assert result.status == "found"
    assert_valid_path(problem, result)
    assert search(get_problem("unreachable_graph"), algorithm).status == "no_solution"


@pytest.mark.parametrize(
    "algorithm, expected",
    [
        ("bfs", [1, 2, 3, 4, 5, 6, 7, 8]),
        ("dfs", [1, 2, 5, 6, 3, 4, 7, 8]),
    ],
)
def test_traversal_order(algorithm, expected):
    result = search(get_problem("numbered_graph"), algorithm, traversal=True)
    assert result.status == "traversed"
    assert result.visit_order == expected


def test_letter_graph_order_and_duplicate_suppression():
    result = search(get_problem("letter_graph"), "bfs")
    assert result.visit_order == list("ABCDEFGHIJKLMNO")
    assert result.path == ("A", "C", "H", "O")
    dfs = search(get_problem("letter_graph"), "dfs")
    assert dfs.visit_order == list("ABEKSLTFMCGNHO")
    assert len(result.visit_order) == len(set(result.visit_order))


@pytest.mark.parametrize("algorithm", ["ucs", "astar"])
def test_replaces_cost_and_skips_stale_entries(algorithm):
    graph = GraphProblem(
        {"S": (("A", 10), ("B", 1)), "B": (("A", 1),), "A": (("G", 20),)}, "S", "G"
    )
    result = search(graph, algorithm)
    assert result.cost == 22
    assert result.path == ("S", "B", "A", "G")
    assert result.visit_order.count("A") == 1


def test_astar_reopens_with_admissible_inconsistent_heuristic():
    graph = GraphProblem(
        {"S": (("A", 2), ("B", 2)), "A": (("C", 2),), "B": (("C", 1),), "C": (("G", 5),)},
        "S",
        "G",
        {"S": 0, "A": 0, "B": 6, "C": 0, "G": 0},
    )
    result = search(graph, "astar")
    assert result.cost == 8
    assert result.visit_order.count("C") == 2
    assert_valid_path(graph, result)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_nonorderable_states_zero_cost_and_equal_ties(algorithm):
    start, a, b, goal = (frozenset({x}) for x in "SABG")
    graph = GraphProblem({start: ((a, 0), (b, 0)), a: ((goal, 0),)}, start, goal)
    result = search(graph, algorithm)
    assert result.visit_order[1] == a
    assert result.cost == 0


def test_dfs_shallower_revisit_and_depth_boundary():
    graph = GraphProblem(
        {
            "S": (("A", 1), ("D", 1)),
            "A": (("B", 1),),
            "B": (("X", 1),),
            "D": (("X", 1),),
            "X": (("G", 1),),
        },
        "S",
        "G",
    )
    result = search(graph, "dfs", limits=SearchLimits(depth_limit=3))
    assert result.path == ("S", "D", "X", "G")
    assert result.visit_order.count("X") == 2
    cutoff = search(graph, "dfs", limits=SearchLimits(depth_limit=2))
    assert (cutoff.status, cutoff.cutoff_reason) == ("cutoff", "depth")
    leaf = search(GraphProblem({}, "S", "G"), "dfs", limits=SearchLimits(depth_limit=0))
    assert leaf.status == "no_solution"


def test_expansion_and_time_cutoffs(monkeypatch):
    graph = get_problem("letter_graph")
    cutoff = search(graph, "bfs", limits=SearchLimits(max_expansions=2))
    assert (cutoff.status, cutoff.cutoff_reason) == ("cutoff", "expansions")
    assert cutoff.stats.expanded == 2
    ticks = count()
    monkeypatch.setattr("searches.algorithms.perf_counter", lambda: float(next(ticks)))
    cutoff = search(graph, "bfs", limits=SearchLimits(max_seconds=0.5))
    assert (cutoff.status, cutoff.cutoff_reason) == ("cutoff", "time")


def test_trace_caps_and_frontier_order():
    result = search(
        get_problem("numbered_graph"),
        "dfs",
        traversal=True,
        trace=True,
        trace_limit=3,
        snapshot_limit=2,
    )
    assert len(result.trace) == 3
    assert result.trace_truncated
    assert result.trace[1].frontier == (3, 4)
    assert all(len(e.frontier) <= 2 and len(e.visited) <= 2 for e in result.trace)
    assert result.trace[2].frontier_total > len(result.trace[2].frontier)


@pytest.mark.parametrize("cost", [-1, float("nan"), float("inf")])
@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_invalid_costs_rejected(cost, algorithm):
    class BadProblem:
        initial = "S"

        def successors(self, state):
            yield Transition("bad", "G", cost)

        def is_goal(self, state):
            return state == "G"

        def heuristic(self, state):
            return 0

    with pytest.raises(ValueError, match="Step costs"):
        search(BadProblem(), algorithm)


@pytest.mark.parametrize("h", [-1, float("nan"), float("inf")])
def test_invalid_heuristic_rejected(h):
    graph = GraphProblem({}, "S", "G")
    graph.heuristics["S"] = h
    with pytest.raises(ValueError, match="Heuristics"):
        search(graph, "astar")


def test_argument_validation():
    graph = get_problem("numbered_graph")
    with pytest.raises(ValueError):
        search(graph, "unknown")
    with pytest.raises(ValueError):
        search(graph, "bfs", limits=SearchLimits(depth_limit=1))
    with pytest.raises(ValueError):
        search(graph, "astar", traversal=True)
    with pytest.raises(ValueError):
        SearchLimits(max_seconds=0)


def test_shortest_paths_against_independent_floyd_warshall():
    # Directed graph includes zero costs, ties, cheaper detours, and a cycle.
    adjacency = {0: ((1, 8), (2, 1)), 1: ((3, 0),), 2: ((1, 1), (3, 9)), 3: ((0, 7), (4, 2)), 4: ()}
    distance = {(a, b): 0 if a == b else float("inf") for a in adjacency for b in adjacency}
    for a, edges in adjacency.items():
        for b, cost in edges:
            distance[a, b] = min(distance[a, b], cost)
    for k in adjacency:
        for a in adjacency:
            for b in adjacency:
                distance[a, b] = min(distance[a, b], distance[a, k] + distance[k, b])
    for a in adjacency:
        for b in adjacency:
            graph = GraphProblem(adjacency, a, b)
            for algorithm in ("ucs", "astar"):
                result = search(graph, algorithm)
                if distance[a, b] == float("inf"):
                    assert result.status == "no_solution"
                else:
                    assert result.cost == distance[a, b]
                    assert_valid_path(graph, result)
