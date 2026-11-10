"""Tests for latency_budget."""

from __future__ import annotations

import pytest

from latency_budget import (
    Alert,
    BudgetTracker,
    LatencyBudget,
    LatencyBudgetError,
    percentile,
)

# --- percentile ---


def test_percentile_acceptance_nearest_rank() -> None:
    assert percentile(list(range(1, 21)), 95) == 19.0


def test_percentile_single_value() -> None:
    assert percentile([5.0], 99) == 5.0


def test_percentile_empty_raises() -> None:
    with pytest.raises(LatencyBudgetError) as exc_info:
        percentile([], 95)
    assert exc_info.value.code == "empty"


def test_percentile_invalid_p_raises() -> None:
    for p in [0, -1, 101, float("inf"), float("nan")]:
        with pytest.raises(LatencyBudgetError) as exc_info:
            percentile([1.0], p)
        assert exc_info.value.code == "invalid_percentile"


def test_percentile_rank_rounding() -> None:
    # ceil(p/100*n) rank
    values = [1, 2, 3, 4, 5]
    assert percentile(values, 50) == 3  # ceil(2.5) = 3 -> 3rd smallest = 3
    assert percentile(values, 20) == 1  # ceil(1) = 1 -> 1st = 1
    assert percentile(values, 99) == 5  # ceil(4.95) = 5 -> 5th = 5


# --- LatencyBudget ---


def test_latency_budget_valid() -> None:
    budget = LatencyBudget(total_ms=800, stages={"auth": 50, "db": 300, "render": 200})
    assert budget.total_ms == 800
    assert dict(budget.stages) == {"auth": 50, "db": 300, "render": 200}
    assert budget.unbudgeted_ms == 250


def test_latency_budget_stages_immutable() -> None:
    budget = LatencyBudget(total_ms=100, stages={"a": 50})
    with pytest.raises(TypeError):
        budget.stages["a"] = 60  # type: ignore[index]


def test_latency_budget_total_ms_not_positive() -> None:
    for total in [0, -1, float("inf"), float("nan")]:
        with pytest.raises(LatencyBudgetError) as exc_info:
            LatencyBudget(total_ms=total, stages={"a": 50})
        assert exc_info.value.code == "invalid_budget"


def test_latency_budget_stages_sum_exceeds_total() -> None:
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget(total_ms=800, stages={"auth": 500, "db": 400})
    assert exc_info.value.code == "invalid_budget"


def test_latency_budget_stage_negative_budget() -> None:
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget(total_ms=100, stages={"a": -1})
    assert exc_info.value.code == "invalid_budget"


def test_latency_budget_stage_infinite_budget() -> None:
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget(total_ms=100, stages={"a": float("inf")})
    assert exc_info.value.code == "invalid_budget"


def test_latency_budget_invalid_stage_name() -> None:
    invalid_names = ["Total", "TOTAL", "1abc", "abc-def", "", "a" * 41, "total", "unbudgeted"]
    for name in invalid_names:
        with pytest.raises(LatencyBudgetError) as exc_info:
            LatencyBudget(total_ms=100, stages={name: 50})
        assert exc_info.value.code == "invalid_budget"


def test_latency_budget_too_many_stages() -> None:
    stages = {f"stage_{i}": 1 for i in range(21)}
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget(total_ms=100, stages=stages)
    assert exc_info.value.code == "invalid_budget"


def test_latency_budget_from_dict_valid() -> None:
    budget = LatencyBudget.from_dict(
        {"total_ms": 800, "stages": {"auth": 50, "db": 300, "render": 200}}
    )
    assert budget.total_ms == 800
    assert budget.unbudgeted_ms == 250


def test_latency_budget_from_dict_unknown_key() -> None:
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget.from_dict({"total_ms": 100, "stages": {"a": 50}, "extra": 1})
    assert exc_info.value.code == "invalid_budget"


def test_latency_budget_from_dict_missing_keys() -> None:
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget.from_dict({"total_ms": 100})
    assert exc_info.value.code == "invalid_budget"
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget.from_dict({"stages": {"a": 50}})
    assert exc_info.value.code == "invalid_budget"


def test_latency_budget_from_dict_invalid_types() -> None:
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget.from_dict({"total_ms": "100", "stages": {"a": 50}})
    assert exc_info.value.code == "invalid_budget"
    with pytest.raises(LatencyBudgetError) as exc_info:
        LatencyBudget.from_dict({"total_ms": 100, "stages": "not_map"})
    assert exc_info.value.code == "invalid_budget"


