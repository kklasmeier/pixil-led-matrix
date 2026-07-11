"""Preserve-mode end_frame: swap incremental canvas, seed back buffer from accumulation."""

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

if "rgbmatrix" not in sys.modules:
    _rgb_stub = MagicMock()
    _rgb_stub.RGBMatrix = MagicMock
    _rgb_stub.RGBMatrixOptions = MagicMock
    sys.modules["rgbmatrix"] = _rgb_stub

from rgb_matrix_lib.api import RGB_Api


@pytest.fixture
def api_no_background():
    api = RGB_Api.__new__(RGB_Api)
    api.frame_mode = True
    api.preserve_frame_changes = True
    api.canvas = MagicMock()
    api.matrix = MagicMock()
    api.matrix.width = 64
    api.matrix.height = 64
    api.matrix.SwapOnVSync.side_effect = lambda canvas: canvas
    api.drawing_buffer = MagicMock()
    api.drawing_buffer.copy.return_value = MagicMock()
    api.current_command_pixels = [(1, 2, 10, 20, 30)]
    api.sprite_manager = MagicMock()
    api.sprite_manager.z_order = []
    api.background_manager = MagicMock()
    api.background_manager.has_background.return_value = False
    api._pace_after_present = MagicMock()
    return api


def test_preserve_end_frame_blits_after_swap_not_before(api_no_background):
    api = api_no_background
    call_order = []

    def record_blit(_buf):
        call_order.append("blit")

    def record_swap(canvas):
        call_order.append("swap")
        return canvas

    api.matrix.SwapOnVSync.side_effect = record_swap
    with patch.object(api, "_blit_array_to_canvas", side_effect=record_blit), patch.object(
        api, "_drawing_buffer_for_display", return_value=MagicMock()
    ):
        api.end_frame()
    assert call_order == ["swap", "blit"]
    api.canvas.Fill.assert_not_called()


def test_standard_end_frame_blits_before_swap(api_no_background):
    api = api_no_background
    api.preserve_frame_changes = False
    call_order = []

    def record_blit(_buf):
        call_order.append("blit")

    def record_swap(canvas):
        call_order.append("swap")
        return canvas

    api.matrix.SwapOnVSync.side_effect = record_swap
    with patch.object(api, "_blit_array_to_canvas", side_effect=record_blit), patch.object(
        api, "_drawing_buffer_for_display", return_value=MagicMock()
    ):
        api.end_frame()
    assert call_order == ["blit", "swap"]
    api.canvas.Fill.assert_called_once_with(0, 0, 0)


def test_standard_begin_frame_does_not_clear_visible_canvas(api_no_background):
    """Avoid black flash while draw_batch is still building the next frame."""
    from rgb_matrix_lib.utils import TRANSPARENT_COLOR

    api = api_no_background
    api.frame_mode = False
    api.preserve_frame_changes = False
    api.drawing_buffer = np.full((64, 64, 3), (1, 2, 3), dtype=np.uint8)
    api.begin_frame(False)
    api.canvas.Fill.assert_not_called()
    assert np.all(api.drawing_buffer == TRANSPARENT_COLOR)
