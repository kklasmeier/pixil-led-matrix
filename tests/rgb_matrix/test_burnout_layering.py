import sys
from unittest.mock import MagicMock

import numpy as np

if "rgbmatrix" not in sys.modules:
    rgb_stub = MagicMock()
    rgb_stub.RGBMatrix = MagicMock
    rgb_stub.RGBMatrixOptions = MagicMock
    sys.modules["rgbmatrix"] = rgb_stub

from rgb_matrix_lib import drawing_objects
from rgb_matrix_lib.drawing_objects import BurnoutMode, ShapeType, ThreadedBurnoutManager


class FakeApi:
    def __init__(self):
        self.drawing_buffer = np.zeros((2, 2, 3), dtype=np.uint8)

    def _draw_to_buffers(self, x, y, r, g, b):
        self.drawing_buffer[y, x] = (r, g, b)


def add_point(manager, api, color, duration_ms, mode):
    api._draw_to_buffers(0, 0, *color)
    manager.add_object(ShapeType.POINT, (0, 0), [(0, 0)], duration_ms, mode, [color])


def test_last_drawn_burnout_owns_pixel_not_longest_duration(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(drawing_objects.time, "time", lambda: now[0])
    api = FakeApi()
    manager = ThreadedBurnoutManager(api)

    add_point(manager, api, (255, 0, 0), 2000, BurnoutMode.FADE)
    trail = manager.pixel_index[(0, 0)][0][0]
    add_point(manager, api, (0, 0, 255), 100, BurnoutMode.INSTANT)
    cover = manager.pixel_index[(0, 0)][-1][0]

    assert manager._is_pixel_owner(0, 0, cover, now[0])
    assert not manager._is_pixel_owner(0, 0, trail, now[0])


def test_expiring_cover_reveals_current_underlying_fade(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(drawing_objects.time, "time", lambda: now[0])
    api = FakeApi()
    manager = ThreadedBurnoutManager(api)

    add_point(manager, api, (255, 0, 0), 2000, BurnoutMode.FADE)
    trail = manager.pixel_index[(0, 0)][0][0]
    add_point(manager, api, (0, 0, 255), 100, BurnoutMode.INSTANT)
    cover = manager.pixel_index[(0, 0)][-1][0]

    now[0] = 100.15
    manager._update_active_fades(now[0])
    assert tuple(api.drawing_buffer[0, 0]) == (0, 0, 255)

    manager._clear_object(cover)

    expected = manager._color_at(trail, 0, now[0])
    assert tuple(api.drawing_buffer[0, 0]) == expected
    assert manager._is_pixel_owner(0, 0, trail, now[0])


def test_expiring_burnout_does_not_clear_permanent_overlay(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(drawing_objects.time, "time", lambda: now[0])
    api = FakeApi()
    manager = ThreadedBurnoutManager(api)

    add_point(manager, api, (255, 0, 0), 100, BurnoutMode.FADE)
    trail = manager.pixel_index[(0, 0)][0][0]
    api._draw_to_buffers(0, 0, 255, 0, 255)

    now[0] = 100.15
    manager._clear_object(trail)

    assert tuple(api.drawing_buffer[0, 0]) == (255, 0, 255)
    assert (0, 0) not in manager.pixel_index


def test_registration_reasserts_draw_if_fade_thread_won_race(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(drawing_objects.time, "time", lambda: now[0])
    api = FakeApi()
    manager = ThreadedBurnoutManager(api)

    add_point(manager, api, (255, 0, 0), 2000, BurnoutMode.FADE)

    # Simulate: producer drew blue, then the fade thread repainted red before
    # the producer registered blue's burnout.
    api._draw_to_buffers(0, 0, 0, 0, 255)
    api._draw_to_buffers(0, 0, 200, 0, 0)
    manager.add_object(
        ShapeType.POINT,
        (0, 0),
        [(0, 0)],
        100,
        BurnoutMode.INSTANT,
        [(0, 0, 255)],
    )

    assert tuple(api.drawing_buffer[0, 0]) == (0, 0, 255)


def test_expiration_tolerates_duplicate_rasterized_points(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(drawing_objects.time, "time", lambda: now[0])
    api = FakeApi()
    manager = ThreadedBurnoutManager(api)

    points = [(0, 0), (0, 0)]
    colors = [(255, 0, 0), (255, 0, 0)]
    api._draw_to_buffers(0, 0, 255, 0, 0)
    manager.add_object(
        ShapeType.POLYGON,
        (0, 0),
        points,
        100,
        BurnoutMode.INSTANT,
        colors,
    )
    obj = manager.pixel_index[(0, 0)][0][0]

    now[0] = 100.15
    manager._clear_object(obj)

    assert tuple(api.drawing_buffer[0, 0]) == (0, 0, 1)
    assert (0, 0) not in manager.pixel_index