# --- BudgetTracker ---


def _make_budget() -> LatencyBudget:
    return LatencyBudget(total_ms=800, stages={"auth": 50, "db": 300, "render": 200})


def test_budget_tracker_init_valid() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget)
    assert tracker._current_window == 1  # type: ignore[attr-defined]
    assert tracker._observations == 0  # type: ignore[attr-defined]


def test_budget_tracker_init_invalid_percentile() -> None:
    budget = _make_budget()
    for p in [0, -1, 101, float("inf"), float("nan")]:
        with pytest.raises(LatencyBudgetError) as exc_info:
            BudgetTracker(budget, percentile=p)
        assert exc_info.value.code == "invalid_options"


def test_budget_tracker_init_invalid_triggers() -> None:
    budget = _make_budget()
    with pytest.raises(LatencyBudgetError) as exc_info:
        BudgetTracker(budget, trigger_windows=0)
    assert exc_info.value.code == "invalid_options"
    with pytest.raises(LatencyBudgetError) as exc_info:
        BudgetTracker(budget, clear_windows=0)
    assert exc_info.value.code == "invalid_options"
    with pytest.raises(LatencyBudgetError) as exc_info:
        BudgetTracker(budget, max_window_observations=0)
    assert exc_info.value.code == "invalid_options"


def test_budget_tracker_init_invalid_on_event() -> None:
    budget = _make_budget()
    with pytest.raises(LatencyBudgetError) as exc_info:
        BudgetTracker(budget, on_event=42)  # type: ignore[arg-type]
    assert exc_info.value.code == "invalid_options"


def test_observe_valid_single() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget, percentile=95)
    tracker.observe({"auth": 40, "db": 350, "render": 100}, total_ms=600)
    # 600 - (40+350+100) = 110 unbudgeted
    assert tracker._series_lists["unbudgeted"] == [110.0]  # type: ignore[attr-defined]
    assert tracker._series_lists["total"] == [600.0]  # type: ignore[attr-defined]


def test_observe_missing_stage_counts_zero() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget)
    tracker.observe({"auth": 10}, total_ms=100)
    # db and render missing -> 0
    assert tracker._series_lists["db"] == [0.0]  # type: ignore[attr-defined]


def test_observe_unknown_stage_raises() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget)
    with pytest.raises(LatencyBudgetError) as exc_info:
        tracker.observe({"cache": 10})
    assert exc_info.value.code == "unknown_stage"


def test_observe_invalid_timing_negative() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget)
    with pytest.raises(LatencyBudgetError) as exc_info:
        tracker.observe({"auth": -1})
    assert exc_info.value.code == "invalid_timing"


def test_observe_invalid_timing_inf() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget)
    with pytest.raises(LatencyBudgetError) as exc_info:
        tracker.observe({"auth": float("inf")})
    assert exc_info.value.code == "invalid_timing"


def test_observe_total_ms_less_than_sum_raises() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget)
    with pytest.raises(LatencyBudgetError) as exc_info:
        tracker.observe({"auth": 40, "db": 350, "render": 100}, total_ms=400)
    assert exc_info.value.code == "invalid_timing"


def test_observe_total_ms_invalid() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget)
    with pytest.raises(LatencyBudgetError) as exc_info:
        tracker.observe({"auth": 10}, total_ms=float("nan"))
    assert exc_info.value.code == "invalid_timing"


def test_window_full_drop() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget, max_window_observations=3)
    for _ in range(4):
        tracker.observe({"auth": 10}, total_ms=20)
    report = tracker.close_window()
    assert report.count == 3
    assert report.dropped == 1


def test_close_window_empty() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget)
    report = tracker.close_window()
    assert report.window == 1
    assert report.count == 0
    assert report.dropped == 0
    assert report.values == {}
    assert report.over == ()
    assert report.alerts == ()
    # Window number advances
    report2 = tracker.close_window()
    assert report2.window == 2


