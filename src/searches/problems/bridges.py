"""Königsberg's distinct bridges; parallel edges cannot be merged."""

from searches.core import Transition

BRIDGES = (
    ("b1", "i1", "i2"),
    ("b2", "i1", "rb1"),
    ("b3", "i1", "rb1"),
    ("b4", "rb1", "i2"),
    ("b5", "i1", "rb2"),
    ("b6", "i1", "rb2"),
    ("b7", "rb2", "i2"),
)
LOCATIONS = ("i1", "i2", "rb1", "rb2")


class BridgesProblem:
    def __init__(self, start: str = "i1"):
        if start not in LOCATIONS:
            raise ValueError(f"Unknown bridge starting location: {start}")
        self.initial = (start, 0)

    def successors(self, state: tuple[str, int]):
        location, used = state
        for i, (bridge, a, b) in enumerate(BRIDGES):
            if not used & (1 << i) and location in (a, b):
                target = b if location == a else a
                yield Transition(bridge, (target, used | (1 << i)))

    def is_goal(self, state: tuple[str, int]) -> bool:
        return state[1] == (1 << len(BRIDGES)) - 1

    def heuristic(self, state: tuple[str, int]) -> float:
        return float(len(BRIDGES) - state[1].bit_count())
