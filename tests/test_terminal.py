import io

import pytest

from searches.cli import main
from searches.terminal import needs_ascii, supports_animation


@pytest.mark.parametrize(
    "encoding,expected", [("ascii", True), ("utf-8", False), ("invalid-codec", True)]
)
def test_encoding_fallback(encoding, expected):
    assert needs_ascii(encoding) == expected


def test_noninteractive_fallback(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO())
    assert not supports_animation()


def test_dumb_terminal(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setenv("TERM", "dumb")
    assert not supports_animation()


def test_cli_no_animate_bypasses_capabilities(monkeypatch, capsys):
    def fail():
        raise AssertionError("Explicit plain output must bypass terminal detection")

    monkeypatch.setattr("searches.cli.supports_animation", fail)
    assert main(["run", "--problem", "romania", "--algorithm", "astar", "--no-animate"]) == 0
    assert "418" in capsys.readouterr().out


def test_cli_animation_and_cancel_exports(monkeypatch, tmp_path, capsys):
    from searches import search
    from searches.animation.channel import AnimationCancelled

    monkeypatch.setattr("searches.cli.supports_animation", lambda: True)
    output = tmp_path / "run.json"

    def completed(name, problem, algorithm, **kwargs):
        kwargs.pop("ascii_only")
        return search(problem, algorithm, **kwargs)

    monkeypatch.setattr("searches.animation.app.run_animation", completed)
    assert main(["run", "--problem", "romania", "--algorithm", "astar", "--json", str(output)]) == 0
    assert output.is_file()
    output.unlink()

    def cancelled(*args, **kwargs):
        raise AnimationCancelled()

    monkeypatch.setattr("searches.animation.app.run_animation", cancelled)
    assert (
        main(["run", "--problem", "romania", "--algorithm", "astar", "--json", str(output)]) == 130
    )
    assert not output.exists()
    assert "cancelled" in capsys.readouterr().out