def test_alerting_firing_and_resolution() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget, percentile=50, trigger_windows=2, clear_windows=2)

    # Window 1: db over (350 > 300), but only one over, no alert
    tracker.observe({"auth": 40, "db": 350, "render": 100}, total_ms=600)
    report1 = tracker.close_window()
    assert report1.alerts == ()
    assert report1.over == ("db",)  # db over, unbudgeted 110 (not over), total 600 < 800 not over
    assert report1.values["db"] == 350.0

    # Window 2: db over again -> firing
    tracker.observe({"auth": 40, "db": 350, "render": 100}, total_ms=600)
    report2 = tracker.close_window()
    assert len(report2.alerts) == 1
    alert = report2.alerts[0]
    assert alert == Alert(stage="db", state="firing", window=2, value_ms=350.0, budget_ms=300.0)

    # Window 3: db over again but already firing, no alert
    tracker.observe({"auth": 40, "db": 350, "render": 100}, total_ms=600)
    report3 = tracker.close_window()
    assert report3.alerts == ()

    # Window 4: db within (200), first within, no resolution
    # (unbudgeted is 400 - 340 = 60 ms, well within its 250 ms budget)
    tracker.observe({"auth": 40, "db": 200, "render": 100}, total_ms=400)
    report4 = tracker.close_window()
    assert report4.alerts == ()

    # Window 5: db within again -> resolved
    tracker.observe({"auth": 40, "db": 200, "render": 100}, total_ms=400)
    report5 = tracker.close_window()
    assert len(report5.alerts) == 1
    alert = report5.alerts[0]
    assert alert == Alert(stage="db", state="resolved", window=5, value_ms=200.0, budget_ms=300.0)


def test_trigger_windows_one() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget, trigger_windows=1, percentile=50)
    tracker.observe({"db": 350}, total_ms=400)
    report = tracker.close_window()
    assert len(report.alerts) == 1
    assert report.alerts[0].state == "firing"


def test_empty_window_does_not_reset_counters() -> None:
    budget = _make_budget()
    tracker = BudgetTracker(budget, trigger_windows=2, clear_windows=2, percentile=50)
    # Window 1: over
    tracker.observe({"db": 350}, total_ms=400)
    tracker.close_window()
    # Empty window (should not reset consecutive_over)
    tracker.close_window()
    # Window 2 (actually window 3): over again -> firing
    tracker.observe({"db": 350}, total_ms=400)
    report = tracker.close_window()
    assert len(report.alerts) == 1
    assert report.alerts[0].state == "firing"


def test_equal_budget_not_over() -> None:
    budget = LatencyBudget(total_ms=100, stages={"a": 50})
    tracker = BudgetTracker(budget, trigger_windows=1, percentile=50)
    tracker.observe({"a": 50})  # exactly equal
    report = tracker.close_window()
    assert report.over == ()
    assert report.alerts == ()


def test_zero_ms_stage_never_over() -> None:
    budget = LatencyBudget(total_ms=100, stages={"a": 0})
    tracker = BudgetTracker(budget, trigger_windows=1, percentile=50)
    tracker.observe({"a": 0})
    report = tracker.close_window()
    assert "a" not in report.over
    assert report.values["a"] == 0.0


def test_on_event_callback() -> None:
    budget = _make_budget()
    events: list[dict[str, object]] = []
    tracker = BudgetTracker(
        budget, percentile=50, trigger_windows=1, clear_windows=1, on_event=events.append
    )
    # Firing
    tracker.observe({"db": 350}, total_ms=400)
    tracker.close_window()
    assert len(events) == 1
    assert events[0] == {
        "event": "firing",
        "stage": "db",
        "window": 1,
        "value_ms": 350.0,
        "budget_ms": 300.0,
    }
    # Resolution
    tracker.observe({"db": 200}, total_ms=300)
    tracker.close_window()
    assert len(events) == 2
    assert events[1] == {
        "event": "resolved",
        "stage": "db",
        "window": 2,
        "value_ms": 200.0,
        "budget_ms": 300.0,
    }


def test_alerts_ordering() -> None:
    budget = LatencyBudget(total_ms=100, stages={"z": 30, "a": 20, "b": 10})
    tracker = BudgetTracker(budget, trigger_windows=1, percentile=50)
    # Make all series over: total >100, unbudgeted >40, each stage > budget
    tracker.observe({"z": 50, "a": 30, "b": 20}, total_ms=200)
    report = tracker.close_window()
    # Over should include all and be in order: z, a, b, unbudgeted, total
    assert report.over == ("z", "a", "b", "unbudgeted", "total")
    # Alerts should be in same order
    stages_alerted = [alert.stage for alert in report.alerts]
    assert stages_alerted == ["z", "a", "b", "unbudgeted", "total"]
