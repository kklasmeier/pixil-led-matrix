"""Pixil-side helpers for unified draw_batch frame buffering."""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Union

from shared.draw_batch_protocol import (
    OP_PLOT,
    encode_buffer,
    pack_draw_op,
    pack_line_record,
)
from shared.mplot_protocol import MPLOT_RECORD_SIZE

from .array_manager import PixilArray

# Commands packed into draw_batch (not draw_text, sprites, etc.)
DRAW_BATCH_COMMANDS = frozenset({
    "plot",
    "mplot",
    "draw_line",
    "draw_rectangle",
    "draw_circle",
    "draw_polygon",
    "draw_ellipse",
    "draw_arc",
})

NumericSeq = Union[PixilArray, Sequence[float], list]


def append_parsed_draw(draw_buffer: bytearray, cmd_name: str, parsed_args: List) -> None:
    packed = pack_draw_op(cmd_name, parsed_args)
    if packed:
        draw_buffer.extend(packed)


def _seq_data(value: NumericSeq) -> list:
    if isinstance(value, PixilArray):
        return value.data
    return value  # type: ignore[return-value]


def append_draw_lines(
    draw_buffer: bytearray,
    x0: NumericSeq,
    y0: NumericSeq,
    x1: NumericSeq,
    y1: NumericSeq,
    color: Union[str, int],
    intensity: Optional[Union[float, int, NumericSeq]] = 100,
    count: Optional[int] = None,
) -> int:
    """Pack N draw_line records from endpoint arrays into draw_buffer.

    ``color`` is shared by all segments. ``intensity`` may be a scalar or a
    per-segment numeric array. Fully off-panel segments are skipped.
    Returns the number of records appended (after clipping).
    """
    x0d = _seq_data(x0)
    y0d = _seq_data(y0)
    x1d = _seq_data(x1)
    y1d = _seq_data(y1)
    n = min(len(x0d), len(y0d), len(x1d), len(y1d))
    if count is not None:
        n = min(n, int(count))

    inten_seq = None
    inten_scalar = 100
    if intensity is None:
        inten_scalar = 100
    elif isinstance(intensity, (int, float)):
        inten_scalar = int(intensity)
    elif isinstance(intensity, PixilArray) or (
        isinstance(intensity, (list, tuple)) and not isinstance(intensity, (str, bytes))
    ):
        inten_seq = _seq_data(intensity)  # type: ignore[arg-type]
        if len(inten_seq) < n:
            raise ValueError(
                f"draw_lines: intensity array length {len(inten_seq)} "
                f"is shorter than count {n}"
            )
    else:
        inten_scalar = int(intensity)  # type: ignore[arg-type]

    added = 0
    for i in range(n):
        inten = inten_scalar if inten_seq is None else int(inten_seq[i])
        packed = pack_line_record(
            x0d[i], y0d[i], x1d[i], y1d[i], color, inten
        )
        if packed:
            draw_buffer.extend(packed)
            added += 1
    return added


def append_mplot_bulk(
    draw_buffer: bytearray,
    xs,
    ys,
    color_ids,
    intensities,
) -> int:
    """Pack many mplot records into draw_buffer in one extend. Returns record count."""
    import struct

    import numpy as np

    from shared.mplot_protocol import BURNOUT_MODE_INSTANT, BURNOUT_NONE, STRUCT_FORMAT

    n = len(xs)
    if n == 0:
        return 0
    op = OP_PLOT
    record_size = 1 + MPLOT_RECORD_SIZE
    out = bytearray(n * record_size)
    offset = 0
    xs_i = xs.astype(np.uint16)
    ys_i = ys.astype(np.uint16)
    cids = color_ids.astype(np.int16)
    ints = intensities.astype(np.uint8)
    fmt = STRUCT_FORMAT
    burnout_none = BURNOUT_NONE
    mode_instant = BURNOUT_MODE_INSTANT
    for i in range(n):
        out[offset] = op
        offset += 1
        struct.pack_into(
            fmt,
            out,
            offset,
            int(xs_i[i]),
            int(ys_i[i]),
            int(cids[i]),
            int(ints[i]),
            burnout_none,
            mode_instant,
        )
        offset += MPLOT_RECORD_SIZE
    draw_buffer.extend(out)
    return n


def flush_draw_buffer(
    draw_buffer: bytearray,
    store_frame_command: Callable[[str], None],
) -> int:
    """Encode buffer as draw_batch; return number of records flushed."""
    if not draw_buffer:
        return 0
    encoded = encode_buffer(bytes(draw_buffer))
    store_frame_command(f'draw_batch("{encoded}")')
    count = len(draw_buffer)  # approximate; cleared below
    draw_buffer.clear()
    return count
