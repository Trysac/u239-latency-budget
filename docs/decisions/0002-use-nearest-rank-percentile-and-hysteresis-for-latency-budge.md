# Use nearest-rank percentile and hysteresis for latency budget alerts

Status: accepted (generated, pending human review)

## Context

The latency budget utility needs to compute percentiles per observation window and alert when a stage exceeds its budget. The specification requires avoiding flapping and identifying the specific stage that consumed the budget.

## Decision

Implement percentile using the nearest-rank method (sort ascending and take the ceil(p/100 * n)-th value). Use a state machine with consecutive over/within counters for each series (stage, unbudgeted, total) to provide hysteresis: firing after trigger_windows consecutive over windows, resolving after clear_windows consecutive within windows. Empty windows do not affect counters.

## Consequences

The implementation is deterministic and simple. Nearest-rank avoids interpolation and is suitable for latency percentiles. Hysteresis prevents flapping but introduces a delay in both alerting and resolution, which is acceptable for the use case. The state machine is bounded by the number of series and window observations, and per-window observations are explicitly capped.
