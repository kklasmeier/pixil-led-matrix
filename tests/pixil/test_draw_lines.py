"""Tests for draw_lines array packing into draw_batch records."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.draw_batch_dispatch import append_draw_lines
from pixil_utils.parameter_types import validate_command_params
from shared.draw_batch_protocol import unpack_draw_batch


def _arr(values):
    a = PixilArray(len(values))
    for i, val in enumerate(values):
        a[i] = val
    return a


def test_validate_draw_lines_requires_endpoints_and_color():
    with pytest.raises(ValueError, match="at least 5"):
        validate_command_params("draw_lines", "v_x0, v_y0, v_x1, v_y1")


def test_append_draw_lines_packs_segments_with_scalar_intensity():
    buf = bytearray()
    n = append_draw_lines(
        buf,
        _arr([0.0, 10.0]),
        _arr([0.0, 10.0]),
        _arr([5.0, 20.0]),
        _arr([5.0, 20.0]),
        "cyan",
        80,
    )
    assert n == 2
    ops = list(unpack_draw_batch(bytes(buf)))
    assert ops[0][0] == "draw_line"
    assert ops[0][1][:4] == (0, 0, 5, 5)
    assert ops[0][1][5] == 80
    assert ops[1][1][:4] == (10, 10, 20, 20)


def test_append_draw_lines_intensity_array_and_count():
    buf = bytearray()
    n = append_draw_lines(
        buf,
        _arr([1.0, 2.0, 3.0]),
        _arr([1.0, 2.0, 3.0]),
        _arr([4.0, 5.0, 6.0]),
        _arr([4.0, 5.0, 6.0]),
        "azure",
        _arr([10.0, 20.0, 30.0]),
        count=2,
    )
    assert n == 2
    ops = list(unpack_draw_batch(bytes(buf)))
    assert len(ops) == 2
    assert ops[0][1][5] == 10
    assert ops[1][1][5] == 20


def test_append_draw_lines_skips_fully_offscreen():
    buf = bytearray()
    n = append_draw_lines(
        buf,
        _arr([-100.0, 10.0]),
        _arr([-100.0, 10.0]),
        _arr([-90.0, 20.0]),
        _arr([-90.0, 20.0]),
        "white",
        100,
    )
    assert n == 1
    ops = list(unpack_draw_batch(bytes(buf)))
    assert len(ops) == 1
    assert ops[0][1][:4] == (10, 10, 20, 20)
