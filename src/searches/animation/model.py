"""Incremental view state with a paged frontier, rather than frame snapshots."""

import heapq
from collections import Counter, deque
from itertools import islice

from searches.events import NodeInfo, SearchEvent


class WalkthroughModel:
    def __init__(self, algorithm: str):
        self.algorithm = algorithm
        self.nodes: dict[int, NodeInfo] = {}
        self.frontier: dict[int, NodeInfo] = {}
        self.frontier_states = Counter()
        self.best_scores = {}
        self.visited = set()
        self.history: list[NodeInfo] = []
        self.queue = deque()
        self.stack = []
        self.heap = []
        self.serial = 0
        self.current: NodeInfo | None = None
        self.previous: NodeInfo | None = None
        self.transitions: list[SearchEvent] = []
        self.stats = None
        self.result = None
        self.solution_nodes = []
        self.event_count = 0
        self.steps = 0

    def apply(self, event: SearchEvent) -> None:
        self.event_count += 1
        self.stats = event.stats
        node = event.node
        if event.kind == "queued":
            self.nodes[node.node_id] = node
            self.frontier[node.node_id] = node
            self.frontier_states[node.state] += 1
            self.best_scores[node.state] = (
                node.g if self.algorithm in ("ucs", "astar") else node.depth
            )
            if self.algorithm == "bfs":
                self.queue.append(node.node_id)
            elif self.algorithm == "dfs":
                self.stack.append(node.node_id)
            else:
                heapq.heappush(self.heap, (node.f, self.serial, node.node_id))
                self.serial += 1
        elif event.kind in ("selected", "stale"):
            self.frontier.pop(node.node_id)
            self.frontier_states[node.state] -= 1
            if self.frontier_states[node.state] == 0:
                del self.frontier_states[node.state]
            if self.algorithm == "bfs":
                assert self.queue.popleft() == node.node_id
            elif self.algorithm == "dfs":
                assert self.stack.pop() == node.node_id
            else:
                assert heapq.heappop(self.heap)[2] == node.node_id
            if event.kind == "selected":
                self.previous, self.current = self.current, node
                self.history.append(node)
                self.visited.add(node.state)
                self.transitions.clear()
                self.steps += 1
        elif event.kind == "transition":
            self.transitions.append(event)
        elif event.kind == "initialized":
            self.current = node
        elif event.kind == "finished":
            self.result = event.result
            if self.result.status == "found":
                self.solution_nodes = self.route()

    def frontier_page(self, offset: int, count: int) -> list[NodeInfo]:
        if self.algorithm == "bfs":
            ids = list(islice(self.queue, offset, offset + count))
        elif self.algorithm == "dfs":
            ids = list(islice(reversed(self.stack), offset, offset + count))
        else:
            # Inspect the actual heap prefix in O((offset + count) log F),
            # without copying or sorting the entire frontier on every redraw.
            prefix = [heapq.heappop(self.heap) for _ in range(min(offset + count, len(self.heap)))]
            ids = [entry[2] for entry in prefix[offset:]]
            for entry in prefix:
                heapq.heappush(self.heap, entry)
        return [self.frontier[node_id] for node_id in ids]

    def route(self) -> list[NodeInfo]:
        nodes = []
        node = self.current
        while node is not None:
            nodes.append(node)
            node = self.nodes.get(node.parent_id)
        return nodes[::-1]

    def is_stale(self, node: NodeInfo) -> bool:
        score = node.g if self.algorithm in ("ucs", "astar") else node.depth
        return score != self.best_scores[node.state]
