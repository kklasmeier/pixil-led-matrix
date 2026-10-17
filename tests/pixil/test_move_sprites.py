"""Tests for move_sprites array packing into sprite_batch records."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.parameter_types import validate_command_params
from pixil_utils.sprite_batch_dispatch import append_move_sprites
from shared.sprite_batch_protocol import unpack_sprite_batch


def _arr(values):
    a = PixilArray(len(values))
    for i, val in enumerate(values):
        a[i] = val
    return a


def test_validate_move_sprites_requires_name_and_xy():
    with pytest.raises(ValueError, match="at least 3"):
        validate_command_params("move_sprites", "bob, v_x")


def test_append_move_sprites_packs_instances_and_cels():
    buf = bytearray()
    n = append_move_sprites(
        buf,
        "bob",
        _arr([10.4, 20.6]),
        _arr([11.0, 21.0]),
        _arr([2.0, 5.0]),
    )
    assert n == 2
    ops = list(unpack_sprite_batch(bytes(buf)))
    assert ops[0] == ("move_sprite", ("bob", 10, 11, 0, 2))
    assert ops[1] == ("move_sprite", ("bob", 21, 21, 1, 5))  # 20.6 rounds to 21


def test_append_move_sprites_respects_count_and_optional_cel():
    buf = bytearray()
    n = append_move_sprites(
        buf,
        "bob",
        _arr([1.0, 2.0, 3.0]),
        _arr([4.0, 5.0, 6.0]),
        cel=None,
        count=2,
    )
    assert n == 2
    ops = list(unpack_sprite_batch(bytes(buf)))
    assert len(ops) == 2
    assert ops[0][0] == "move_sprite"
    assert ops[0][1][:4] == ("bob", 1, 4, 0)
    assert ops[1][1][:4] == ("bob", 2, 5, 1)


def test_append_move_sprites_packs_z_index():
    buf = bytearray()
    n = append_move_sprites(
        buf,
        "bob",
        _arr([10.0, 20.0]),
        _arr([11.0, 21.0]),
        _arr([2.0, 5.0]),
        z=_arr([3.0, 40.0]),
    )
    assert n == 2
    ops = list(unpack_sprite_batch(bytes(buf)))
    assert ops[0] == ("move_sprite", ("bob", 10, 11, 0, 2, 3))
    assert ops[1] == ("move_sprite", ("bob", 20, 21, 1, 5, 40))
