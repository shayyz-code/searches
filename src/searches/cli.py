"""Command-line runs, optional walkthroughs, and comparison reports."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from searches.algorithms import ALGORITHMS, search
from searches.comparisons import compare, json_value, result_record, save_report
from searches.core import SearchLimits, SearchResult
from searches.problems import PROBLEMS, get_problem


def _limits(args) -> SearchLimits:
    return SearchLimits(args.max_seconds, args.max_expansions, args.depth_limit)


def _short(value, maximum: int = 180) -> str:
    text = str(value)
    return text if len(text) <= maximum else text[: maximum - 1] + "…"


def _show_run(console: Console, result: SearchResult) -> None:
    reason = f" ({result.cutoff_reason})" if result.cutoff_reason else ""
    console.print(f"Outcome: {result.status}{reason}", style="bold")
    if result.status == "found":
        console.print(f"Cost: {result.cost:g} | Depth: {result.depth}")
        states = (
            result.path if len(result.path) <= 20 else (*result.path[:10], "…", *result.path[-5:])
        )
        console.print("Path: " + " → ".join(_short(state, 70) for state in states), markup=False)
        if len(result.actions) <= 20:
            console.print("Actions: " + ", ".join(result.actions), markup=False)
        else:
            console.print(
                f"Path display abbreviated; {len(result.path)} states. Use --json for all."
            )
    elif result.status == "traversed":
        console.print("Visit order: " + _short(result.visit_order), markup=False)
    console.print(
        f"Expanded: {result.stats.expanded} | Generated: {result.stats.generated} | "
        f"Peak frontier: {result.stats.peak_frontier} | "
        f"Retained states: {result.stats.retained_states}"
    )
    console.print(f"Search time: {result.stats.elapsed_seconds:.6f}s")
    if result.trace:
        table = Table(title="Trace · frontier before expansion; latest visited entries first")
        for title in ("Step", "Selected", "Depth / g", "Frontier", "Visited"):
            table.add_column(title)
        for event in result.trace:
            frontier = _short(event.frontier)
            visited = _short(event.visited)
            if event.frontier_total > len(event.frontier):
                frontier += f" … ({event.frontier_total} total)"
            if event.visited_total > len(event.visited):
                visited += f" … ({event.visited_total} total)"
            table.add_row(
                str(event.iteration),
                _short(event.selected, 70),
                f"{event.depth} / {event.cost:g}",
                frontier,
                visited,
            )
        console.print(table)
    if result.trace_truncated:
        console.print(f"Trace truncated at {len(result.trace)} events.")


def _show_comparison(console: Console, report: dict) -> None:
    console.print("First-run counters · median timing · separate memory measurement", style="dim")
    for name in report["metadata"]["problems"]:
        rows = [row for row in report["results"] if row["problem"] == name]
        summary = Table(title=name)
        for label in ("Search", "Outcome", "Cost", "Depth", "ms", "Memory KiB"):
            summary.add_column(label, justify="left" if label in ("Search", "Outcome") else "right")
        work = Table()
        for label in ("Search", "Expanded", "Generated", "Peak frontier", "Retained states"):
            work.add_column(label, justify="left" if label == "Search" else "right")
        for row in rows:
            status = row["status"]
            if row["cutoff_reason"]:
                status += f"/{row['cutoff_reason']}"
            summary.add_row(
                row["algorithm"],
                status,
                "—" if row["cost"] is None else f"{row['cost']:g}",
                "—" if row["depth"] is None else str(row["depth"]),
                f"{row['median_seconds'] * 1000:.3f}",
                f"{row['peak_python_bytes'] / 1024:.1f}",
            )
            work.add_row(
                row["algorithm"],
                str(row["expanded"]),
                str(row["generated"]),
                str(row["peak_frontier"]),
                str(row["retained_states"]),
            )
        console.print(summary)
        console.print(work)
        for row in rows:
            if (row["memory_status"], row["memory_cutoff_reason"]) != (
                row["sample_status"],
                row["cutoff_reason"],
            ):
                console.print(
                    f"{row['algorithm']} memory run: {row['memory_status']} "
                    f"({row['memory_cutoff_reason'] or 'no cutoff'}); see JSON for details."
                )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Search algorithms and deck examples")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Solve a problem or traverse a graph")
    run.add_argument("--problem", choices=PROBLEMS, required=True)
    run.add_argument("--algorithm", choices=ALGORITHMS, required=True)
    run.add_argument(
        "--traverse", action="store_true", help="Full numbered-graph BFS/DFS traversal"
    )
    run.add_argument("--trace", action="store_true")
    run.add_argument("--trace-limit", type=int, default=100)
    run.add_argument("--snapshot-limit", type=int, default=20)
    run.add_argument("--json", type=Path, help="Save complete path, actions, statistics, and trace")
    comparison = commands.add_parser(
        "compare", help="Benchmark all examples and save reports/plots"
    )
    comparison.add_argument("--problems", nargs="+", choices=PROBLEMS)
    comparison.add_argument("--algorithms", nargs="+", choices=ALGORITHMS, default=ALGORITHMS)
    comparison.add_argument("--repeats", type=int, default=3)
    comparison.add_argument("--output", type=Path, default=Path("reports"))
    for command in (run, comparison):
        command.add_argument("--max-seconds", type=float, default=30)
        command.add_argument("--max-expansions", type=int, default=250_000)
        command.add_argument("--depth-limit", type=int, help="DFS only")
    images = commands.add_parser(
        "images", help="Regenerate the three README visuals from fresh results"
    )
    images.add_argument("--output", type=Path, default=Path("docs/images"))
    commands.add_parser("list", help="List available algorithms and problem names")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    console = Console()
    try:
        if args.command == "list":
            console.print("Algorithms: " + ", ".join(ALGORITHMS))
            console.print("Problems:\n" + "\n".join(PROBLEMS))
        elif args.command == "run":
            if args.traverse and args.problem != "numbered_graph":
                raise ValueError("--traverse is supported for numbered_graph")
            result = search(
                get_problem(args.problem),
                args.algorithm,
                limits=_limits(args),
                trace=args.trace,
                trace_limit=args.trace_limit,
                snapshot_limit=args.snapshot_limit,
                traversal=args.traverse,
            )
            _show_run(console, result)
            if args.json:
                args.json.parent.mkdir(parents=True, exist_ok=True)
                args.json.write_text(
                    json.dumps(
                        {
                            **result_record(result),
                            "path": json_value(result.path),
                            "actions": result.actions,
                            "visit_order": json_value(result.visit_order),
                            "trace": json_value([asdict(event) for event in result.trace]),
                            "trace_truncated": result.trace_truncated,
                        },
                        indent=2,
                    )
                    + "\n"
                )
            return 0 if result.status in ("found", "traversed") else 1
        elif args.command == "compare":
            with Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Comparing searches", total=None)
                report = compare(
                    args.problems,
                    args.algorithms,
                    repeats=args.repeats,
                    limits=_limits(args),
                    progress=lambda name, algorithm: progress.update(
                        task, description=f"{name}: {algorithm}"
                    ),
                )
            save_report(report, args.output)
            from searches.visualization import save_figures

            save_figures(report, args.output)
            _show_comparison(console, report)
            console.print(f"Saved CSV, JSON, and four PNG figures to {args.output.resolve()}")
        elif args.command == "images":
            from searches.visualization import regenerate_readme_images

            regenerate_readme_images(args.output)
            console.print(f"Saved three README figures to {args.output.resolve()}")
    except (ValueError, TypeError, OSError) as exc:
        console.print(f"Error: {exc}", style="red", markup=False)
        return 2
    return 0
