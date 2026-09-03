"""Regression tests for RGB_Api.rest timing boundaries."""

import sys
from unittest.mock import MagicMock


def _api_module():
    if "rgbmatrix" not in sys.modules:
        sys.modules["rgbmatrix"] = MagicMock()
    from rgb_matrix_lib import api

    return api


def test_rest_does_not_sleep_after_deadline_passes(monkeypatch):
    api_module = _api_module()
    api = api_module.RGB_Api.__new__(api_module.RGB_Api)
    api._drain_checker = None
    api._shutdown_checker = None
    api.pump_fade_display = MagicMock()

    # The deadline passes between checking the current time and sleeping,
    # which previously caused time.sleep() to receive a negative duration.
    timestamps = iter((100.0, 100.0, 100.9, 101.1))
    sleep = MagicMock()
    monkeypatch.setattr(api_module.time, "monotonic", lambda: next(timestamps))
    monkeypatch.setattr(api_module.time, "sleep", sleep)

    api.rest(1.0)

    sleep.assert_not_called()
