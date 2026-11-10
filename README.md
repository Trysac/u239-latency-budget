# latency-budget

[![PyPI version](https://img.shields.io/pypi/v/trysac-latency-budget)](https://pypi.org/project/trysac-latency-budget/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-latency-budget)](LICENSE)
[![CI](https://github.com/Trysac/u239-latency-budget/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u239-latency-budget/actions/workflows/ci.yml)

Per-stage latency budgets for request pipelines: nearest-rank percentiles per window, unbudgeted time, and alerts with trigger and clear hysteresis

## Problem

A request that must answer in 800 ms passes through authentication, database, model calls and rendering. When it gets slow, an end-to-end latency alert only says that something is slow, not which stage spent the budget, and it flaps when a percentile hovers at the limit. This library splits a total budget into per-stage budgets, computes nearest-rank percentiles per stage for each observation window, exposes unbudgeted time, and raises alerts after consecutive breaches and resolves them after consecutive recoveries.

## Install

```sh
pip install trysac-latency-budget
```

Requires Python 3.10 or newer. The package has no runtime dependencies.

## Usage

```python
from latency_budget import BudgetTracker, LatencyBudget

budget = LatencyBudget(total_ms=800, stages={"auth": 50, "db": 300})
tracker = BudgetTracker(budget, trigger_windows=1)
tracker.observe({"auth": 20, "db": 400}, total_ms=420)
report = tracker.close_window()
print(report.alerts[0].stage, report.alerts[0].state)
```

Public API:

- `percentile(values, p)` returns the nearest-rank percentile of a non-empty numeric sequence. `p` must be in `(0, 100]`; violations raise `LatencyBudgetError` with code `invalid_percentile`, and an empty sequence raises code `empty`.
- `LatencyBudget(total_ms, stages)` is a frozen dataclass. `total_ms` must be finite and greater than 0. Stage names must match `[a-z][a-z0-9_]{0,39}`, must not be `total` or `unbudgeted`, there may be at most 20 stages, each budget must be finite and at least 0, and the stage sum must not exceed `total_ms`. It exposes `unbudgeted_ms` and `from_dict(d)`; unknown dictionary keys raise code `invalid_budget`.
- `BudgetTracker(budget, *, percentile=95, trigger_windows=2, clear_windows=2, max_window_observations=100_000, on_event=None)` buffers observations and emits alerts. `percentile` must be in `(0, 100]`; `trigger_windows`, `clear_windows` and `max_window_observations` must be positive integers; `on_event` must be callable or `None`. Invalid options raise code `invalid_options`.
- `observe(timings, *, total_ms=None)` accepts a subset of the configured stages; missing stages count as 0 ms. Timings must be finite and at least 0. Unknown stage names raise `unknown_stage`; invalid timings or a `total_ms` smaller than the stage sum raise `invalid_timing`. Omitted `total_ms` defaults to the stage sum.
- `close_window()` returns a `WindowReport` with the window number, accepted and dropped observation counts, the percentile value per series, the series over budget, and emitted `Alert` objects. Windows are numbered from 1 and advance on every close, including empty windows. A value equal to its budget is not over budget. Alerts are ordered as configured stages in budget order, then `unbudgeted`, then `total`.
- `Alert(stage, state, window, value_ms, budget_ms)` represents a `firing` or `resolved` alert. A series fires after `trigger_windows` consecutive over-budget windows and resolves after `clear_windows` consecutive within-budget windows. An empty window does not change counters or states.
- `LatencyBudgetError` carries a stable `.code` attribute with one of `empty`, `invalid_percentile`, `invalid_budget`, `unknown_stage`, `invalid_timing`, `invalid_options`.

## Why not an end-to-end SLO alert

An end-to-end SLO alert reports that the whole request is slow and flaps when a percentile crosses the limit. This library reports which stage exceeded its own budget and applies trigger and clear hysteresis, so a single marginal window does not fire or resolve an alert.

## Documentation

- [Project record](docs/PROJECT.md) and [architecture](docs/ARCHITECTURE.md)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Stack](docs/STACK.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
