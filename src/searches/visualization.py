"""Static figures derived from measured results, using a headless backend."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from searches.algorithms import ALGORITHMS, search  # noqa: E402
from searches.core import SearchLimits  # noqa: E402
from searches.problems import get_problem  # noqa: E402
from searches.problems.examples import ROMANIA_EDGES  # noqa: E402

COLORS = {
    "bfs": "#2d6cdf",
    "dfs": "#a45cbd",
    "ucs": "#19856a",
    "greedy": "#d8891c",
    "astar": "#c44848",
}
LABELS = {"bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "greedy": "Greedy", "astar": "A*"}


def _save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def plot_traversal(path: Path) -> None:
    positions = {
        1: (0, 2),
        2: (-2, 1),
        3: (0, 1),
        4: (2, 1),
        5: (-3, 0),
        6: (-1, 0),
        7: (1, 0),
        8: (3, 0),
    }
    problem = get_problem("numbered_graph")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for ax, algorithm in zip(axes, ("bfs", "dfs"), strict=True):
        result = search(problem, algorithm, traversal=True)
        for state in positions:
            for transition in problem.successors(state):
                a, b = positions[state], positions[transition.state]
                ax.plot((a[0], b[0]), (a[1], b[1]), color="#bbc3cf", zorder=1)
        for rank, state in enumerate(result.visit_order, 1):
            x, y = positions[state]
            ax.scatter(x, y, s=950, color=COLORS[algorithm], zorder=2)
            ax.text(x, y, str(state), color="white", ha="center", va="center", fontsize=15)
            ax.text(x + 0.34, y + 0.14, f"#{rank}", fontsize=10, color="#344053")
        ax.set_title(LABELS[algorithm], fontsize=17, weight="bold")
        ax.text(
            0.5,
            -0.06,
            " → ".join(map(str, result.visit_order)),
            transform=ax.transAxes,
            ha="center",
            fontsize=11,
        )
        ax.set(xlim=(-3.8, 3.8), ylim=(-0.5, 2.6))
        ax.axis("off")
    fig.suptitle("Traversal order on the deck’s numbered graph", fontsize=18)
    _save(fig, path)


def plot_romania(path: Path) -> None:
    positions = {
        "Arad": (0, 3.1),
        "Zerind": (0.2, 4),
        "Oradea": (0.8, 5),
        "Sibiu": (2, 3),
        "Timisoara": (0, 1.9),
        "Lugoj": (1, 1.2),
        "Mehadia": (1, 0.4),
        "Dobreta": (1, -0.5),
        "Craiova": (2.4, -0.7),
        "Fagaras": (3.5, 2.8),
        "Rimnicu Vilcea": (2.4, 1.7),
        "Pitesti": (3.5, 0.7),
        "Bucharest": (4.7, 0),
    }
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), layout="constrained")
    for ax, algorithm in zip(axes, ("greedy", "astar"), strict=True):
        result = search(get_problem("romania"), algorithm)
        selected = {frozenset((a, b)) for a, b in zip(result.path, result.path[1:], strict=False)}
        for a, b, cost in ROMANIA_EDGES:
            if a not in positions or b not in positions:
                continue
            x1, y1 = positions[a]
            x2, y2 = positions[b]
            highlighted = frozenset((a, b)) in selected
            ax.plot(
                (x1, x2),
                (y1, y2),
                color=COLORS[algorithm] if highlighted else "#d0d5dd",
                linewidth=3 if highlighted else 1,
                zorder=1,
            )
            if highlighted:
                ax.text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2 + 0.1,
                    str(cost),
                    fontsize=10,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 1},
                )
        for city, (x, y) in positions.items():
            ax.scatter(
                x, y, color=COLORS[algorithm] if city in result.path else "#aab2be", s=60, zorder=3
            )
            label = city.replace("Rimnicu Vilcea", "Rimnicu\nVilcea")
            ax.annotate(
                label,
                (x, y),
                xytext=(12, 2) if city == "Rimnicu Vilcea" else (0, 9),
                textcoords="offset points",
                ha="left" if city == "Rimnicu Vilcea" else "center",
                fontsize=9,
            )
        ax.set_title(f"{LABELS[algorithm]}: cost {result.cost:g}", fontsize=17, weight="bold")
        ax.text(
            0.5,
            -0.06,
            " → ".join(result.path).replace("Rimnicu Vilcea", "R. Vilcea"),
            transform=ax.transAxes,
            ha="center",
            fontsize=10,
        )
        ax.set(xlim=(-0.65, 5.3), ylim=(-1.1, 5.7))
        ax.axis("off")
    fig.suptitle("Arad to Bucharest · road costs, with relevant map region shown", fontsize=17)
    _save(fig, path)


def plot_comparison(report: dict, path: Path, problem: str = "romania") -> None:
    rows = [row for row in report["results"] if row["problem"] == problem]
    if not rows:
        raise ValueError(f"No measured comparison for {problem}")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), layout="constrained")
    fields = ("cost", "expanded", "median_seconds")
    titles = ("Solution cost", "Expanded nodes", "Median time (ms)")
    for ax, field, title in zip(axes, fields, titles, strict=True):
        for i, row in enumerate(rows):
            if row["status"] == "found":
                value = row[field] * (1000 if field == "median_seconds" else 1)
                ax.bar(i, value, color=COLORS[row["algorithm"]], width=0.65)
                ax.annotate(
                    f"{value:.3f}" if field == "median_seconds" else f"{value:g}",
                    (i, value),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    fontsize=9,
                )
            else:
                ax.text(
                    i,
                    0.03,
                    row["status"].replace("_", "\n"),
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    fontsize=8,
                )
        ax.set_xticks(range(len(rows)), [LABELS[row["algorithm"]] for row in rows])
        ax.set_title(title, fontsize=13)
        ax.set_ylim(bottom=0, top=max(ax.get_ylim()[1] * 1.18, 0.001))
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.15)
        ax.set_axisbelow(True)
    fig.suptitle(f"Measured search comparison · {problem}", fontsize=18)
    fig.text(
        0.5,
        -0.035,
        "Timing is machine-dependent; cutoffs and failures are not successful bars.",
        ha="center",
        fontsize=9,
        color="#4b5563",
    )
    _save(fig, path)


def plot_suite(report: dict, path: Path) -> None:
    """Compare expansions across the entire suite, preserving failure labels."""
    names = report["metadata"]["problems"]
    fig, ax = plt.subplots(figsize=(12, max(5, len(names) * 0.55)), layout="constrained")
    algorithms = [a for a in ALGORITHMS if a in report["metadata"]["algorithms"]]
    width = 0.8 / len(algorithms)
    lookup = {(r["problem"], r["algorithm"]): r for r in report["results"]}
    uniform_failures = {
        name: lookup[name, algorithms[0]]["status"]
        for name in names
        if len({lookup[name, algorithm]["status"] for algorithm in algorithms}) == 1
        and lookup[name, algorithms[0]]["status"] != "found"
    }
    for offset, algorithm in enumerate(algorithms):
        for index, name in enumerate(names):
            row = lookup[name, algorithm]
            y = index - 0.4 + width * (offset + 0.5)
            ax.barh(
                y,
                max(row["expanded"], 1),
                height=width * 0.9,
                color=COLORS[algorithm],
                alpha=0.8,
                hatch="//" if row["status"] != "found" else None,
                label=LABELS[algorithm] if index == 0 else None,
            )
            if row["status"] != "found" and name not in uniform_failures:
                ax.text(
                    max(row["expanded"], 1) * 1.12,
                    y,
                    row["status"].replace("_", " "),
                    va="center",
                    fontsize=7,
                )
    for index, name in enumerate(names):
        if name in uniform_failures:
            maximum = max(lookup[name, algorithm]["expanded"] for algorithm in algorithms)
            ax.text(
                max(maximum, 1) * 1.12,
                index,
                uniform_failures[name].replace("_", " ") + " (all)",
                va="center",
                fontsize=9,
            )
    ax.set_yticks(range(len(names)), names)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("Expanded nodes (log scale; zero shown at 1)")
    ax.set_title("All examples · search work and outcomes", fontsize=17)
    ax.legend(ncols=len(algorithms), loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.15)
    _save(fig, path)


def save_figures(report: dict, directory: Path) -> None:
    plot_traversal(directory / "traversal_order.png")
    plot_romania(directory / "romania_routes.png")
    name = (
        "romania"
        if "romania" in report["metadata"]["problems"]
        else report["results"][0]["problem"]
    )
    plot_comparison(report, directory / "comparison_metrics.png", name)
    plot_suite(report, directory / "suite_expansions.png")


def regenerate_readme_images(directory: Path) -> None:
    """Measure Romania afresh and regenerate the three committed README figures."""
    from searches.comparisons import compare

    report = compare(["romania"], limits=SearchLimits())
    plot_traversal(directory / "traversal_order.png")
    plot_romania(directory / "romania_routes.png")
    plot_comparison(report, directory / "comparison_metrics.png")
