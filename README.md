# latency-budget

[![PyPI version](https://img.shields.io/pypi/v/trysac-latency-budget)](https://pypi.org/project/trysac-latency-budget/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-latency-budget)](LICENSE)
[![CI](https://github.com/Trysac/u239-latency-budget/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u239-latency-budget/actions/workflows/ci.yml)

Per-stage latency budgets for request pipelines: nearest-rank percentiles per window, unbudgeted time, and alerts with trigger and clear hysteresis

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-latency-budget
# or
uv add trysac-latency-budget
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import latency_budget

# normalize() trims surrounding whitespace and lower-cases the text.
print(latency_budget.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    latency_budget.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
