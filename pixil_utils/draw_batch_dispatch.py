"""Pixil-side helpers for unified draw_batch frame buffering."""

from __future__ import annotations

from typing import Callable, List

from shared.draw_batch_protocol import OP_PLOT, encode_buffer, pack_draw_op
from shared.mplot_protocol import MPLOT_RECORD_SIZE

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


def append_parsed_draw(draw_buffer: bytearray, cmd_name: str, parsed_args: List) -> None:
    packed = pack_draw_op(cmd_name, parsed_args)
    if packed:
        draw_buffer.extend(packed)


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
