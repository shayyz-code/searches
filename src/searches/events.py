"""Optional execution events. No terminal dependencies or UI policy live here."""

from dataclasses import dataclass
from typing import Literal

from searches.core import SearchResult, State


@dataclass(frozen=True, slots=True)
class NodeInfo:
    node_id: int
    state: State
    parent_id: int | None
    action: str | None
    depth: int
    g: float
    h: float | None
    f: float | None


@dataclass(frozen=True, slots=True)
class StatsSnapshot:
    expanded: int
    generated: int
    peak_frontier: int
    retained_states: int
    elapsed_seconds: float
    frontier_size: int


@dataclass(frozen=True, slots=True)
class SearchEvent:
    kind: Literal[
        "queued", "initialized", "selected", "transition", "expanded", "stale", "finished"
    ]
    stats: StatsSnapshot
    node: NodeInfo | None = None
    target: NodeInfo | None = None
    edge_cost: float | None = None
    disposition: str | None = None
    result: SearchResult | None = None
