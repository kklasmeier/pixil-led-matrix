"""
Unified frame draw batch protocol for Pixil → rgb_matrix_lib.

One ordered bytearray of typed records (plot + all draw_* shapes).
Flush as draw_batch(encoded) at end_frame or mflush.

Record layout: uint8 op_code + fixed-size payload per op.
PLOT payload matches mplot_protocol (20 bytes).
"""

from __future__ import annotations

import struct
from typing import Any, Iterator, List, Optional, Tuple, Union

from shared.mplot_protocol import (
    BURNOUT_NONE,
    INTENSITY_DEFAULT,
    MPLOT_RECORD_SIZE,
    encode_buffer,
    decode_buffer,
    get_burnout_mode_int,
    get_burnout_mode_str,
    get_color_from_id,
    get_color_id,
    normalize_mplot_color,
    pack_mplot,
)

# Op codes
OP_PLOT = 1
OP_LINE = 2
OP_RECT = 3
OP_CIRCLE = 4
OP_POLYGON = 5
OP_ELLIPSE = 6
OP_ARC = 7

def _payload_size(fmt: str) -> int:
    return struct.calcsize(fmt)


_LINE_FMT = "<4HhBIB3x"
_RECT_FMT = "<4HhBIBB2x"
_CIRCLE_FMT = "<3HhBIBB3x"
_POLYGON_FMT = "<4HfhBIBB3x"
_ELLIPSE_FMT = "<4HfhBIBB3x"
_ARC_FMT = "<4HfhBIBB3x"

OP_RECORD_SIZES = {
    OP_PLOT: 1 + MPLOT_RECORD_SIZE,
    OP_LINE: 1 + _payload_size(_LINE_FMT),
    OP_RECT: 1 + _payload_size(_RECT_FMT),
    OP_CIRCLE: 1 + _payload_size(_CIRCLE_FMT),
    OP_POLYGON: 1 + _payload_size(_POLYGON_FMT),
    OP_ELLIPSE: 1 + _payload_size(_ELLIPSE_FMT),
    OP_ARC: 1 + _payload_size(_ARC_FMT),
}


def _intensity_byte(intensity: Optional[int]) -> int:
    if intensity is None:
        return INTENSITY_DEFAULT
    return int(intensity)


def _burnout_uint(burnout: Optional[int]) -> int:
    if burnout is None:
        return BURNOUT_NONE
    return int(burnout)


def _fill_byte(fill: Any) -> int:
    if isinstance(fill, bool):
        return 1 if fill else 0
    if isinstance(fill, str):
        return 1 if fill.strip().lower() in ("true", "1", "yes") else 0
    return 1 if fill else 0


def _color_id_from_arg(color: Any) -> int:
    return get_color_id(normalize_mplot_color(color))


def _coord_int(value: Any) -> int:
    """Coerce plot/mplot coordinates from parse_value (may be str digits)."""
    return int(float(value))


def _coord_uint16(value: Any) -> int:
    """Coerce to unsigned 16-bit for struct H fields (clamp off-screen coords)."""
    n = int(float(value))
    if n < 0:
        return 0
    if n > 65535:
        return 65535
    return n


# Default piMatrix panel (rgb_matrix_lib options.rows/cols)
DEFAULT_PANEL_WIDTH = 64
DEFAULT_PANEL_HEIGHT = 64

_INSIDE, _LEFT, _RIGHT, _BOTTOM, _TOP = 0, 1, 2, 4, 8


def _line_outcode(x: float, y: float, xmax: float, ymax: float) -> int:
    code = _INSIDE
    if x < 0:
        code |= _LEFT
    elif x > xmax:
        code |= _RIGHT
    if y < 0:
        code |= _BOTTOM
    elif y > ymax:
        code |= _TOP
    return code


