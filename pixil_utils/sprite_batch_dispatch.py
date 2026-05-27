"""Pixil-side helpers for sprite_batch frame buffering."""

from __future__ import annotations

from typing import Any, Callable, List

from shared.sprite_batch_protocol import encode_sprite_buffer, pack_sprite_op

SPRITE_BATCH_COMMANDS = frozenset({"show_sprite", "move_sprite", "hide_sprite"})


def append_parsed_sprite(sprite_buffer: bytearray, cmd_name: str, parsed_args: List[Any]) -> None:
    sprite_buffer.extend(pack_sprite_op(cmd_name, parsed_args))


def flush_sprite_buffer(
    sprite_buffer: bytearray,
    store_frame_command: Callable[[str], None],
) -> int:
    if not sprite_buffer:
        return 0
    encoded = encode_sprite_buffer(bytes(sprite_buffer))
    store_frame_command(f'sprite_batch("{encoded}")')
    count = len(sprite_buffer)
    sprite_buffer.clear()
    return count
