"""Five-city travelling salesperson state space with an admissible MST bound."""

from searches.core import Transition

TSP_EDGES = (
    ("A", "B", 100),
    ("A", "C", 125),
    ("A", "D", 100),
    ("A", "E", 75),
    ("B", "C", 50),
    ("B", "D", 75),
    ("B", "E", 125),
    ("C", "D", 100),
    ("C", "E", 125),
    ("D", "E", 50),
)


class TravellingSalespersonProblem:
    cities = ("A", "B", "C", "D", "E")
    initial = ("A", frozenset({"A"}))

    def __init__(self):
        self.weights = {frozenset((a, b)): float(cost) for a, b, cost in TSP_EDGES}

    def distance(self, a: str, b: str) -> float:
        return self.weights[frozenset((a, b))] if a != b else 0.0

    def successors(self, state: tuple[str, frozenset[str]]):
        current, visited = state
        if len(visited) == len(self.cities):
            if current != "A":
                yield Transition("return to A", ("A", visited), self.distance(current, "A"))
            return
        for city in self.cities:
            if city not in visited:
                yield Transition(
                    f"travel to {city}", (city, visited | {city}), self.distance(current, city)
                )

    def is_goal(self, state: tuple[str, frozenset[str]]) -> bool:
        current, visited = state
        return current == "A" and len(visited) == len(self.cities)

    def heuristic(self, state: tuple[str, frozenset[str]]) -> float:
        current, visited = state
        remaining = [city for city in self.cities if city not in visited]
        if not remaining:
            return self.distance(current, "A")
        connected = {remaining[0]}
        mst = 0.0
        while len(connected) < len(remaining):
            weight, city = min(
                (self.distance(a, b), b)
                for a in sorted(connected)
                for b in remaining
                if b not in connected
            )
            mst += weight
            connected.add(city)
        return (
            mst
            + min(self.distance(current, city) for city in remaining)
            + min(self.distance(city, "A") for city in remaining)
        )
