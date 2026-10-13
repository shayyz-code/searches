"""Terminal capability checks without importing the interactive application."""

import os
import sys


def supports_animation() -> bool:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    term = os.environ.get("TERM", "")
    if term.lower() in ("", "dumb", "unknown"):
        return False
    try:
        import curses
    except ImportError:
        return False
    try:
        curses.setupterm(term=term, fd=sys.stdout.fileno())
        return bool(curses.tigetstr("cup") and curses.tigetstr("clear"))
    except (OSError, ValueError, curses.error):
        return False


def needs_ascii(encoding: str | None) -> bool:
    try:
        "─│↓↑".encode(encoding or "ascii")
        return False
    except (UnicodeEncodeError, LookupError):
        return True
