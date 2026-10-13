"""Ordered directed or undirected state-space graphs."""

from collections.abc import Iterable, Mapping
from math import isfinite

from searches.core import State, Transition


class GraphProblem:
    def __init__(
        self,
        adjacency: Mapping[State, Iterable[tuple[State, float]]],
        initial: State,
        goal: State | None,
        heuristics: Mapping[State, float] | None = None,
    ):
        self.adjacency = {state: tuple(edges) for state, edges in adjacency.items()}
        self.initial = initial
        self.goal = goal
        self.heuristics = dict(heuristics or {})
        for edges in self.adjacency.values():
            for _, cost in edges:
                if not isfinite(cost) or cost < 0:
                    raise ValueError("Graph costs must be finite and nonnegative")
        for h in self.heuristics.values():
            if not isfinite(h) or h < 0:
                raise ValueError("Heuristics must be finite and nonnegative")

    def successors(self, state: State):
        for target, cost in self.adjacency.get(state, ()):
            yield Transition(str(target), target, cost)

    def is_goal(self, state: State) -> bool:
        return self.goal is not None and state == self.goal

    def heuristic(self, state: State) -> float:
        return self.heuristics.get(state, 0.0)


def undirected(edges: Iterable[tuple[str, str, float]]) -> dict[str, list[tuple[str, float]]]:
    adjacency: dict[str, list[tuple[str, float]]] = {}
    for a, b, cost in edges:
        adjacency.setdefault(a, []).append((b, cost))
        adjacency.setdefault(b, []).append((a, cost))
    return adjacency
