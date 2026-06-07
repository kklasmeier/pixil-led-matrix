"""
Regression tests for draw_batch off-screen coordinate handling.

Bug: pack_draw_op used _coord_uint16() on shape coordinates. Negative values
were silently clamped to 0, so circles/polygons/ellipses drawn off the left
(or top) appeared pinned on the panel edge instead of disappearing. Rectangles
with negative x kept their full width but shifted origin to 0, widening the
visible strip. Arc endpoints were clamped independently, distorting the curve.

Fix: skip or clip shapes before packing (see shared/draw_batch_protocol.py).
These tests fail if that guard is removed and naive uint16 packing returns.
"""

from __future__ import annotations

import struct
import sys
from unittest.mock import MagicMock

import pytest

from pixil_utils.draw_batch_dispatch import append_parsed_draw
from shared.draw_batch_protocol import (
    OP_CIRCLE,
    _CIRCLE_FMT,
    _burnout_uint,
    _color_id_from_arg,
    _coord_uint16,
    _fill_byte,
    _intensity_byte,
    center_radius_visible_on_panel,
    clip_rectangle,
    encode_buffer,
    ellipse_visible_on_panel,
    pack_draw_op,
    unpack_draw_batch,
)
from shared.mplot_protocol import get_burnout_mode_int

if "rgbmatrix" not in sys.modules:
    _rgb_stub = MagicMock()
    _rgb_stub.RGBMatrix = MagicMock
    _rgb_stub.RGBMatrixOptions = MagicMock
    sys.modules["rgbmatrix"] = _rgb_stub


# ---------------------------------------------------------------------------
# Root cause documentation
# ---------------------------------------------------------------------------


def test_uint16_coord_clamp_is_the_underlying_encoding_bug():
    """Negative coords cannot be represented; naive pack maps them to 0."""
    assert _coord_uint16(-5) == 0
    assert _coord_uint16(-1) == 0


def test_naive_uint16_circle_pack_would_pin_at_left_edge():
    """
    Symptom of the original bug: unpacking a circle packed with clamped x=0.

    This documents failure mode; the guard tests below ensure we never emit this.
    """
    payload = struct.pack(
        _CIRCLE_FMT,
        _coord_uint16(-5),
        _coord_uint16(32),
        _coord_uint16(4),
        _color_id_from_arg("gold"),
        _intensity_byte(90),
        _burnout_uint(None),
        get_burnout_mode_int("instant"),
        _fill_byte(True),
    )
    rec = bytes([OP_CIRCLE]) + payload
    cmd_name, args = next(iter(unpack_draw_batch(rec)))
    assert cmd_name == "draw_circle"
    assert args[0] == 0, "bug symptom: off-screen circle center became x=0"
    assert args[1] == 32
    assert args[2] == 4


# ---------------------------------------------------------------------------
# pack_draw_op must omit or clip — parametrized per shape
# ---------------------------------------------------------------------------

OFFSCREEN_OMIT_CASES = [
    (
        "draw_circle",
        [-5, 32, 4, "gold", 90, True, None, "instant"],
    ),
    (
        "draw_polygon",
        [-5, 32, 6, 5, "green", 80, 0.0, False, None, "instant"],
    ),
    (
        "draw_ellipse",
        [-5, 32, 8, 4, "purple", 80, False, 0.0, None, "instant"],
    ),
    (
        "draw_arc",
        [-200, -200, -150, -150, 5.0, "orange", 80, False, None, "instant"],
    ),
]


@pytest.mark.parametrize("cmd_name,args", OFFSCREEN_OMIT_CASES)
def test_offscreen_shape_omitted_from_batch(cmd_name, args):
    """Regression: off-screen shapes must not be packed (no left-edge pin)."""
    assert pack_draw_op(cmd_name, args) == b""


CLIP_CASES = [
    (
        "draw_rectangle",
        [-5, 10, 20, 10, "blue", 80, True, None, "instant"],
        (0, 10, 15, 10),
    ),
    (
        "draw_rectangle",
        [50, 10, 20, 10, "blue", 80, True, None, "instant"],
        (50, 10, 14, 10),
    ),
    (
        "draw_rectangle",
        [10, -3, 10, 20, "blue", 80, True, None, "instant"],
        (10, 0, 10, 17),
    ),
    (
        "draw_line",
        [32, 32, -10, 70, "cyan", 90, None, "instant"],
        (32, 32, 0, 61),
    ),
    (
        "draw_arc",
        [32, 32, -10, 70, 5.0, "orange", 80, False, None, "instant"],
        (32, 32, 0, 61),
    ),
]