def clip_line_segment(
    x0: Any,
    y0: Any,
    x1: Any,
    y1: Any,
    width: int = DEFAULT_PANEL_WIDTH,
    height: int = DEFAULT_PANEL_HEIGHT,
) -> Optional[Tuple[int, int, int, int]]:
    """
    Cohen–Sutherland clip to [0, width-1] x [0, height-1].

    Clips the segment instead of clamping each endpoint independently (which
    collapses off-screen trapezoids and hides pan/tilt on 3D-style scripts).
    Returns None when the segment is fully outside the panel.
    """
    x0f, y0f = float(x0), float(y0)
    x1f, y1f = float(x1), float(y1)
    xmax = float(width - 1)
    ymax = float(height - 1)
    out0 = _line_outcode(x0f, y0f, xmax, ymax)
    out1 = _line_outcode(x1f, y1f, xmax, ymax)
    while True:
        if not (out0 | out1):
            return (
                int(round(x0f)),
                int(round(y0f)),
                int(round(x1f)),
                int(round(y1f)),
            )
        if out0 & out1:
            return None
        out = out0 if out0 else out1
        if out & _TOP:
            x = x0f + (x1f - x0f) * (ymax - y0f) / (y1f - y0f)
            y = ymax
        elif out & _BOTTOM:
            x = x0f + (x1f - x0f) * (0.0 - y0f) / (y1f - y0f)
            y = 0.0
        elif out & _RIGHT:
            y = y0f + (y1f - y0f) * (xmax - x0f) / (x1f - x0f)
            x = xmax
        else:  # _LEFT
            y = y0f + (y1f - y0f) * (0.0 - x0f) / (x1f - x0f)
            x = 0.0
        if out == out0:
            x0f, y0f = x, y
            out0 = _line_outcode(x0f, y0f, xmax, ymax)
        else:
            x1f, y1f = x, y
            out1 = _line_outcode(x1f, y1f, xmax, ymax)


