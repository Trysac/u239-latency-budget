# Project record

## Objective

Provide per-stage latency budgets for request pipelines: split a total budget into stage budgets, compute nearest-rank percentiles per stage for each observation window, expose unbudgeted time, and emit alerts with trigger and clear hysteresis.

## Scope

- In scope: `percentile`, `LatencyBudget` validation and `from_dict`, `BudgetTracker.observe` and `BudgetTracker.close_window`, `WindowReport`, `Alert`, and `LatencyBudgetError` with stable error codes.
- In scope: nearest-rank percentiles, per-series alert state machines for each configured stage, `unbudgeted` and `total`, and the optional `on_event` callback.
- Out of scope: collecting timings, wall-clock window scheduling, histogram sketches, and multi-window burn rates. Callers feed observations and close windows.
- Out of scope: runtime dependencies, network I/O, file I/O, and persistence.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 1093079 / 50145 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.0799 |

## Factory run u239 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-10 | generation | deepseek-v4-pro | yes | 1663 | 14276 | 0 | 3200 | 0.0294 |
| 2026-11-10 | fix-1 | deepseek-flash | no | 12238 | 2007 | 0 | 77056 | 0.0033 |
| 2026-11-10 | audit | deepseek-flash | no | 17707 | 15174 | 0 | 213632 | 0.0124 |
| 2026-11-10 | fix-2 | deepseek-flash | no | 25994 | 4841 | 0 | 486400 | 0.0083 |
| 2026-11-10 | threat-model | deepseek-flash | no | 25027 | 4028 | 0 | 135936 | 0.0066 |
| 2026-11-10 | docs | deepseek-flash | no | 93970 | 9819 | 0 | 256 | 0.0200 |

Total: $0.0799. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
