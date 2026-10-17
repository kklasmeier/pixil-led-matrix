"""z_index must control sprite compositing order (not just creation order)."""

import sys
from unittest.mock import MagicMock

import pytest

if "rgbmatrix" not in sys.modules:
    _rgb_stub = MagicMock()
    _rgb_stub.RGBMatrix = MagicMock
    _rgb_stub.RGBMatrixOptions = MagicMock
    sys.modules["rgbmatrix"] = _rgb_stub

from rgb_matrix_lib.sprite import SpriteManager


@pytest.fixture
def manager_with_three_sprites():
    mgr = SpriteManager()
    for name, z in (("back", 0), ("mid", 5), ("front", 10)):
        mgr.begin_sprite_definition(name, 2, 2)
        mgr.end_sprite_definition()
        # Create in reverse z order so creation order != draw order
    mgr.create_instance("front", 0, 0, 0, z_index=10)
    mgr.create_instance("back", 0, 0, 0, z_index=0)
    mgr.create_instance("mid", 0, 0, 0, z_index=5)
    return mgr


def test_iter_draw_order_sorts_by_z_index(manager_with_three_sprites):
    mgr = manager_with_three_sprites
    assert mgr.z_order == [("front", 0), ("back", 0), ("mid", 0)]
    assert mgr.iter_draw_order() == [("back", 0), ("mid", 0), ("front", 0)]


def test_iter_draw_order_stable_for_equal_z():
    mgr = SpriteManager()
    for name in ("a", "b", "c"):
        mgr.begin_sprite_definition(name, 1, 1)
        mgr.end_sprite_definition()
        mgr.create_instance(name, 0, 0, 0, z_index=3)
    assert mgr.iter_draw_order() == [("a", 0), ("b", 0), ("c", 0)]


def test_z_index_change_updates_draw_order(manager_with_three_sprites):
    mgr = manager_with_three_sprites
    mgr.get_instance("back", 0).z_index = 20
    assert mgr.iter_draw_order() == [("mid", 0), ("front", 0), ("back", 0)]
