"""Deck data transcribed from slides; source mapping lives in docs/comparisons.md."""

from searches.problems.graph import GraphProblem, undirected

ROMANIA_EDGES = (
    ("Arad", "Zerind", 75),
    ("Arad", "Sibiu", 140),
    ("Arad", "Timisoara", 118),
    ("Zerind", "Oradea", 71),
    ("Oradea", "Sibiu", 151),
    ("Sibiu", "Fagaras", 99),
    ("Sibiu", "Rimnicu Vilcea", 80),
    ("Fagaras", "Bucharest", 211),
    ("Rimnicu Vilcea", "Pitesti", 97),
    ("Rimnicu Vilcea", "Craiova", 146),
    ("Pitesti", "Craiova", 138),
    ("Pitesti", "Bucharest", 101),
    ("Timisoara", "Lugoj", 111),
    ("Lugoj", "Mehadia", 70),
    ("Mehadia", "Dobreta", 75),
    ("Dobreta", "Craiova", 120),
    ("Bucharest", "Giurgiu", 90),
    ("Bucharest", "Urziceni", 85),
    ("Urziceni", "Hirsova", 98),
    ("Hirsova", "Eforie", 86),
    ("Urziceni", "Vaslui", 142),
    ("Vaslui", "Iasi", 92),
    ("Iasi", "Neamt", 87),
)
ROMANIA_HEURISTICS = {
    "Arad": 366,
    "Bucharest": 0,
    "Craiova": 160,
    "Dobreta": 242,
    "Eforie": 161,
    "Fagaras": 176,
    "Giurgiu": 77,
    "Hirsova": 151,
    "Iasi": 226,
    "Lugoj": 244,
    "Mehadia": 241,
    "Neamt": 234,
    "Oradea": 380,
    "Pitesti": 100,
    "Rimnicu Vilcea": 193,
    "Sibiu": 253,
    "Timisoara": 329,
    "Urziceni": 80,
    "Vaslui": 199,
    "Zerind": 374,
}


def numbered_graph() -> GraphProblem:
    return GraphProblem(
        {1: ((2, 1), (3, 1), (4, 1)), 2: ((5, 1), (6, 1)), 4: ((7, 1), (8, 1))}, 1, 8
    )


def letter_graph() -> GraphProblem:
    successors = {
        "A": "BCD",
        "B": "EF",
        "C": "GH",
        "D": "IJ",
        "E": "KL",
        "F": "LM",
        "G": "N",
        "H": "OP",
        "I": "PQ",
        "J": "R",
        "K": "S",
        "L": "T",
        "P": "U",
    }
    return GraphProblem({a: tuple((b, 1) for b in bs) for a, bs in successors.items()}, "A", "O")


def weighted_graph() -> GraphProblem:
    # The two occurrences of 6 on slide 31 represent the same goal state.
    return GraphProblem(
        {1: ((2, 1), (3, 4), (4, 3)), 2: ((5, 2), (6, 5)), 4: ((6, 5), (8, 1))}, 1, 6
    )


def romania() -> GraphProblem:
    return GraphProblem(undirected(ROMANIA_EDGES), "Arad", "Bucharest", ROMANIA_HEURISTICS)


def cyclic_graph() -> GraphProblem:
    return GraphProblem(
        {"S": (("A", 1), ("B", 1)), "A": (("S", 1), ("G", 1)), "B": (("A", 1),)}, "S", "G"
    )


def unreachable_graph() -> GraphProblem:
    return GraphProblem({"S": (("A", 1),), "A": (("S", 1),)}, "S", "G")


def weighted_trap() -> GraphProblem:
    return GraphProblem(
        {"S": (("G", 10), ("A", 1)), "A": (("B", 1),), "B": (("G", 1),)},
        "S",
        "G",
        {"S": 3, "A": 2, "B": 1, "G": 0},
    )
