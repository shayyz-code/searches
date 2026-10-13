"""Shared problem, result, limits, and trace interfaces."""

from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from math import isfinite
from typing import Literal, Protocol

type State = Hashable
type Status = Literal["found", "no_solution", "cutoff", "traversed"]


@dataclass(frozen=True, slots=True)
class Transition:
    action: str
    state: State
    cost: float = 1.0


class Problem(Protocol):
    """States must be immutable/hashable; successors must have stable ordering."""

    initial: State

    def successors(self, state: State) -> Iterable[Transition]: ...

    def is_goal(self, state: State) -> bool: ...

    def heuristic(self, state: State) -> float: ...


@dataclass(frozen=True, slots=True)
class SearchLimits:
    max_seconds: float = 30.0
    max_expansions: int = 250_000
    depth_limit: int | None = None

    def __post_init__(self) -> None:
        if not isfinite(self.max_seconds) or self.max_seconds <= 0:
            raise ValueError("max_seconds must be finite and positive")
        if self.max_expansions < 0:
            raise ValueError("max_expansions must be nonnegative")
        if self.depth_limit is not None and self.depth_limit < 0:
            raise ValueError("depth_limit must be nonnegative")


@dataclass(slots=True)
class SearchStats:
    expanded: int = 0
    generated: int = 1  # Includes the initial node and duplicate successors.
    peak_frontier: int = 1  # Includes stale heap entries until they are popped.
    retained_states: int = 1  # Peak distinct keys retained in the discovery map.
    elapsed_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class TraceEvent:
    iteration: int
    selected: State
    depth: int
    cost: float
    frontier: tuple[State, ...]
    visited: tuple[State, ...]
    frontier_total: int
    visited_total: int


@dataclass(slots=True)
class SearchResult:
    status: Status
    path: tuple[State, ...] = ()
    actions: tuple[str, ...] = ()
    cost: float | None = None
    stats: SearchStats = field(default_factory=SearchStats)
    visit_order: list[State] = field(default_factory=list)
    trace: list[TraceEvent] = field(default_factory=list)
    trace_truncated: bool = False
    cutoff_reason: str | None = None

    @property
    def depth(self) -> int | None:
        return len(self.actions) if self.status == "found" else None
