"""Regenerate the README SVG from the real application and search events."""

import argparse
import asyncio
import os
from pathlib import Path
from time import monotonic

from searches.animation.app import SearchAnimation
from searches.problems import get_problem


async def capture(output: Path) -> None:
    # Make the documentation export colorful even in CI/NO_COLOR shells.
    os.environ.pop("NO_COLOR", None)
    app = SearchAnimation("letter_graph", get_problem("letter_graph"), "bfs", autoplay=False)
    async with app.run_test(size=(132, 44)) as pilot:
        for step in range(5):
            deadline = monotonic() + 5
            while not (
                app.channel.waiting and app.channel.events.empty() and app.model.steps == step
            ):
                if monotonic() > deadline:
                    raise RuntimeError("Walkthrough did not reach the expected screenshot state")
                await pilot.pause(0.02)
            if step < 4:
                await pilot.press("n")
        app.refresh_views()
        await pilot.pause()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(app.export_screenshot(title="BFS terminal walkthrough"), encoding="utf-8")
        await pilot.press("q")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/images/terminal_walkthrough.svg"))
    args = parser.parse_args()
    asyncio.run(capture(args.output))
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
