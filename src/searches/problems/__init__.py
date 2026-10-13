"""Fresh problem instances for each benchmark run."""

from collections.abc import Callable

from searches.core import Problem
from searches.problems.bridges import LOCATIONS, BridgesProblem
from searches.problems.examples import (
    cyclic_graph,
    letter_graph,
    numbered_graph,
    romania,
    unreachable_graph,
    weighted_graph,
    weighted_trap,
)
from searches.problems.puzzle import SPIRAL_GOAL, PuzzleProblem
from searches.problems.tsp import TravellingSalespersonProblem

PROBLEMS: dict[str, Callable[[], Problem]] = {
    "numbered_graph": numbered_graph,
    "letter_graph": letter_graph,
    "weighted_graph": weighted_graph,
    "romania": romania,
    "puzzle_main": lambda: PuzzleProblem((7, 2, 4, 5, 0, 6, 8, 3, 1)),
    "puzzle_walkthrough": lambda: PuzzleProblem((2, 8, 3, 1, 6, 4, 7, 0, 5), SPIRAL_GOAL),
    "puzzle_transition": lambda: PuzzleProblem((1, 4, 3, 7, 0, 6, 5, 8, 2)),
    "tsp": TravellingSalespersonProblem,
    **{
        f"bridges_{location}": lambda location=location: BridgesProblem(location)
        for location in LOCATIONS
    },
    "cyclic_graph": cyclic_graph,
    "unreachable_graph": unreachable_graph,
    "weighted_trap": weighted_trap,
}


def get_problem(name: str) -> Problem:
    try:
        return PROBLEMS[name]()
    except KeyError:
        raise ValueError(f"Unknown problem: {name}; choose from {', '.join(PROBLEMS)}") from None
