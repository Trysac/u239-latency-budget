# Testing

## Running

```sh
python -m pytest tests/test_latency_budget.py
```

## Policy

- The supplied test module asserts return values and `LatencyBudgetError.code` values through the public import `latency_budget`.
- Tests are deterministic and do not use network, wall-clock scheduling, or external services.
- The supplied module contains tests for percentile calculation and `LatencyBudget` validation and construction.

## Tiers

- Local pytest tier: `tests/test_latency_budget.py`. No conformance markers, external tools, or CI-only setup are present in the supplied test module.

## Layout

- `tests/test_latency_budget.py` contains `test_percentile_acceptance_nearest_rank`, `test_percentile_single_value`, `test_percentile_empty_raises`, `test_percentile_invalid_p_raises`, `test_percentile_rank_rounding`, `test_latency_budget_valid`, `test_latency_budget_stages_immutable`, `test_latency_budget_total_ms_not_positive`, `test_latency_budget_stages_sum_exceeds_total`, `test_latency_budget_stage_negative_budget`, `test_latency_budget_stage_infinite_budget`, `test_latency_budget_invalid_stage_name`, `test_latency_budget_too_many_stages`, `test_latency_budget_from_dict_valid`, `test_latency_budget_from_dict_unknown_key`, `test_latency_budget_from_dict_missing_keys`, and `test_latency_budget_from_dict_invalid_types`.
