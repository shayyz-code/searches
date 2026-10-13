from functools import lru_cache
from itertools import permutations

import pytest

from searches import SearchLimits, search
from searches.algorithms import ALGORITHMS
from searches.problems import PROBLEMS, get_problem
from searches.problems.bridges import BRIDGES, LOCATIONS, BridgesProblem
from searches.problems.puzzle import SPIRAL_GOAL, STANDARD_GOAL, PuzzleProblem
from searches.problems.tsp import TravellingSalespersonProblem


@pytest.mark.parametrize(
    "name, algorithm, cost",
    [
        ("weighted_graph", "ucs", 6),
        ("romania", "ucs", 418),
        ("romania", "astar", 418),
        ("romania", "greedy", 450),
        ("puzzle_main", "astar", 20),
        ("puzzle_main", "bfs", 20),
        ("tsp", "ucs", 375),
        ("tsp", "astar", 375),
    ],
)
def test_deck_expected_costs(name, algorithm, cost):
    result = search(get_problem(name), algorithm)
    assert result.status == "found"
    assert result.cost == cost


def test_spiral_walkthrough_at_depth_five():
    puzzle = get_problem("puzzle_walkthrough")
    result = search(puzzle, "dfs", limits=SearchLimits(depth_limit=5))
    assert result.status == "found"
    assert result.depth == 5
    assert result.path[-1] == SPIRAL_GOAL


def test_puzzle_validation_and_transitions():
    with pytest.raises(ValueError, match="exactly once"):
        PuzzleProblem((0,) * 9)
    with pytest.raises(ValueError, match="parity"):
        PuzzleProblem((2, 1, 3, 4, 5, 6, 7, 8, 0))
    puzzle = PuzzleProblem((1, 2, 3, 4, 0, 5, 7, 8, 6))
    transitions = list(puzzle.successors(puzzle.initial))
    assert [t.action for t in transitions] == ["up", "left", "down", "right"]
    assert puzzle.heuristic(STANDARD_GOAL) == 0
    assert puzzle.heuristic(puzzle.initial) == 2
    for transition in transitions:
        assert sorted(transition.state) == list(range(9))
        assert sum(a != b for a, b in zip(puzzle.initial, transition.state, strict=True)) == 2
        assert puzzle.heuristic(puzzle.initial) <= 1 + puzzle.heuristic(transition.state)


@pytest.mark.parametrize("start", LOCATIONS)
@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_all_original_bridge_starts_fail(start, algorithm):
    assert search(BridgesProblem(start), algorithm).status == "no_solution"


def test_bridge_edge_identity_and_no_reuse():
    problem = BridgesProblem("i1")
    transitions = list(problem.successors(problem.initial))
    assert len(BRIDGES) == 7
    assert len(transitions) == 5
    parallel = [t for t in transitions if t.state[0] == "rb1"]
    assert [t.action for t in parallel] == ["b2", "b3"]
    assert parallel[0].state != parallel[1].state
    assert "b2" not in [t.action for t in problem.successors(parallel[0].state)]


def test_tsp_optimum_and_admissibility_against_exhaustive_completions():
    problem = TravellingSalespersonProblem()
    optimum = min(
        sum(problem.distance(a, b) for a, b in zip(tour, tour[1:], strict=False))
        for route in permutations("BCDE")
        for tour in [("A", *route, "A")]
    )
    assert optimum == 375

    @lru_cache(None)
    def remaining_cost(state):
        if problem.is_goal(state):
            return 0
        return min(t.cost + remaining_cost(t.state) for t in problem.successors(state))

    stack, visited = [problem.initial], set()
    while stack:
        state = stack.pop()
        if state in visited:
            continue
        visited.add(state)
        assert 0 <= problem.heuristic(state) <= remaining_cost(state)
        stack.extend(t.state for t in problem.successors(state))
    result = search(problem, "astar")
    cities = [state[0] for state in result.path]
    assert cities[0] == cities[-1] == "A"
    assert len(set(cities[:-1])) == 5


def test_all_registered_problems_are_fresh():
    for name in PROBLEMS:
        assert get_problem(name) is not get_problem(name)
