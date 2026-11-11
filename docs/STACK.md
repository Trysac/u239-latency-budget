# Stack

## Used

| Tool | Why |
|---|---|
| Python >= 3.10 | The code uses union type syntax, `Literal`, frozen dataclasses, `MappingProxyType`, and `from __future__ import annotations`. |
| Python standard library | The package imports only `logging`, `re`, `collections.abc`, `dataclasses`, `math`, `types`, `typing`, and `__future__`; `allowed_dependencies` is empty. |
| pytest | The supplied test module in `tests/test_latency_budget.py` uses plain test functions and `pytest.raises`. |

## Discarded

| Tool | Why not |
|---|---|
| Runtime dependencies | The package has no runtime dependencies and no I/O. |
| Histogram sketches and external metrics clients | Out of scope: the library keeps per-window observation lists and computes nearest-rank percentiles directly. |
| Wall-clock schedulers | Out of scope: the caller closes windows. |
