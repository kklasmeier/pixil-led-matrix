"""Pixil-side helpers for unified draw_batch frame buffering."""

from __future__ import annotations

from typing import Any, Callable, List

from shared.draw_batch_protocol import encode_buffer, pack_draw_op

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


def append_parsed_draw(draw_buffer: bytearray, cmd_name: str, parsed_args: List[Any]) -> None:
    packed = pack_draw_op(cmd_name, parsed_args)
    if packed:
        draw_buffer.extend(packed)


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
