# Search behavior and deck coverage

The implementations use immutable states, ordered successors, nonnegative finite
step costs, and a goal test. Informed searches also use a nonnegative finite
heuristic. Algorithms are implemented here using Python's standard library;
they do not call a graph library's search routines.

## Related searches

| Comparison | Shared behavior | Important difference | Example |
| --- | --- | --- | --- |
| BFS / DFS | Explore without a heuristic | BFS selects the shallowest node; DFS follows the first branch deeply | Numbered graph traversal |
| BFS / UCS | Find shortest solutions under their ordering | BFS minimizes moves; UCS minimizes accumulated cost | `weighted_trap`: BFS cost 10, UCS cost 3 |
| UCS / A* | Track cheapest known paths and reopen improved states | UCS orders by `g`; A* orders by `g + h` | Romania: both cost 418; A* explores fewer nodes |
| Greedy / A* | Use an estimate of distance to the goal | Greedy orders by `h` alone; A* also accounts for cost already paid | Romania: greedy cost 450, A* cost 418 |

`g` is the actual accumulated path cost. `h` estimates the remaining cost.
Adding heuristic values along a route does **not** calculate its path cost.
With a zero heuristic, A* uses the same priority and tie ordering as UCS.

## Guarantees and complexity

These statements concern unrestricted searches. A configured limit can interrupt
any algorithm; a cutoff is not proof that no solution exists.

| Algorithm | Completeness | Optimality |
| --- | --- | --- |
| BFS | Complete on finite graphs; also with finite branching and a finite-depth goal | Fewest actions; least cost when every edge has the same cost |
| DFS | This implementation is complete on finite graphs because it prevents repeated-state loops | Not guaranteed |
| UCS | Complete on finite graphs with nonnegative costs; infinite spaces need further conditions, such as a positive lower bound on edge costs | Least path cost |
| Greedy | This implementation is complete on finite graphs with duplicate suppression; not guaranteed on infinite spaces | Not guaranteed |
| A* | Complete on these finite graphs; infinite spaces require additional branching/cost conditions | Least path cost with an admissible heuristic, zero at goals, and reopening of improved states |

An admissible heuristic never overestimates the remaining cost. A consistent
heuristic additionally satisfies `h(s) <= cost(s, t) + h(t)` for every edge.
This A* implementation supports admissible inconsistent heuristics by reopening
states reached with a cheaper `g`.

For finite graphs, unrestricted BFS and DFS run in `O(V + E)` time and retain
`O(V)` distinct states. Their traversal history and discovery maps mean DFS here
does not have the small memory footprint of DFS that stores only a recursion path.
UCS uses a lazy priority queue: stale entries can require `O(E)` queue space and
`O((V + E) log(V + E))` time. Greedy discovers a state once and uses a heap;
A* with reopening can expand a state repeatedly, so its work depends on the
heuristic and number of improvements. Depth-limited DFS can also revisit states
at shallower depths.

Textbook **tree-search** estimates use branching factor `b`, shallowest solution
depth `d`, and maximum depth `m`: BFS can require `O(b^(d+1))` time/space, while
DFS takes `O(b^m)` time and an `O(bm)` frontier. Those estimates are not universal
measurements of these graph-search implementations. A single benchmark cannot
establish asymptotic complexity, completeness, or an optimality guarantee.

