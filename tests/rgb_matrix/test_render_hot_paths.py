"""Pixel-equivalence checks for optimized rectangle and sprite hot paths."""

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
from rgb_matrix_lib.background import BackgroundManager
from rgb_matrix_lib.sprite import MatrixSprite, SpriteInstance, SpriteManager
from rgb_matrix_lib.utils import TRANSPARENT_COLOR


def make_api(frame_mode=True):
    api = RGB_Api.__new__(RGB_Api)
    api.matrix = MagicMock()
    api.matrix.width = 8
    api.matrix.height = 8
    api.canvas = MagicMock()
    api.drawing_buffer = np.full((8, 8, 3), TRANSPARENT_COLOR, dtype=np.uint8)
    api.current_command_pixels = []
    api.frame_mode = frame_mode
    api.preserve_frame_changes = False
    api._maybe_swap_buffer = MagicMock()
    api.burnout_manager = MagicMock()
    return api


def test_filled_rectangle_clips_and_draws_exact_pixels_in_standard_frame():
    api = make_api()

    api.draw_rectangle(-2, 1, 5, 3, (10, 20, 30), fill=True)

    expected = np.full((8, 8, 3), TRANSPARENT_COLOR, dtype=np.uint8)
    expected[1:4, 0:3] = (10, 20, 30)
    np.testing.assert_array_equal(api.drawing_buffer, expected)
    api.canvas.SetPixel.assert_not_called()
    api.burnout_manager.add_object.assert_not_called()


def test_filled_rectangle_keeps_per_pixel_immediate_mode_behavior():
    api = make_api(frame_mode=False)

    api.draw_rectangle(1, 2, 2, 2, (10, 20, 30), fill=True)

    assert api.canvas.SetPixel.call_count == 4
    assert api.current_command_pixels == [
        (1, 2, 10, 20, 30),
        (1, 3, 10, 20, 30),
        (2, 2, 10, 20, 30),
        (2, 3, 10, 20, 30),
    ]


def test_filled_rectangle_preserves_burnout_point_order():
    api = make_api()

    api.draw_rectangle(1, 2, 2, 2, (10, 20, 30), fill=True, burnout=100)

    points = api.burnout_manager.add_object.call_args.args[2]
    assert points == [(1, 2), (1, 3), (2, 2), (2, 3)]


def test_sprite_blit_preserves_clipping_transparency_and_intensity_rounding():
    api = make_api()
    template = MatrixSprite(3, 2, "test")
    template.buffer[:, :] = [
        [(100, 50, 25), TRANSPARENT_COLOR, (255, 1, 2)],
        [(10, 20, 30), (9, 9, 9), (200, 100, 50)],
    ]
    template.intensity_buffer[:, :] = [
        [50, 100, 33],
        [100, 0, 75],
    ]
    sprite = SpriteInstance(template, -1, 2)

    api.copy_sprite_to_buffer(sprite, api.canvas)

    assert api.canvas.SetPixel.call_args_list == [
        ((1, 2, 84, 0, 0),),
        ((0, 3, 0, 0, 0),),
        ((1, 3, 150, 75, 37),),
    ]


@pytest.mark.parametrize(
    ("method", "args", "kwargs"),
    [
        ("draw_circle", (4, 4, 4, (11, 22, 33)), {"fill": True}),
        (
            "draw_polygon",
            (4, 4, 4, 7, (11, 22, 33)),
            {"rotation": 13, "fill": True},
        ),
        (
            "draw_ellipse",
            (4, 4, 4, 2, (11, 22, 33)),
            {"rotation": 27, "fill": True},
        ),
    ],
)
def test_standard_frame_filled_shapes_match_preserve_pixel_path(method, args, kwargs):
    optimized = make_api()
    reference = make_api()
    reference.preserve_frame_changes = True

    getattr(optimized, method)(*args, **kwargs)
    getattr(reference, method)(*args, **kwargs)

    np.testing.assert_array_equal(optimized.drawing_buffer, reference.drawing_buffer)


def test_background_viewport_cache_is_isolated_and_invalidated_by_nudge():
    sprites = SpriteManager()
    template = MatrixSprite(2, 2, "background")
    template.buffer[:, :] = [
        [(10, 20, 30), (40, 50, 60)],
        [(70, 80, 90), TRANSPARENT_COLOR],
    ]
    sprites.templates["background"] = template
    manager = BackgroundManager(sprites)
    manager.set_background("background")

    with patch.object(manager, "_render_layer", wraps=manager._render_layer) as render:
        first = manager.get_viewport(8, 8)
        first[0, 0] = (255, 255, 255)
        second = manager.get_viewport(8, 8)
        assert render.call_count == 1
        assert tuple(second[0, 0]) == (10, 20, 30)

        manager.nudge(1, 0, cel_index=0)
        shifted = manager.get_viewport(8, 8)
        assert render.call_count == 2
        assert tuple(shifted[0, 0]) == (40, 50, 60)
