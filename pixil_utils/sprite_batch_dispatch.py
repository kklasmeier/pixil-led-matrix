"""Pixil-side helpers for sprite_batch frame buffering."""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence, Union

from shared.sprite_batch_protocol import (
    encode_sprite_buffer,
    pack_move_record,
    pack_sprite_op,
)

from .array_manager import PixilArray

SPRITE_BATCH_COMMANDS = frozenset({"show_sprite", "move_sprite", "hide_sprite"})

NumericSeq = Union[PixilArray, Sequence[float], list]


def append_parsed_sprite(sprite_buffer: bytearray, cmd_name: str, parsed_args: List[Any]) -> None:
    sprite_buffer.extend(pack_sprite_op(cmd_name, parsed_args))


def _seq_data(value: NumericSeq) -> list:
    if isinstance(value, PixilArray):
        return value.data
    return value  # type: ignore[return-value]


def append_move_sprites(
    sprite_buffer: bytearray,
    name: str,
    x: NumericSeq,
    y: NumericSeq,
    cel: Optional[NumericSeq] = None,
    count: Optional[int] = None,
    z: Optional[NumericSeq] = None,
) -> int:
    """Pack N move_sprite records (instance ids 0..n-1) in one producer pass.

    Returns the number of records appended. Optional ``cel`` is per-instance;
    when omitted, cel is left unchanged on the consumer (cel byte 255).
    Optional ``z`` sets per-instance z_index (batched MOVE_Z records).
    """
    xd = _seq_data(x)
    yd = _seq_data(y)
    n = min(len(xd), len(yd))
    if count is not None:
        n = min(n, int(count))
    cd = _seq_data(cel) if cel is not None else None
    zd = _seq_data(z) if z is not None else None
    if cd is not None and len(cd) < n:
        raise ValueError(
            f"move_sprites: cel array length {len(cd)} is shorter than count {n}"
        )
    if zd is not None and len(zd) < n:
        raise ValueError(
            f"move_sprites: z array length {len(zd)} is shorter than count {n}"
        )
    for i in range(n):
        cel_idx = None if cd is None else int(cd[i])
        z_index = None if zd is None else int(zd[i])
        sprite_buffer.extend(
            pack_move_record(
                name, int(round(xd[i])), int(round(yd[i])), i, cel_idx, z_index
            )
        )
    return n


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
