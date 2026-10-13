from dataclasses import FrozenInstanceError, asdict

import pytest

from searches import SearchLimits, search
from searches.algorithms import ALGORITHMS
from searches.animation.model import WalkthroughModel
from searches.problems import PROBLEMS, get_problem
from searches.problems.graph import GraphProblem


@pytest.mark.parametrize("name", PROBLEMS)
@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_observer_preserves_every_problem_and_algorithm(name, algorithm):
    limits = SearchLimits(max_expansions=100)
    plain = search(get_problem(name), algorithm, limits=limits, trace=True)
    events = []
    observed = search(
        get_problem(name), algorithm, limits=limits, trace=True, on_event=events.append
    )
    assert (
        observed.status,
        observed.cutoff_reason,
        observed.path,
        observed.actions,
        observed.cost,
    ) == (plain.status, plain.cutoff_reason, plain.path, plain.actions, plain.cost)
    assert observed.visit_order == plain.visit_order
    assert observed.trace == plain.trace
    for key, value in asdict(plain.stats).items():
        if key != "elapsed_seconds":
            assert getattr(observed.stats, key) == value
    assert events[0].kind == "queued"
    assert events[1].kind == "initialized"
    assert events[-1].kind == "finished"
    assert events[-1].result is observed
    assert [e.node.state for e in events if e.kind == "selected"] == plain.visit_order
    model = WalkthroughModel(algorithm)
    for event in events:
        model.apply(event)
        if event.kind == "expanded":
            assert model.stats.frontier_size == len(model.frontier)
    assert model.result is observed
    assert len(model.history) == len(observed.visit_order)
    assert model.event_count == len(events)
    assert model.stats.expanded == observed.stats.expanded


def test_clock_excludes_observer_wait_and_still_limits_algorithm_work(monkeypatch):
    class Clock:
        now = 0.0

    clock = Clock()
    monkeypatch.setattr("searches.algorithms.perf_counter", lambda: clock.now)

    class SlowGraph(GraphProblem):
        def successors(self, state):
            for edge in super().successors(state):
                clock.now += 0.1
                yield edge

    graph = SlowGraph({"S": (("A", 1),), "A": (("G", 1),)}, "S", "G")

    def wait(event):
        clock.now += 600

    result = search(graph, "bfs", on_event=wait, limits=SearchLimits(max_seconds=0.5))
    assert result.status == "found"
    assert result.stats.elapsed_seconds == pytest.approx(0.2, abs=1e-8)
    result = search(graph, "bfs", on_event=wait, limits=SearchLimits(max_seconds=0.15))
    assert (result.status, result.cutoff_reason) == ("cutoff", "time")
    assert result.stats.elapsed_seconds == pytest.approx(0.2, abs=1e-8)


def test_reopening_stale_entries_and_priority_frontier():
    graph = GraphProblem(
        {"S": (("A", 2), ("B", 2)), "A": (("C", 2),), "B": (("C", 1),), "C": (("G", 5),)},
        "S",
        "G",
        {"S": 0, "A": 0, "B": 6, "C": 0, "G": 0},
    )
    events = []
    result = search(graph, "astar", on_event=events.append)
    assert result.cost == 8
    selected = [e.node for e in events if e.kind == "selected" and e.node.state == "C"]
    assert len(selected) == 2 and selected[0].node_id != selected[1].node_id
    model = WalkthroughModel("astar")
    for event in events:
        model.apply(event)
        page = model.frontier_page(0, 10)
        assert [n.f for n in page] == sorted(n.f for n in page)
    assert len({n.node_id for n in model.history}) == len(model.history)
    with pytest.raises(FrozenInstanceError):
        events[0].stats.expanded = 20
    stale = []
    search(
        GraphProblem({"S": (("A", 10), ("B", 1)), "B": (("A", 1),), "A": (("G", 20),)}, "S", "G"),
        "ucs",
        on_event=stale.append,
    )
    assert any(e.kind == "stale" and e.node.state == "A" for e in stale)
    model = WalkthroughModel("ucs")
    saw_stale = False
    for event in stale:
        model.apply(event)
        saw_stale |= any(model.is_stale(node) for node in model.frontier_page(0, 10))
    assert saw_stale


def test_bounded_dfs_and_uncapped_animation_events():
    graph = GraphProblem(
        {
            "S": (("A", 1), ("D", 1)),
            "A": (("B", 1),),
            "B": (("X", 1),),
            "D": (("X", 1),),
            "X": (("G", 1),),
        },
        "S",
        "G",
    )
    events = []
    result = search(graph, "dfs", on_event=events.append, limits=SearchLimits(depth_limit=3))
    assert result.path == ("S", "D", "X", "G")
    graph = GraphProblem({i: ((i + 1, 1),) for i in range(250)}, 0, 250)
    events = []
    result = search(graph, "bfs", trace=True, trace_limit=2, on_event=events.append)
    assert result.trace_truncated and len(result.trace) == 2
    assert len([e for e in events if e.kind == "selected"]) == 251


def test_unobserved_search_and_benchmark_never_construct_events(monkeypatch):
    from searches.comparisons import benchmark

    def fail(*args, **kwargs):
        raise AssertionError("Unobserved execution created animation metadata")

    monkeypatch.setattr("searches.algorithms.SearchEvent", fail)
    search(get_problem("romania"), "astar")
    assert benchmark("romania", "astar", repeats=1)["cost"] == 418
