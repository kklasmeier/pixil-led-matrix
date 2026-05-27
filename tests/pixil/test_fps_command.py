"""fps() display pacing helpers."""

import sys
import time
from unittest.mock import MagicMock

from pixil_utils.param_bounds import clamp_fps


def _rgb_api_class():
    if "rgbmatrix" not in sys.modules:
        mock = MagicMock()
        sys.modules["rgbmatrix"] = mock
        sys.modules["rgbmatrix"].RGBMatrix = MagicMock
        sys.modules["rgbmatrix"].RGBMatrixOptions = MagicMock
    from rgb_matrix_lib.api import RGB_Api

    return RGB_Api


def test_clamp_fps_zero_disables():
    assert clamp_fps(0) == 0.0
    assert clamp_fps(-5) == 0.0


def test_clamp_fps_positive():
    assert clamp_fps(60) == 60.0


def test_pace_after_present_sleeps_when_too_fast():
    RGB_Api = _rgb_api_class()
    api = RGB_Api.__new__(RGB_Api)
    api._target_fps = 60.0
    api._frame_interval = 1.0 / 60.0
    api._last_present_time = time.perf_counter()
    slept = []

    def _fake_sleep(seconds):
        slept.append(seconds)

    original_sleep = time.sleep
    time.sleep = _fake_sleep
    try:
        api._pace_after_present()
    finally:
        time.sleep = original_sleep

    assert len(slept) == 1
    assert slept[0] > 0


def test_pace_after_present_no_sleep_when_disabled():
    RGB_Api = _rgb_api_class()
    api = RGB_Api.__new__(RGB_Api)
    api._frame_interval = 0.0
    api._last_present_time = time.perf_counter()
    slept = []

    def _fake_sleep(seconds):
        slept.append(seconds)

    original_sleep = time.sleep
    time.sleep = _fake_sleep
    try:
        api._pace_after_present()
    finally:
        time.sleep = original_sleep

    assert slept == []


def test_set_fps_updates_interval():
    RGB_Api = _rgb_api_class()
    api = RGB_Api.__new__(RGB_Api)
    api._target_fps = 0.0
    api._frame_interval = 0.0
    api._last_present_time = 0.0

    api.set_fps(30)
    assert api._target_fps == 30.0
    assert abs(api._frame_interval - (1.0 / 30.0)) < 1e-9

    api.set_fps(0)
    assert api._target_fps == 0.0
    assert api._frame_interval == 0.0
