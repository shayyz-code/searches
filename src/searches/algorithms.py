"""Five deterministic graph searches, with shared instrumentation."""

import heapq
from collections import deque
from dataclasses import dataclass
from itertools import count, islice
from math import isfinite
from time import perf_counter

from searches.core import Problem, SearchLimits, SearchResult, SearchStats, State, TraceEvent

ALGORITHMS = ("bfs", "dfs", "ucs", "greedy", "astar")


@dataclass(slots=True)
class _Node:
    state: State
    parent: "_Node | None" = None
    action: str | None = None
    cost: float = 0.0
    depth: int = 0


def _path(node: _Node) -> tuple[tuple[State, ...], tuple[str, ...]]:
    states, actions = [], []
    while node is not None:
        states.append(node.state)
        if node.action is not None:
            actions.append(node.action)
        node = node.parent
    return tuple(reversed(states)), tuple(reversed(actions))


def search(
    problem: Problem,
    algorithm: str,
    *,
    limits: SearchLimits | None = None,
    trace: bool = False,
    trace_limit: int = 100,
    snapshot_limit: int = 20,
    traversal: bool = False,
) -> SearchResult:
    """Run a graph search. Full traversal is supported for BFS and DFS.

    UCS/A* retain best g values, so even expanded states can be reopened.
    Bounded DFS retains the shallowest discovered depth instead of a boolean
    visited flag. Unbounded DFS, BFS, and greedy discover each state once.
    Traces show the frontier *before* successor expansion, in selection order.
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    limits = limits or SearchLimits()
    if limits.depth_limit is not None and algorithm != "dfs":
        raise ValueError("depth_limit is only supported by DFS")
    if traversal and algorithm not in ("bfs", "dfs"):
        raise ValueError("Full traversal requires BFS or DFS")
    if trace_limit < 0 or snapshot_limit < 1:
        raise ValueError("trace_limit must be nonnegative and snapshot_limit positive")

    started = perf_counter()
    stats = SearchStats()
    result = SearchResult("no_solution", stats=stats)
    root = _Node(problem.initial)
    serial = count()
    queue: deque[_Node] = deque()
    stack: list[_Node] = []
    heap: list[tuple[float, int, _Node]] = []
    best: dict[State, float] = {root.state: 0.0}

    def score(node: _Node) -> float:
        return node.cost if algorithm in ("ucs", "astar") else float(node.depth)

    def push(node: _Node) -> None:
        if algorithm == "bfs":
            queue.append(node)
        elif algorithm == "dfs":
            stack.append(node)
        else:
            h = problem.heuristic(node.state) if algorithm in ("greedy", "astar") else 0.0
            if not isfinite(h) or h < 0:
                raise ValueError("Heuristics must be finite and nonnegative")
            priority = h if algorithm == "greedy" else node.cost + h
            if not isfinite(priority):
                raise ValueError("Search priority must be finite")
            heapq.heappush(heap, (priority, next(serial), node))

    def size() -> int:
        return len(queue) + len(stack) + len(heap)

    def finish(status: str, reason: str | None = None, node: _Node | None = None):
        result.status = status
        result.cutoff_reason = reason
        if node is not None:
            result.path, result.actions = _path(node)
            result.cost = node.cost
        stats.elapsed_seconds = perf_counter() - started
        return result

    push(root)
    depth_cutoff = False
    while size():
        if perf_counter() - started >= limits.max_seconds:
            return finish("cutoff", "time")
        node = (
            queue.popleft()
            if algorithm == "bfs"
            else stack.pop()
            if algorithm == "dfs"
            else heapq.heappop(heap)[2]
        )
        if score(node) != best[node.state]:
            continue
        result.visit_order.append(node.state)
        if trace:
            if len(result.trace) < trace_limit:
                if algorithm == "bfs":
                    frontier = [n.state for n in islice(queue, snapshot_limit)]
                elif algorithm == "dfs":
                    frontier = [n.state for n in stack[-snapshot_limit:][::-1]]
                else:
                    frontier = [entry[2].state for entry in heapq.nsmallest(snapshot_limit, heap)]
                result.trace.append(
                    TraceEvent(
                        len(result.visit_order),
                        node.state,
                        node.depth,
                        node.cost,
                        tuple(frontier),
                        tuple(result.visit_order[-snapshot_limit:][::-1]),
                        size(),
                        len(result.visit_order),
                    )
                )
            else:
                result.trace_truncated = True
        if not traversal and problem.is_goal(node.state):
            return finish("found", node=node)
        if stats.expanded >= limits.max_expansions:
            return finish("cutoff", "expansions")

        at_depth_limit = limits.depth_limit is not None and node.depth >= limits.depth_limit
        children = []
        if not at_depth_limit:
            stats.expanded += 1
        for transition in problem.successors(node.state):
            if perf_counter() - started >= limits.max_seconds:
                return finish("cutoff", "time")
            if not isfinite(transition.cost) or transition.cost < 0:
                raise ValueError("Step costs must be finite and nonnegative")
            stats.generated += 1
            child = _Node(
                transition.state,
                node,
                transition.action,
                node.cost + transition.cost,
                node.depth + 1,
            )
            if not isfinite(child.cost):
                raise ValueError("Accumulated cost must be finite")
            previous = best.get(child.state)
            improves = previous is None or (
                (algorithm in ("ucs", "astar") or limits.depth_limit is not None)
                and score(child) < previous
            )
            if not improves:
                continue
            if at_depth_limit:
                depth_cutoff = True
                continue
            best[child.state] = score(child)
            if algorithm == "dfs":
                children.append(child)
            else:
                push(child)
        if algorithm == "dfs":
            stack.extend(reversed(children))
        stats.peak_frontier = max(stats.peak_frontier, size())
        stats.retained_states = max(stats.retained_states, len(best))
    if depth_cutoff:
        return finish("cutoff", "depth")
    return finish("traversed" if traversal else "no_solution")


def breadth_first_search(problem: Problem, **kwargs) -> SearchResult:
    return search(problem, "bfs", **kwargs)


def depth_first_search(problem: Problem, **kwargs) -> SearchResult:
    return search(problem, "dfs", **kwargs)


def uniform_cost_search(problem: Problem, **kwargs) -> SearchResult:
    return search(problem, "ucs", **kwargs)


def greedy_best_first_search(problem: Problem, **kwargs) -> SearchResult:
    return search(problem, "greedy", **kwargs)


def a_star_search(problem: Problem, **kwargs) -> SearchResult:
    return search(problem, "astar", **kwargs)
