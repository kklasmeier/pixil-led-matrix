"""Immediate-mode sprite ops: one refresh_display present (no broken incremental path)."""

import sys
from unittest.mock import MagicMock

import pytest

# rgbmatrix is only installed on the Pi; stub so unit tests can import RGB_Api elsewhere.
if "rgbmatrix" not in sys.modules:
    _rgb_stub = MagicMock()
    _rgb_stub.RGBMatrix = MagicMock
    _rgb_stub.RGBMatrixOptions = MagicMock
    sys.modules["rgbmatrix"] = _rgb_stub

from rgb_matrix_lib.api import RGB_Api
from rgb_matrix_lib.sprite import SpriteInstance, SpriteManager


@pytest.fixture
def api_with_visible_ball():
    api = RGB_Api.__new__(RGB_Api)
    api.frame_mode = False
    api.canvas = MagicMock()
    api.matrix = MagicMock()
    api.matrix.width = 64
    api.matrix.height = 64
    api.drawing_buffer = MagicMock()
    api.grid_dirty = MagicMock()
    api.background_manager = MagicMock()
    api.background_manager.has_background.return_value = False
    api.current_command_pixels = []
    api.sprite_manager = MagicMock(spec=SpriteManager)
    api.sprite_manager.z_order = []

    instance = MagicMock(spec=SpriteInstance)
    instance.visible = True
    instance.x = 10
    instance.y = 20
    instance.width = 1
    instance.height = 1
    instance.occupied_cells = set()
    api.sprite_manager.get_instance.return_value = instance

    api._mark_cells_dirty = MagicMock()
    api._restore_dirty_cells = MagicMock()
    api.copy_sprite_to_buffer = MagicMock()
    api._maybe_swap_buffer = MagicMock()
    api.refresh_display = MagicMock()

    return api, instance


def test_move_sprite_uses_full_refresh_once(api_with_visible_ball):
    api, _instance = api_with_visible_ball
    api.move_sprite("ball_sprite", 12, 22)
    api.refresh_display.assert_called_once()
    api._restore_dirty_cells.assert_not_called()
    api.copy_sprite_to_buffer.assert_not_called()
    api._maybe_swap_buffer.assert_not_called()


def test_hide_sprite_uses_full_refresh_once(api_with_visible_ball):
    api, instance = api_with_visible_ball
    instance.visible = True
    api.hide_sprite("ball_sprite")
    api.refresh_display.assert_called_once()
    api._restore_dirty_cells.assert_not_called()
    api._maybe_swap_buffer.assert_not_called()


def test_move_sprite_skips_present_in_frame_mode(api_with_visible_ball):
    api, _instance = api_with_visible_ball
    api.frame_mode = True
    api.move_sprite("ball_sprite", 12, 22)
    api.refresh_display.assert_not_called()
