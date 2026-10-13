# Terminal walkthroughs

`searches run` animates by default when stdin and stdout are terminals with cursor
addressing and clearing support. `--no-animate` bypasses the interface completely.
Files, pipes, unavailable interactive input, `TERM=dumb`, and unsupported terminal
capabilities use the existing text output automatically. `compare`, `list`, and
`images` retain their existing behavior.

## Playback and inspection

The initial frontier appears before execution advances. Autoplay selects and
expands two nodes per second. Space pauses/resumes; N pauses and advances one
expansion. Selected goal nodes can finish without being expanded, as in the
non-interactive implementation. Empty-frontier exhaustion may finish on the next
playback tick after the last expansion.

Plus (or equals) and minus adjust the target rate from 0.25 to 64 steps/s. Normal
playback shows each expansion; rendering limits the effective rate to at most
20 steps/s. F explicitly enables faster, counted batches of up to 32 expansions.
Fast-forward coalesces redraws and omits tile interpolation, while applying every
underlying event. F toggles this mode off. Space pauses it, and N returns to normal
single-step mode. The header identifies fast-forward and processed selection/event
counts; no switch to batching happens automatically.

At completion the display retains the result, counters, frontier, visited history,
and highlighted solution. R replays the solution; Space, N, speed keys, and F also
work during replay. Q returns to the shell, printing the existing summary and
requested trace table, and saving a requested JSON result. A proven failure or
cutoff retains exit code 1. Quitting before completion exits 130, restores the
terminal, and writes no partial result. Existing output files are not deleted.

## Panes and resizing

The diagram uses C/F/V/P markers as well as color; PC marks the current solution
node. Node styling takes precedence over underlying edges. Tab selects a pane;
arrows and paging keys scroll its rows and columns. Frontier rows follow actual
queue, stack, or priority ordering, including labelled stale entries until the
engine removes them. Visited rows show the most recent selections first and retain
reopenings. Row ranges and totals identify data outside the visible viewport.

At 100 columns or wider, the diagram and search data sit side by side. Narrower
terminals use vertically stacked panes, with Tab bringing off-screen panes into
view. Under 60×18, the interface waits for resizing; quit controls remain available.
Resizing preserves user pause state and pane scroll positions. A 132×44 terminal
shows the letter graph and its search data together comfortably.

Connection/cost rows list every edge, including parallel bridges, with a full-name
key for Romania's abbreviations. Dense maps can share connection lanes; use the
connection table to inspect individual endpoints and weights. TSP and bridge maps
summarize physical locations while frontier/history rows identify complete search
states. The selected state also shows its visited-city or used-bridge set.

Puzzles show selected and goal boards together, then legal successor previews and
all generated successor states. Changing between unrelated selected boards is
labelled as a branch selection, not animated as a tile move. Sliding animation
applies only to a real parent/successor pair or adjacent boards in solution replay.
Paused single steps display the completed move.

`--ascii` uses ASCII lines, arrows, and borders. The same fallback is chosen for
encodings that cannot represent the Unicode symbols. `NO_COLOR` is respected;
markers preserve the meaning of highlighting without color.

## Events and measurement

The `Problem` protocol and existing return types remain unchanged. `search` and
its algorithm wrappers accept an optional keyword-only `on_event` callback:

```python
from searches import search
from searches.problems import get_problem


def observe(event):
    if event.kind == "expanded":
        print(event.node.state, event.stats.expanded)


result = search(get_problem("romania"), "astar", on_event=observe)
```

Immutable `SearchEvent`, `NodeInfo`, and `StatsSnapshot` records describe actual
initialization, selection, generated transitions, queue changes, stale removal,
expansion, and completion. Node identities distinguish cheaper replacements of
the same state and link each node to the actual parent/action. UCS exposes `f=g`,
greedy `f=h`, and A* `f=g+h`; uninformed searches do not evaluate extra heuristics.

Observer/event construction and delivery durations are subtracted from elapsed
search time and time-limit checks, including queue backpressure and pauses.
Algorithm work and solution reconstruction remain measured. The UI owns rendering;
a single worker owns search. Delivery is capped at 256 buffered events and demand
at 32 expansions. The model retains current search data and selection history,
not complete screen snapshots. Custom observer exceptions propagate to the caller.

The existing `--trace-limit` and `--snapshot-limit` still cap only the optional text
trace/JSON trace, not animation. Benchmarks attach no observer, allocate no animation
node metadata, and import no terminal application. Search time is distinct from
total elapsed time spent watching the walkthrough.
