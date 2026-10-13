"""Repeated timing and separately instrumented Python-memory measurements."""

import csv
import json
import platform
import sys
import tracemalloc
from collections.abc import Callable, Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

from searches.algorithms import ALGORITHMS, search
from searches.core import SearchLimits, SearchResult
from searches.problems import PROBLEMS, get_problem


def json_value(value):
    """Serialize heterogeneous immutable states without unstable set ordering."""
    if isinstance(value, (set, frozenset)):
        return [json_value(item) for item in sorted(value, key=str)]
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    return value


def result_record(result: SearchResult) -> dict:
    return {
        "status": result.status,
        "cutoff_reason": result.cutoff_reason,
        "cost": result.cost,
        "depth": result.depth,
        **asdict(result.stats),
    }


def benchmark(
    problem_name: str,
    algorithm: str,
    *,
    repeats: int = 3,
    limits: SearchLimits | None = None,
) -> dict:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    samples = []
    first = None
    # Setup happens before each search's internal timer starts.
    for _ in range(repeats):
        problem = get_problem(problem_name)
        result = search(problem, algorithm, limits=limits)
        samples.append(result_record(result))
        if first is None:
            first = result
        else:
            del result
    if tracemalloc.is_tracing():
        raise RuntimeError("Benchmark memory measurement requires tracemalloc to be inactive")
    problem = get_problem(problem_name)
    tracemalloc.start()
    try:
        memory_result = search(problem, algorithm, limits=limits)
        _, peak_bytes = tracemalloc.get_traced_memory()
        memory_sample = result_record(memory_result)
    finally:
        tracemalloc.stop()
    identities = {(s["status"], s["cutoff_reason"], s["cost"], s["depth"]) for s in samples}
    return {
        "problem": problem_name,
        "algorithm": algorithm,
        **result_record(first),
        "sample_status": first.status,
        "status": first.status if len(identities) == 1 else "mixed",
        "median_seconds": median(s["elapsed_seconds"] for s in samples),
        "peak_python_bytes": peak_bytes,
        "memory_status": memory_sample["status"],
        "memory_cutoff_reason": memory_sample["cutoff_reason"],
        "timing_runs": samples,
        "memory_run": memory_sample,
        "path": json_value(first.path),
        "actions": list(first.actions),
    }


def compare(
    problems: Iterable[str] | None = None,
    algorithms: Iterable[str] = ALGORITHMS,
    *,
    repeats: int = 3,
    limits: SearchLimits | None = None,
    progress: Callable[[str, str], None] | None = None,
) -> dict:
    names = list(PROBLEMS) if problems is None else list(problems)
    algorithms = tuple(algorithms)
    if not names or not algorithms:
        raise ValueError("Select at least one problem and algorithm")
    limits = limits or SearchLimits()
    if limits.depth_limit is not None and any(a != "dfs" for a in algorithms):
        raise ValueError("Depth-limited comparisons must select DFS only")
    rows = []
    for name in names:
        for algorithm in algorithms:
            if progress is not None:
                progress(name, algorithm)
            rows.append(benchmark(name, algorithm, repeats=repeats, limits=limits))
    return {
        "metadata": {
            "created_utc": datetime.now(UTC).isoformat(),
            "python": sys.version,
            "platform": platform.platform(),
            "repeats": repeats,
            "limits": asdict(limits),
            "problems": names,
            "algorithms": algorithms,
            "measurement": (
                "Median search-only timing; separate tracemalloc search; traces disabled. "
                "Counters/path are from the first timing run. Memory excludes problem setup. "
                "Cutoff and mixed outcomes must not be ranked as successful solutions."
            ),
        },
        "results": rows,
    }


CSV_FIELDS = (
    "problem",
    "algorithm",
    "status",
    "sample_status",
    "cutoff_reason",
    "cost",
    "depth",
    "expanded",
    "generated",
    "peak_frontier",
    "retained_states",
    "median_seconds",
    "peak_python_bytes",
    "memory_status",
    "memory_cutoff_reason",
)


def save_report(report: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    with (directory / "comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["results"])