def _optional_int_arg(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(float(value))


def pack_plot_record(
    x: int,
    y: int,
    color: Union[str, int],
    intensity: Optional[int] = None,
    burnout: Optional[int] = None,
    burnout_mode: Optional[str] = None,
) -> bytes:
    return bytes([OP_PLOT]) + pack_mplot(x, y, color, intensity, burnout, burnout_mode)


def pack_draw_op(cmd_name: str, args: List[Any]) -> bytes:
    """
  Pack one frame draw command from already-parsed Pixil arguments.

    Args order must match PARAMETER_TYPES / expand_legacy_shape_params output.
    """
    if cmd_name in ("plot", "mplot"):
        x, y, color = _coord_uint16(args[0]), _coord_uint16(args[1]), args[2]
        intensity = _optional_int_arg(args[3]) if len(args) > 3 else None
        burnout = _optional_int_arg(args[4]) if len(args) > 4 else None
        burnout_mode = args[5] if len(args) > 5 else None
        if isinstance(burnout_mode, str):
            burnout_mode = burnout_mode.strip('"').strip("'")
        return pack_plot_record(x, y, color, intensity, burnout, burnout_mode)

    if cmd_name == "draw_line":
        x0, y0, x1, y1, color = args[0], args[1], args[2], args[3], args[4]
        intensity = args[5] if len(args) > 5 else 100
        burnout = args[6] if len(args) > 6 else None
        burnout_mode = args[7] if len(args) > 7 else "instant"
        clipped = clip_line_segment(x0, y0, x1, y1)
        if clipped is None:
            return b""
        cx0, cy0, cx1, cy1 = clipped
        payload = struct.pack(
            _LINE_FMT,
            _coord_uint16(cx0), _coord_uint16(cy0), _coord_uint16(cx1), _coord_uint16(cy1),
            _color_id_from_arg(color),
            _intensity_byte(intensity),
            _burnout_uint(burnout),
            get_burnout_mode_int(burnout_mode),
        )
        return bytes([OP_LINE]) + payload

    if cmd_name == "draw_rectangle":
        x, y, w, h, color = args[0], args[1], args[2], args[3], args[4]
        intensity = args[5] if len(args) > 5 else 100
        fill = args[6] if len(args) > 6 else False
        burnout = args[7] if len(args) > 7 else None
        burnout_mode = args[8] if len(args) > 8 else "instant"
        payload = struct.pack(
            _RECT_FMT,
            _coord_uint16(x), _coord_uint16(y), _coord_uint16(w), _coord_uint16(h),
            _color_id_from_arg(color),
            _intensity_byte(intensity),
            _burnout_uint(burnout),
            get_burnout_mode_int(burnout_mode),
            _fill_byte(fill),
        )
        return bytes([OP_RECT]) + payload

    if cmd_name == "draw_circle":
        x, y, radius, color = args[0], args[1], args[2], args[3]
        intensity = args[4] if len(args) > 4 else 100
        fill = args[5] if len(args) > 5 else False
        burnout = args[6] if len(args) > 6 else None
        burnout_mode = args[7] if len(args) > 7 else "instant"
        payload = struct.pack(
            _CIRCLE_FMT,
            _coord_uint16(x), _coord_uint16(y), _coord_uint16(radius),
            _color_id_from_arg(color),
            _intensity_byte(intensity),
            _burnout_uint(burnout),
            get_burnout_mode_int(burnout_mode),
            _fill_byte(fill),
        )
        return bytes([OP_CIRCLE]) + payload

    if cmd_name == "draw_polygon":
        x, y, radius, sides, color = args[0], args[1], args[2], args[3], args[4]
        intensity = args[5] if len(args) > 5 else 100
        rotation = float(args[6]) if len(args) > 6 else 0.0
        fill = args[7] if len(args) > 7 else False
        burnout = args[8] if len(args) > 8 else None
        burnout_mode = args[9] if len(args) > 9 else "instant"
        payload = struct.pack(
            _POLYGON_FMT,
            _coord_uint16(x), _coord_uint16(y), _coord_uint16(radius), _coord_uint16(sides),
            float(rotation),
            _color_id_from_arg(color),
            _intensity_byte(intensity),
            _burnout_uint(burnout),
            get_burnout_mode_int(burnout_mode),
            _fill_byte(fill),
        )
        return bytes([OP_POLYGON]) + payload

    if cmd_name == "draw_ellipse":
        xc, yc, xr, yr, color = args[0], args[1], args[2], args[3], args[4]
        intensity = args[5] if len(args) > 5 else 100
        fill = args[6] if len(args) > 6 else False
        rotation = float(args[7]) if len(args) > 7 else 0.0
        burnout = args[8] if len(args) > 8 else None
        burnout_mode = args[9] if len(args) > 9 else "instant"
        payload = struct.pack(
            _ELLIPSE_FMT,
            _coord_uint16(xc), _coord_uint16(yc), _coord_uint16(xr), _coord_uint16(yr),
            float(rotation),
            _color_id_from_arg(color),
            _intensity_byte(intensity),
            _burnout_uint(burnout),
            get_burnout_mode_int(burnout_mode),
            _fill_byte(fill),
        )
        return bytes([OP_ELLIPSE]) + payload

    if cmd_name == "draw_arc":
        x1, y1, x2, y2, bulge, color = args[0], args[1], args[2], args[3], args[4], args[5]
        intensity = args[6] if len(args) > 6 else 100
        fill = args[7] if len(args) > 7 else False
        burnout = args[8] if len(args) > 8 else None
        burnout_mode = args[9] if len(args) > 9 else "instant"
        payload = struct.pack(
            _ARC_FMT,
            _coord_uint16(x1), _coord_uint16(y1), _coord_uint16(x2), _coord_uint16(y2),
            float(bulge),
            _color_id_from_arg(color),
            _intensity_byte(intensity),
            _burnout_uint(burnout),
            get_burnout_mode_int(burnout_mode),
            _fill_byte(fill),
        )
        return bytes([OP_ARC]) + payload

    raise ValueError(f"draw_batch does not support command: {cmd_name}")


def _unpack_common_tail(
    intensity_b: int, burnout_u: int, mode_b: int,
) -> Tuple[Optional[int], Optional[int], str]:
    intensity = None if intensity_b == INTENSITY_DEFAULT else intensity_b
    burnout = None if burnout_u == BURNOUT_NONE else burnout_u
    mode = get_burnout_mode_str(mode_b)
    return intensity, burnout, mode


def unpack_draw_batch(binary_data: bytes) -> Iterator[Tuple[str, tuple]]:
    """
    Yield (command_name, args_tuple) in submission order for CommandExecutor dispatch.
    """
    offset = 0
    n = len(binary_data)
    while offset < n:
        if offset >= n:
            break
        op = binary_data[offset]
        size = OP_RECORD_SIZES.get(op)
        if size is None:
            raise ValueError(f"Unknown draw_batch op code: {op}")
        if offset + size > n:
            raise ValueError(f"Truncated draw_batch record op={op} at offset {offset}")
        chunk = binary_data[offset : offset + size]
        offset += size
        payload = chunk[1:]

        if op == OP_PLOT:
            from shared.mplot_protocol import unpack_mplot_batch

            yield ("plot", next(iter(unpack_mplot_batch(payload))))
            continue

        if op == OP_LINE:
            x0, y0, x1, y1, cid, ib, bu, mb = struct.unpack(_LINE_FMT, payload)
            intensity, burnout, mode = _unpack_common_tail(ib, bu, mb)
            yield (
                "draw_line",
                (x0, y0, x1, y1, get_color_from_id(cid), intensity or 100, burnout, mode),
            )
            continue

        if op == OP_RECT:
            x, y, w, h, cid, ib, bu, mb, fill_b = struct.unpack(_RECT_FMT, payload)
            intensity, burnout, mode = _unpack_common_tail(ib, bu, mb)
            yield (
                "draw_rectangle",
                (x, y, w, h, get_color_from_id(cid), intensity or 100, bool(fill_b), burnout, mode),
            )
            continue

        if op == OP_CIRCLE:
            x, y, r, cid, ib, bu, mb, fill_b = struct.unpack(_CIRCLE_FMT, payload)
            intensity, burnout, mode = _unpack_common_tail(ib, bu, mb)
            yield (
                "draw_circle",
                (x, y, r, get_color_from_id(cid), intensity or 100, bool(fill_b), burnout, mode),
            )
            continue

        if op == OP_POLYGON:
            x, y, r, sides, rot_f, cid, ib, bu, mb, fill_b = struct.unpack(
                _POLYGON_FMT, payload
            )
            intensity, burnout, mode = _unpack_common_tail(ib, bu, mb)
            yield (
                "draw_polygon",
                (
                    x, y, r, sides,
                    get_color_from_id(cid),
                    intensity or 100,
                    rot_f,
                    bool(fill_b),
                    burnout,
                    mode,
                ),
            )
            continue

        if op == OP_ELLIPSE:
            xc, yc, xr, yr, rot_f, cid, ib, bu, mb, fill_b = struct.unpack(_ELLIPSE_FMT, payload)
            intensity, burnout, mode = _unpack_common_tail(ib, bu, mb)
            yield (
                "draw_ellipse",
                (
                    xc, yc, xr, yr,
                    get_color_from_id(cid),
                    intensity or 100,
                    bool(fill_b),
                    rot_f,
                    burnout,
                    mode,
                ),
            )
            continue

        if op == OP_ARC:
            x1, y1, x2, y2, bulge, cid, ib, bu, mb, fill_b = struct.unpack(_ARC_FMT, payload)
            intensity, burnout, mode = _unpack_common_tail(ib, bu, mb)
            yield (
                "draw_arc",
                (
                    x1, y1, x2, y2, bulge,
                    get_color_from_id(cid),
                    intensity or 100,
                    bool(fill_b),
                    burnout,
                    mode,
                ),
            )
            continue

        raise ValueError(f"Unhandled op {op}")


__all__ = [
    "OP_PLOT",
    "OP_LINE",
    "OP_RECT",
    "OP_CIRCLE",
    "OP_POLYGON",
    "OP_ELLIPSE",
    "OP_ARC",
    "pack_draw_op",
    "pack_plot_record",
    "unpack_draw_batch",
    "encode_buffer",
    "decode_buffer",
    "OP_RECORD_SIZES",
]
