# Architecture

## Purpose

`trysac-latency-budget` is a dependency-free Python library for per-stage latency budgets, nearest-rank percentiles per observation window, unbudgeted time, and alerts with trigger and clear hysteresis.

## Shape

```text
caller code --> latency_budget (public API in src/latency_budget/__init__.py)
                    |
                    +-- percentile and LatencyBudget validation (pure)
                    +-- BudgetTracker (stateful, in-memory, no I/O)
```

- Public names are `Alert`, `BudgetTracker`, `LatencyBudget`, `LatencyBudgetError`, `WindowReport`, and `percentile`, as listed in `__all__`.
- `LatencyBudget` is a frozen dataclass with a mapping proxy for `stages`; it validates total and stage budgets, stage names, stage count, and the stage sum.
- `BudgetTracker` keeps per-window observation lists for each configured stage, `unbudgeted`, and `total`. It caps each window at `max_window_observations` and counts dropped observations.
- `close_window` computes nearest-rank percentiles for non-empty windows, compares each series to its budget, updates per-series trigger and clear counters, and returns a `WindowReport`.
- Errors are raised as `LatencyBudgetError` with a stable `.code`; the module also installs a `NullHandler` on its logger and performs no other logging or I/O.

## Quality contract

The supplied test module is `tests/test_latency_budget.py`; it imports the public package and uses `pytest.raises`. See [TESTING.md](TESTING.md).

## Decisions

No architecture decision records are included in the supplied tree. The implementation decisions are visible in `src/latency_budget/__init__.py`.
