"""
Test-mode hooks for Pixil (PIXIL_TEST_MODE=1 only).

When the environment variable is unset, is_test_mode() is False and all
record_* functions are no-ops — no measurable impact on lightshow runs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

_ENV_FLAG = "PIXIL_TEST_MODE"

# Cap rests in test mode (seconds) so Tier 2 finishes quickly.
REST_CAP_SECONDS = float(os.environ.get("PIXIL_TEST_REST_CAP", "0.01"))


def is_test_mode() -> bool:
    """Read env each call so consumer subprocess always sees PIXIL_TEST_MODE."""
    val = os.environ.get(_ENV_FLAG, "").strip().lower()
    return val in ("1", "true", "yes", "on")


def effective_rest_duration(requested: float) -> float:
    """Return sleep duration for rest(); capped in test mode."""
    if not is_test_mode():
        return requested
    if requested <= 0:
        return requested
    return min(requested, REST_CAP_SECONDS)


@dataclass
class TestRunMetrics:
    script: str = ""
    commands_dispatched: int = 0
    rest_calls: int = 0
    fail_lines: int = 0
    buffer_hash: str = ""

    def format_summary_line(self, exit_code: int = 0) -> str:
        return (
            f"PIXIL_TEST_SUMMARY "
            f"script={self.script} "
            f"commands={self.commands_dispatched} "
            f"rest={self.rest_calls} "
            f"failures={self.fail_lines} "
            f"buffer={self.buffer_hash or 'none'} "
            f"exit={exit_code}"
        )


_metrics = TestRunMetrics()


def reset_metrics(script: str = "") -> None:
    global _metrics
    _metrics = TestRunMetrics(script=script)


def get_metrics() -> TestRunMetrics:
    return _metrics


def set_script_name(script: str) -> None:
    if is_test_mode():
        _metrics.script = script


def record_command_dispatched() -> None:
    if is_test_mode():
        _metrics.commands_dispatched += 1


def record_rest() -> None:
    if is_test_mode():
        _metrics.rest_calls += 1


def record_fail_line() -> None:
    if is_test_mode():
        _metrics.fail_lines += 1


def set_buffer_hash(value: str) -> None:
    if is_test_mode():
        _metrics.buffer_hash = value


def print_summary(exit_code: int = 0) -> None:
    if is_test_mode():
        print(_metrics.format_summary_line(exit_code), flush=True)


def note_fail_in_line(text: str) -> None:
    """Call from print paths when output may contain self-check failures."""
    if is_test_mode() and "FAIL" in text.upper():
        record_fail_line()
