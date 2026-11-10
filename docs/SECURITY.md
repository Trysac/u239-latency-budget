# Security notes

## Threat model

### Defended

- The package is a pure in-memory library with no network, file, shell or environment access.
- Budgets are validated: `total_ms` is finite and greater than 0; stage budgets are finite and at least 0; the stage sum must not exceed `total_ms`; stage names match `[a-z][a-z0-9_]{0,39}`, are not `total` or `unbudgeted`, and are limited to 20 stages.
- Observations are validated: stage keys must be configured stages, timings are finite and at least 0, and `total_ms` is finite, at least 0, and not smaller than the stage sum.
- Tracker options are validated: `percentile` is in `(0, 100]`; `trigger_windows`, `clear_windows` and `max_window_observations` are positive integers; `on_event` is callable or `None`.
- The package does not use `eval`, `exec`, or deserialization beyond `LatencyBudget.from_dict`, which accepts a mapping with only `total_ms` and `stages`.
- The optional `on_event` callback receives only `event`, `stage`, `window`, `value_ms` and `budget_ms`; it does not receive request payloads or timings from `observe`.
- Per-window observation lists are bounded by `max_window_observations`; extras are counted in `WindowReport.dropped` and are not stored.

### Not defended

- The caller controls `max_window_observations`; the library does not impose an upper cap or a memory limit. Each tracker holds up to one list per configured series per open window.
- `on_event` runs synchronously in the caller process. Exceptions from the callback are not caught by the library, and the callback's own security properties are the caller's responsibility.
- The library does not authenticate, authorize, encrypt, or protect observations in transit or at rest. It performs no I/O and keeps no persistent state.
- Timing side channels, hostile custom `Mapping` implementations, and denial of service through very large configured observation limits are outside the library boundary.

## Publishing

The supplied code contains no release or publishing configuration. Publishing is outside the runtime behavior of the library.
