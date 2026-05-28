"""Unified draw_batch protocol pack/unpack and ordering."""

import pixil_utils.optimization_flags as flags
from shared.draw_batch_protocol import (
    OP_CIRCLE,
    OP_LINE,
    OP_PLOT,
    OP_RECT,
    clip_line_segment,
    encode_buffer,
    decode_buffer,
    pack_draw_op,
    unpack_draw_batch,
)


def test_plot_string_coords_from_ultra_fast_parse():
    """parse_value ultra-fast path returns digit strings; pack must coerce."""
    rec = pack_draw_op("plot", ["32", "32", "white", "100"])
    cmds = list(unpack_draw_batch(rec))
    assert cmds[0][0] == "plot"
    assert cmds[0][1][:2] == (32, 32)


def test_mplot_string_coords_from_ultra_fast_parse():
    rec = pack_draw_op("mplot", ["5", "10", "cyan", "80"])
    cmds = list(unpack_draw_batch(rec))
    assert cmds[0][1][:2] == (5, 10)


def test_plot_transparent_roundtrip():
    """Langton's Ant and erasing use plot(..., transparent) inside begin_frame."""
    rec = pack_draw_op("plot", [5, 5, "transparent"])
    cmds = list(unpack_draw_batch(rec))
    assert cmds[0][0] == "plot"
    x, y, color, intensity, burnout, mode = cmds[0][1]
    assert (x, y) == (5, 5)
    assert color == "transparent"
    assert intensity is None
    assert burnout is None
    assert mode == "instant"


def test_plot_roundtrip():
    rec = pack_draw_op("plot", [10, 20, "red", 80, 100, "instant"])
    data = encode_buffer(rec)
    cmds = list(unpack_draw_batch(decode_buffer(data)))
    assert len(cmds) == 1
    assert cmds[0][0] == "plot"
    x, y, color, intensity, burnout, mode = cmds[0][1]
    assert (x, y) == (10, 20)
    assert color == "red"
    assert intensity == 80
    assert burnout == 100
    assert mode == "instant"


def test_plot_fade_mode_roundtrip():
  rec = pack_draw_op("plot", [5, 10, 42, 70, 750, "fade"])
  cmds = list(unpack_draw_batch(rec))
  assert cmds[0][0] == "plot"
  x, y, color, intensity, burnout, mode = cmds[0][1]
  assert burnout == 750
  assert mode == "fade"


def test_draw_order_preserved_circle_rect_polygon():
    buf = bytearray()
    buf.extend(pack_draw_op("draw_circle", [32, 32, 5, 50, 80, False, None, "instant"]))
    buf.extend(pack_draw_op("draw_rectangle", [0, 0, 10, 10, 60, 70, False, None, "instant"]))
    buf.extend(
        pack_draw_op(
            "draw_polygon",
            [32, 32, 6, 5, 70, 80, 0.0, False, None, "instant"],
        )
    )
    names = [c[0] for c in unpack_draw_batch(bytes(buf))]
    assert names == ["draw_circle", "draw_rectangle", "draw_polygon"]


def test_line_and_circle_roundtrip():
    rec = pack_draw_op("draw_line", [0, 0, 10, 10, "cyan", 90, None, "instant"])
    cmds = list(unpack_draw_batch(rec))
    assert cmds[0][0] == "draw_line"
    assert cmds[0][1][:4] == (0, 0, 10, 10)


def test_clip_line_segment_partially_off_screen():
    """Clip to viewport instead of pinning each endpoint to 0."""
    assert clip_line_segment(32, 32, -10, 70) == (32, 32, 0, 61)


def test_clip_line_segment_fully_outside_returns_none():
    assert clip_line_segment(-200, -200, -150, -150) is None


def test_draw_line_negative_coords_clipped_to_viewport():
    """3D projection can yield negative endpoints; pack must not raise on struct H."""
    rec = pack_draw_op(
        "draw_line",
        [32, 32, -10, 70, 50, 80, None, "instant"],
    )
    assert rec
    cmds = list(unpack_draw_batch(rec))
    assert cmds[0][1][:4] == (32, 32, 0, 61)


def test_draw_line_fully_outside_skipped():
    rec = pack_draw_op(
        "draw_line",
        [-200, -200, -150, -150, "green", 100, None, "instant"],
    )
    assert rec == b""


def test_plot_negative_coords_clamped():
    rec = pack_draw_op("plot", [-5, 80, "white", 100])
    cmds = list(unpack_draw_batch(rec))
    assert cmds[0][1][:2] == (0, 80)


def test_mplot_via_pack_draw_op():
    rec = pack_draw_op("mplot", [1, 2, 42, 75, None, None])
    assert rec[0] == OP_PLOT
    cmds = list(unpack_draw_batch(rec))
    assert cmds[0][1][2] == 42


def test_expanding_circles_style_polygon():
    rec = pack_draw_op(
        "draw_polygon",
        [10, 10, 4, 5, 20, 80, 0, False, None, "instant"],
    )
    cmds = list(unpack_draw_batch(rec))
    assert cmds[0][0] == "draw_polygon"
    assert cmds[0][1][3] == 5
