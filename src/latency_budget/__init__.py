"""Per-stage latency budgets for request pipelines.

This module provides utilities to split a total latency budget into
per-stage budgets, compute nearest-rank percentiles per observation window,
and emit alerts with hysteresis when a stage exceeds its budget.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import ceil, isfinite
from types import MappingProxyType
from typing import Literal

__all__ = [
    "Alert",
    "BudgetTracker",
    "LatencyBudget",
    "LatencyBudgetError",
    "WindowReport",
    "percentile",
]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class LatencyBudgetError(Exception):
    """Error raised by latency_budget functions.

    Attributes:
        code: Stable machine-readable error code.
        message: Optional human-readable description.
    """

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message
        super().__init__(message if message else code)


def percentile(values: Sequence[float], p: float) -> float:
    """Return the nearest-rank percentile of ``values``.

    Implements the nearest-rank method: sort ``values`` ascending, then
    return the value at rank ``max(1, ceil(p / 100 * n))``.

    Args:
        values: Sequence of numeric values (at least one element).
        p: Percentile in the interval ``(0, 100]``.

    Returns:
        The percentile value as a float.

    Raises:
        LatencyBudgetError: If ``p`` is outside ``(0, 100]`` (code
            ``'invalid_percentile'``) or if ``values`` is empty (code
            ``'empty'``).
    """
    if not isinstance(p, (int, float)) or not isfinite(p) or p <= 0 or p > 100:
        raise LatencyBudgetError("invalid_percentile", "p must be in (0, 100]")
    if not values:
        raise LatencyBudgetError("empty", "values must not be empty")
    n = len(values)
    rank = max(1, ceil(p / 100 * n))
    sorted_values = sorted(values)
    return sorted_values[rank - 1]


_STAGE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_RESERVED_NAMES = {"total", "unbudgeted"}
_MAX_STAGES = 20


@dataclass(frozen=True)
class LatencyBudget:
    """Immutable definition of total and per-stage latency budgets.

    Args:
        total_ms: Overall budget in milliseconds (must be > 0 and finite).
        stages: Mapping of stage name to its budget in milliseconds.
            Stage names must match ``[a-z][a-z0-9_]{0,39}``, must not be
            ``'total'`` or ``'unbudgeted'``, at most 20 stages, and the
            sum of stage budgets must not exceed ``total_ms``.

    Attributes:
        total_ms: Total budget.
        stages: Immutable mapping of stage budgets.
        unbudgeted_ms: Remaining budget after subtracting stage budgets.
    """

    total_ms: float
    stages: Mapping[str, float]

    def __post_init__(self) -> None:
        # Validate total_ms
        if (
            not isinstance(self.total_ms, (int, float))
            or not isfinite(self.total_ms)
            or self.total_ms <= 0
        ):
            raise LatencyBudgetError("invalid_budget", "total_ms must be finite and > 0")
        # Validate stages is a mapping
        if not isinstance(self.stages, Mapping):
            raise LatencyBudgetError("invalid_budget", "stages must be a mapping")
        stages = dict(self.stages)
        if len(stages) > _MAX_STAGES:
            raise LatencyBudgetError("invalid_budget", f"at most {_MAX_STAGES} stages allowed")
        # Validate each stage
        total_stage_budget = 0.0
        for name, value in stages.items():
            if (
                not isinstance(name, str)
                or not _STAGE_NAME_RE.fullmatch(name)
                or name in _RESERVED_NAMES
            ):
                raise LatencyBudgetError("invalid_budget", f"invalid stage name: {name!r}")
            if not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise LatencyBudgetError(
                    "invalid_budget", f"stage {name!r} budget must be finite and >= 0"
                )
            total_stage_budget += value
        if total_stage_budget > self.total_ms:
            raise LatencyBudgetError(
                "invalid_budget", "sum of stage budgets must not exceed total_ms"
            )
        # Replace stages with an immutable mapping proxy
        object.__setattr__(self, "stages", MappingProxyType(stages))

    @property
    def unbudgeted_ms(self) -> float:
        """Return the portion of the total budget not assigned to stages."""
        return self.total_ms - sum(self.stages.values())

    @classmethod
    def from_dict(cls, d: Mapping[str, object]) -> LatencyBudget:
        """Create a LatencyBudget from a dictionary.

        The dictionary must contain exactly the keys ``'total_ms'`` (a
        finite positive number) and ``'stages'`` (a mapping). Any other
        key raises ``LatencyBudgetError`` with code ``'invalid_budget'``.

        Args:
            d: Mapping with keys ``'total_ms'`` and ``'stages'``.

        Returns:
            A new LatencyBudget instance.

        Raises:
            LatencyBudgetError: If ``d`` contains unknown keys, if required
                keys are missing, or if values are invalid.
        """
        allowed = {"total_ms", "stages"}
        if any(k not in allowed for k in d):
            raise LatencyBudgetError("invalid_budget", "unknown key in dictionary")
        if "total_ms" not in d or not isinstance(d["total_ms"], (int, float)):
            raise LatencyBudgetError("invalid_budget", "total_ms must be a number")
        if "stages" not in d or not isinstance(d["stages"], Mapping):
            raise LatencyBudgetError("invalid_budget", "stages must be a mapping")
        return cls(total_ms=d["total_ms"], stages=d["stages"])


@dataclass(frozen=True)
class Alert:
    """An alert emitted by BudgetTracker.

    Attributes:
        stage: Series name (stage, 'unbudgeted', or 'total').
        state: Either 'firing' or 'resolved'.
        window: Window number in which the alert was emitted.
        value_ms: Percentile value that triggered the alert.
        budget_ms: The budget against which the value was compared.
    """

    stage: str
    state: Literal["firing", "resolved"]
    window: int
    value_ms: float
    budget_ms: float


@dataclass(frozen=True)
class WindowReport:
    """Result of closing an observation window.

    Attributes:
        window: Window number (1-based).
        count: Number of observations accepted in this window.
        dropped: Number of observations dropped because the window was full.
        values: Percentile value per series for non-empty windows.
        over: Tuple of series names whose percentile exceeded budget.
        alerts: Tuple of Alert objects emitted when the window closed.
    """

    window: int
    count: int
    dropped: int
    values: dict[str, float]
    over: tuple[str, ...]
    alerts: tuple[Alert, ...]


class BudgetTracker:
    """Tracks latency observations and emits alerts on consecutive breaches.

    The tracker maintains a per-series state machine:

    * States: ``ok`` and ``firing``.
    * A window is "over" for a series when its percentile exceeds its budget.
    * Transition from ``ok`` to ``firing`` occurs after ``trigger_windows``
      consecutive over windows.
    * Transition from ``firing`` to ``ok`` occurs after ``clear_windows``
      consecutive within (not over) windows.
    * An over window resets the within counter; a within window resets the
      over counter.
    * Empty windows do not change any counters or states.

    Args:
        budget: LatencyBudget defining total and stage budgets.
        percentile: Percentile to compute per window (default 95).
        trigger_windows: Consecutive over windows before firing (default 2).
        clear_windows: Consecutive within windows before resolving (default 2).
        max_window_observations: Maximum observations buffered per window
            (default 100_000). Excess observations are dropped.
        on_event: Optional callback, called with an event dict when an alert
            is emitted. The dict contains 'event', 'stage', 'window',
            'value_ms', and 'budget_ms'.
    """

    def __init__(
        self,
        budget: LatencyBudget,
        *,
        percentile: float = 95,
        trigger_windows: int = 2,
        clear_windows: int = 2,
        max_window_observations: int = 100_000,
        on_event: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        # Validate options
        if (
            not isinstance(percentile, (int, float))
            or not isfinite(percentile)
            or percentile <= 0
            or percentile > 100
        ):
            raise LatencyBudgetError("invalid_options", "percentile must be in (0, 100]")
        if not isinstance(trigger_windows, int) or trigger_windows < 1:
            raise LatencyBudgetError(
                "invalid_options", "trigger_windows must be a positive integer"
            )
        if not isinstance(clear_windows, int) or clear_windows < 1:
            raise LatencyBudgetError("invalid_options", "clear_windows must be a positive integer")
        if not isinstance(max_window_observations, int) or max_window_observations < 1:
            raise LatencyBudgetError(
                "invalid_options", "max_window_observations must be a positive integer"
            )
        if on_event is not None and not callable(on_event):
            raise LatencyBudgetError("invalid_options", "on_event must be callable")

        self._budget = budget
        self._percentile = percentile
        self._trigger_windows = trigger_windows
        self._clear_windows = clear_windows
        self._max_window_observations = max_window_observations
        self._on_event = on_event

        # Build series order: stages in budget order, then unbudgeted, then total
        self._series_order: list[str] = [*budget.stages, "unbudgeted", "total"]
        self._budget_values: dict[str, float] = {
            **dict(budget.stages),
            "unbudgeted": budget.unbudgeted_ms,
            "total": budget.total_ms,
        }

        # Per-window state
        self._current_window = 1
        self._observations = 0
        self._dropped = 0
        self._series_lists: dict[str, list[float]] = {name: [] for name in self._series_order}

        # Alert state machine
        self._consecutive_over: dict[str, int] = {name: 0 for name in self._series_order}
        self._consecutive_within: dict[str, int] = {name: 0 for name in self._series_order}
        self._firing: dict[str, bool] = {name: False for name in self._series_order}

    def observe(
        self,
        timings: Mapping[str, float],
        *,
        total_ms: float | None = None,
    ) -> None:
        """Record one observation of per-stage timings.

        Each observation contributes one value per configured stage (missing
        stages are treated as 0 ms), one for ``'unbudgeted'`` (``total_ms -
        sum(stages)``), and one for ``'total'``.

        Args:
            timings: Mapping of stage name to observed milliseconds.
                Keys must be a subset of the configured stage names.
            total_ms: Overall request latency. If omitted, defaults to the
                sum of the stage timings. Must be >= the stage sum.

        Raises:
            LatencyBudgetError: If a timing key is not a configured stage
                ('unknown_stage'), if a timing is invalid ('invalid_timing'),
                or if ``total_ms`` is invalid ('invalid_timing').
        """
        # Validate total_ms
        stage_sum = 0.0
        for name, value in timings.items():
            if not isinstance(name, str) or name not in self._budget.stages:
                raise LatencyBudgetError("unknown_stage", f"unknown stage: {name!r}")
            if not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise LatencyBudgetError(
                    "invalid_timing", f"timing for {name!r} must be finite and >= 0"
                )
            stage_sum += value

        if total_ms is None:
            total_ms = stage_sum
        else:
            if not isinstance(total_ms, (int, float)) or not isfinite(total_ms) or total_ms < 0:
                raise LatencyBudgetError("invalid_timing", "total_ms must be finite and >= 0")
            if total_ms < stage_sum:
                raise LatencyBudgetError(
                    "invalid_timing", "total_ms must be >= sum of stage timings"
                )

        # Check window capacity
        if self._observations >= self._max_window_observations:
            self._dropped += 1
            return

        # Add observation to all series
        self._observations += 1
        for stage_name in self._budget.stages:
            value = timings.get(stage_name, 0.0)
            self._series_lists[stage_name].append(value)
        unbudgeted = total_ms - stage_sum
        self._series_lists["unbudgeted"].append(unbudgeted)
        self._series_lists["total"].append(total_ms)

    def close_window(self) -> WindowReport:
        """Close the current window, compute report, and advance to next.

        Returns:
            WindowReport describing the just-closed window.
        """
        window = self._current_window
        count = self._observations
        dropped = self._dropped

        # Empty window: no values, no alerts, no state changes
        if count == 0:
            self._advance_window()
            return WindowReport(
                window=window,
                count=0,
                dropped=0,
                values={},
                over=(),
                alerts=(),
            )

        # Compute percentiles for each series
        values: dict[str, float] = {}
        for name in self._series_order:
            values[name] = percentile(self._series_lists[name], self._percentile)

        # Determine which series are over budget
        over: list[str] = []
        for name in self._series_order:
            if values[name] > self._budget_values[name]:
                over.append(name)

        # Update state machine and generate alerts
        alerts: list[Alert] = []
        for name in self._series_order:
            is_over = name in over
            if is_over:
                self._consecutive_within[name] = 0
                self._consecutive_over[name] += 1
                if not self._firing[name] and self._consecutive_over[name] >= self._trigger_windows:
                    self._firing[name] = True
                    alert = Alert(
                        stage=name,
                        state="firing",
                        window=window,
                        value_ms=values[name],
                        budget_ms=self._budget_values[name],
                    )
                    alerts.append(alert)
                    if self._on_event is not None:
                        self._on_event(
                            {
                                "event": "firing",
                                "stage": name,
                                "window": window,
                                "value_ms": values[name],
                                "budget_ms": self._budget_values[name],
                            }
                        )
            else:
                self._consecutive_over[name] = 0
                self._consecutive_within[name] += 1
                if self._firing[name] and self._consecutive_within[name] >= self._clear_windows:
                    self._firing[name] = False
                    alert = Alert(
                        stage=name,
                        state="resolved",
                        window=window,
                        value_ms=values[name],
                        budget_ms=self._budget_values[name],
                    )
                    alerts.append(alert)
                    if self._on_event is not None:
                        self._on_event(
                            {
                                "event": "resolved",
                                "stage": name,
                                "window": window,
                                "value_ms": values[name],
                                "budget_ms": self._budget_values[name],
                            }
                        )

        # Prepare report
        report = WindowReport(
            window=window,
            count=count,
            dropped=dropped,
            values=values,
            over=tuple(over),
            alerts=tuple(alerts),
        )

        # Advance to next window
        self._advance_window()
        return report

    def _advance_window(self) -> None:
        """Reset per-window state and increment window number."""
        self._current_window += 1
        self._observations = 0
        self._dropped = 0
        for name in self._series_order:
            self._series_lists[name].clear()