See the primary [AIMA search reference](https://aima.cs.berkeley.edu/python/search.html)
for problem formulation, search terminology, and heuristic evaluation functions.

## Measurements and limits

`uv run searches compare` includes all 15 registered instances and all five
algorithms. Each pair has three uninstrumented timing runs and one separate
`tracemalloc` run. Problem construction, printing, and plotting happen outside
the measurement. Search bookkeeping and solution reconstruction are included.
Python allocation memory excludes problem construction, native allocations,
and interpreter/process memory; it is not RSS.

Interactive `run` walkthroughs use separate execution events and subtract observer
delivery and playback waits from search time. Comparison runs attach no observer;
animation timing, metadata, and rendering are absent from these measurements.

| Metric | Definition |
| --- | --- |
| Expanded | Nodes whose successors are explored, including leaves; excludes goals and depth-boundary probes |
| Generated | Initial node plus every yielded successor, including duplicates and depth-boundary probes |
| Peak frontier | Maximum queued entries, including stale priority-queue entries |
| Retained states | Peak distinct state keys in the discovery/best-score map; not a count of all live node objects |
| Median time | Median of the timing runs, measured with `perf_counter` |
| Peak Python bytes | Peak allocations during the separate memory-instrumented search |

Counters, cost, depth, and path come from the first timing run. JSON preserves
all timing samples and the memory run's counters/outcome. If timing outcomes
differ, the summary is `mixed`. Memory instrumentation can cause a time cutoff
even when timing runs succeed; its outcome is shown separately. Charts do not
draw successful-solution bars for cutoff, mixed, or exhausted outcomes.

Each search defaults to 30 seconds and 250,000 expansions. These are cooperative
limits checked between search operations, not an operating-system timeout;
a slow custom successor or heuristic function can exceed the time budget.
The limits apply independently to every timing and memory run.

```bash
uv run searches compare --problems romania tsp --repeats 5
uv run searches compare --max-seconds 60 --max-expansions 500000
uv run searches compare --problems puzzle_walkthrough --algorithms dfs --depth-limit 5
```

Reports contain CSV, JSON with configuration/platform metadata, and four PNGs.
The default output directory is ignored by Git. Runtime values depend on the
machine and system load; fixed successor ordering makes search order reproducible.

## Deck coverage

Source: *Topic 2 – Problem Solving using Search*, supplied PowerPoint, 41 slides.
Its cited references are Russell & Norvig (2016) and Luger (2011). The original
deck is not distributed with this repository.

| Slides | Project example or behavior |
| --- | --- |
| 6, 33–36 | `romania`: Arad → Bucharest; road distances and straight-line estimates from slide 33 |
| 8 | `bridges_i1`, `bridges_i2`, `bridges_rb1`, `bridges_rb2`: all starting locations; distinct bridge IDs |
| 10 | `tsp`: weighted five-city graph, each city visited once, returning to A |
| 11–12 | `puzzle_main`: `(7,2,4,5,0,6,8,3,1)` → `(1,2,3,4,5,6,7,8,0)`; `puzzle_transition`: `(1,4,3,7,0,6,5,8,2)` |
| 13 | Forward and backward problem formulation; backward search is conceptual, not an additional implemented algorithm |
| 16–18, 24–26 | `numbered_graph`: full BFS/DFS traversal; goal 8 for goal-directed comparisons |
| 19–21, 27–28 | `letter_graph`: original directed A–U graph, with shared L/P states and goal O |
| 22, 29 | `puzzle_walkthrough`: `(2,8,3,1,6,4,7,0,5)` → spiral goal `(1,2,3,8,0,4,7,6,5)`; optional DFS depth limit 5 |
| 30–31 | `weighted_graph`: shared state 6; UCS route `1 → 2 → 6`, cost 6 |
| 37–39 | Measured comparisons and conditional guarantees above |

The transition illustration has no specified goal, so it uses the standard
bottom-right-blank goal explicitly. Puzzle successor order is up, left, down,
right, following slide 11; consequently exact expansion numbers can differ from
the separate slide 22/29 trees. Blank tiles are excluded from Manhattan distance.
Start/goal inversion parity is checked before search.

TSP's heuristic is the MST cost over unvisited cities plus the cheapest
connection from the current city and back to A. With no unvisited cities, it
is the return-to-A cost. The original Königsberg graph has four odd-degree
vertices and no route using every bridge once; all algorithms exhaust it.
Parallel bridges remain separate transitions and separate used-edge bits.

Supplementary examples are `cyclic_graph`, `unreachable_graph`, and
`weighted_trap`. They demonstrate duplicate suppression, exhaustion, and the
difference between fewest actions and least cost.

### Corrections and trace conventions

- Slides 15/38 overgeneralize guarantees. BFS requires equal costs for cost
  optimality; DFS/greedy can be complete on finite graphs; A* needs heuristic
  conditions. The tables above state the relevant assumptions.
- Slide 34 adds heuristic estimates and gives Sibiu as 235 rather than slide
  33's 253. The implemented heuristic is 253 and the greedy route's actual road
  cost is `140 + 99 + 211 = 450`.
- Slide 35 describes `g` as an estimate. Here it is the actual accumulated cost.
- Repeated/misaligned BFS iteration numbers in slides 20/21 are not copied.
  CLI traces number actual selections starting at 1, show the remaining frontier
  before expansion, and show recent selected states first. A* reopenings may
  appear repeatedly in the visited history.
- Trace limits cap stored events and frontier/history snapshots. Larger totals
  and omitted events are identified explicitly. Full solution paths remain
  available through `run --json` even when terminal display is abbreviated.

## Python API

```python
from searches import SearchLimits, a_star_search
from searches.problems import get_problem

result = a_star_search(get_problem("romania"), limits=SearchLimits())
assert result.status == "found"
print(result.path, result.cost, result.stats.expanded)
```

Custom problems implement the `Problem` protocol: `initial`, `successors(state)`
yielding `Transition(action, state, cost)`, `is_goal(state)`, and
`heuristic(state)`. Results distinguish `found`, `no_solution`, `cutoff`, and
`traversed`; cutoffs include a reason. CLI `run` exits 0 for found/traversed, 1
for exhausted/cutoff, and 2 for invalid arguments. `compare` exits 0 when it
successfully creates a report, including expected no-solution/cutoff outcomes.