@pytest.mark.parametrize("cmd_name,args,expected_coords", CLIP_CASES)
def test_offscreen_shape_clipped_not_clamped(cmd_name, args, expected_coords):
    """Regression: partial off-screen shapes clip geometry, not pin origin."""
    rec = pack_draw_op(cmd_name, args)
    assert rec, f"{cmd_name} should produce a clipped record"
    _cmd, packed_args = next(iter(unpack_draw_batch(rec)))
    assert packed_args[: len(expected_coords)] == expected_coords


def test_rectangle_regression_must_not_keep_full_width_after_left_clip():
    """
    Old bug: x=-5 clamped to 0 but width stayed 20 → 20px strip on left edge.

    Correct clip: width 15 (visible portion only).
    """
    naive_x = _coord_uint16(-5)
    assert naive_x == 0
    rec = pack_draw_op(
        "draw_rectangle",
        [-5, 10, 20, 10, "blue", 80, True, None, "instant"],
    )
    _cmd, (x, y, w, h, *_rest) = next(iter(unpack_draw_batch(rec)))
    assert (x, y, w, h) == (0, 10, 15, 10)
    assert w != 20, "must not preserve full width after left-edge clip"


# ---------------------------------------------------------------------------
# Helper boundary values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "xc,yc,r,visible",
    [
        (-1, 32, 4, False),
        (0, 32, 4, True),
        (2, 32, 4, True),
        (68, 32, 4, False),
        (32, -1, 4, False),
        (32, 32, 0, False),
    ],
)
def test_center_radius_visible_on_panel_boundaries(xc, yc, r, visible):
    assert center_radius_visible_on_panel(xc, yc, r) is visible


@pytest.mark.parametrize(
    "xc,yc,xr,yr,visible",
    [
        (-1, 32, 8, 4, False),
        (4, 32, 8, 4, True),
        (72, 32, 8, 4, False),
    ],
)
def test_ellipse_visible_on_panel_boundaries(xc, yc, xr, yr, visible):
    assert ellipse_visible_on_panel(xc, yc, xr, yr) is visible


@pytest.mark.parametrize(
    "x,y,w,h,expected",
    [
        (-5, 10, 20, 10, (0, 10, 15, 10)),
        (50, 10, 20, 10, (50, 10, 14, 10)),
        (10, -3, 10, 20, (10, 0, 10, 17)),
        (-20, 10, 10, 10, None),
        (70, 10, 10, 10, None),
    ],
)
def test_clip_rectangle_boundaries(x, y, w, h, expected):
    assert clip_rectangle(x, y, w, h) == expected


# ---------------------------------------------------------------------------
# Dispatch and execution integration
# ---------------------------------------------------------------------------


def test_append_parsed_draw_skips_offscreen_circle():
    buf = bytearray()
    append_parsed_draw(buf, "draw_circle", [-5, 32, 4, "gold", 90, True, None, "instant"])
    assert len(buf) == 0

    append_parsed_draw(buf, "draw_circle", [32, 32, 4, "gold", 90, True, None, "instant"])
    assert len(buf) > 0
    _cmd, args = next(iter(unpack_draw_batch(bytes(buf))))
    assert args[0] == 32


def test_draw_batch_handler_skips_offscreen_circle():
    from rgb_matrix_lib.commands import CommandExecutor

    api = MagicMock()
    api.drain_abort_requested.return_value = False
    api.draw_circle = MagicMock()
    executor = CommandExecutor(api)

    batch = bytearray()
    batch.extend(pack_draw_op("draw_circle", [32, 32, 4, "gold", 90, True, None, "instant"]))
    batch.extend(pack_draw_op("draw_circle", [-5, 32, 4, "gold", 90, True, None, "instant"]))
    encoded = encode_buffer(bytes(batch))

    executor._handle_draw_batch(encoded)

    api.draw_circle.assert_called_once()
    assert api.draw_circle.call_args[0][0] == 32


def test_draw_batch_handler_never_invokes_draw_with_zero_from_negative_input():
    """End-to-end: negative circle input must not reach draw_circle(x=0, ...)."""
    from rgb_matrix_lib.commands import CommandExecutor

    api = MagicMock()
    api.drain_abort_requested.return_value = False
    api.draw_circle = MagicMock()
    executor = CommandExecutor(api)

    batch = bytearray()
    batch.extend(pack_draw_op("draw_circle", [-5, 32, 4, "gold", 90, True, None, "instant"]))
    if batch:
        encoded = encode_buffer(bytes(batch))
        executor._handle_draw_batch(encoded)

    api.draw_circle.assert_not_called()
