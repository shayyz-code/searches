import csv
import json
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from searches.algorithms import ALGORITHMS
from searches.cli import _show_comparison, main
from searches.comparisons import benchmark, compare, save_report
from searches.core import SearchLimits
from searches.problems import PROBLEMS
from searches.visualization import save_figures


def test_cli_runs_exports_and_exit_codes(tmp_path, capsys):
    output = tmp_path / "run.json"
    assert main(["run", "--problem", "romania", "--algorithm", "astar", "--json", str(output)]) == 0
    data = json.loads(output.read_text())
    assert data["cost"] == 418
    assert data["path"][0] == "Arad"
    assert "418" in capsys.readouterr().out
    assert (
        main(
            [
                "run",
                "--problem",
                "letter_graph",
                "--algorithm",
                "bfs",
                "--trace",
                "--trace-limit",
                "2",
                "--json",
                str(output),
            ]
        )
        == 0
    )
    assert len(json.loads(output.read_text())["trace"]) == 2
    assert "Trace truncated" in capsys.readouterr().out
    assert (
        main(["run", "--problem", "puzzle_walkthrough", "--algorithm", "dfs", "--depth-limit", "5"])
        == 0
    )
    assert main(["run", "--problem", "numbered_graph", "--algorithm", "dfs", "--traverse"]) == 0
    assert main(["run", "--problem", "bridges_i1", "--algorithm", "bfs"]) == 1
    assert (
        main(["run", "--problem", "romania", "--algorithm", "astar", "--max-expansions", "0"]) == 1
    )
    assert main(["run", "--problem", "romania", "--algorithm", "bfs", "--depth-limit", "2"]) == 2
    assert main(["list"]) == 0


def test_measurement_exports_and_plot_files(tmp_path):
    report = compare(["romania", "unreachable_graph"], repeats=2)
    assert len(report["results"]) == 10
    assert report["metadata"]["repeats"] == 2
    row = report["results"][0]
    assert len(row["timing_runs"]) == 2
    assert row["peak_python_bytes"] > 0
    assert row["median_seconds"] >= 0
    assert row["memory_status"] == "found"
    save_report(report, tmp_path)
    assert json.loads((tmp_path / "comparison.json").read_text())["metadata"]["python"]
    with (tmp_path / "comparison.csv").open() as stream:
        assert len(list(csv.DictReader(stream))) == 10
    save_figures(report, tmp_path)
    for name in ("traversal_order", "romania_routes", "comparison_metrics", "suite_expansions"):
        assert (tmp_path / f"{name}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_complete_default_suite_smoke():
    # Every default problem/algorithm executes; a small budget keeps CI bounded.
    report = compare(repeats=1, limits=SearchLimits(max_expansions=100))
    assert len(report["results"]) == len(PROBLEMS) * len(ALGORITHMS)
    assert {row["problem"] for row in report["results"]} == set(PROBLEMS)
    assert {row["status"] for row in report["results"]} <= {"found", "no_solution", "cutoff"}


def test_comparison_cli(tmp_path, capsys):
    assert (
        main(
            [
                "compare",
                "--problems",
                "weighted_trap",
                "--algorithms",
                "bfs",
                "ucs",
                "--repeats",
                "1",
                "--output",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (tmp_path / "comparison.json").is_file()
    assert "Saved CSV" in capsys.readouterr().out


def test_invalid_comparison_configuration():
    with pytest.raises(ValueError):
        benchmark("romania", "bfs", repeats=0)
    with pytest.raises(ValueError):
        compare([], repeats=1)
    with pytest.raises(ValueError):
        compare(["romania"], limits=SearchLimits(depth_limit=2))


def test_images_cli(tmp_path):
    assert main(["images", "--output", str(tmp_path)]) == 0
    assert len(list(Path(tmp_path).glob("*.png"))) == 3


def test_comparison_output_readable_in_standard_terminal():
    report = compare(["romania"], repeats=1)
    stream = StringIO()
    _show_comparison(Console(file=stream, width=80), report)
    output = stream.getvalue()
    assert "romania" in output
    assert "418" in output
    assert "Expanded" in output
    assert "Retained states" in output
    assert "…" not in output
