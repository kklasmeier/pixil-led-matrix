"""
Sprite batch protocol for Pixil → rgb_matrix_lib.

Batches show_sprite / move_sprite / hide_sprite into one queue command per frame.
"""

from __future__ import annotations

import struct
from typing import Any, Iterator, List, Optional, Tuple

from shared.mplot_protocol import encode_buffer, decode_buffer

OP_SHOW = 1
OP_MOVE = 2
OP_HIDE = 3

_MAX_NAME_LEN = 48
# op B, name_len B, name[name_len], x h, y h, instance B, flags B, cel b (optional -1 = none)
_SHOW_MOVE_FMT = "<2B"
_SHOW_MOVE_TAIL = "<2h2B"
_HIDE_FMT = "<2B"
_HIDE_TAIL = "<B"


def _pack_name(name: str) -> bytes:
    raw = name.encode("utf-8")
    if len(raw) > _MAX_NAME_LEN:
        raise ValueError(f"sprite name too long (max {_MAX_NAME_LEN}): {name!r}")
    return bytes([len(raw)]) + raw


def _unpack_name(data: bytes, offset: int) -> Tuple[str, int]:
    if offset >= len(data):
        raise ValueError("truncated sprite_batch name length")
    nlen = data[offset]
    offset += 1
    end = offset + nlen
    if end > len(data):
        raise ValueError("truncated sprite_batch name")
    return data[offset:end].decode("utf-8"), end


def pack_show_record(name: str, x: int, y: int, instance_id: int = 0, cel_idx: Optional[int] = None) -> bytes:
    cel_byte = 255 if cel_idx is None else int(cel_idx) & 0xFF
    return (
        bytes([OP_SHOW])
        + _pack_name(name)
        + struct.pack("<2h2B", int(x), int(y), int(instance_id) & 0xFF, cel_byte)
    )


def pack_move_record(name: str, x: int, y: int, instance_id: int = 0, cel_idx: Optional[int] = None) -> bytes:
    cel_byte = 255 if cel_idx is None else int(cel_idx) & 0xFF
    return (
        bytes([OP_MOVE])
        + _pack_name(name)
        + struct.pack("<2h2B", int(x), int(y), int(instance_id) & 0xFF, cel_byte)
    )


def pack_hide_record(name: str, instance_id: int = 0) -> bytes:
    return bytes([OP_HIDE]) + _pack_name(name) + struct.pack("<B", int(instance_id) & 0xFF)


def pack_sprite_op(cmd_name: str, args: List[Any]) -> bytes:
    """Pack one sprite op from parsed Pixil arguments (name, x, y, ...)."""
    name = str(args[0]).strip().strip('"').strip("'")
    if cmd_name == "hide_sprite":
        instance_id = int(args[1]) if len(args) > 1 else 0
        return pack_hide_record(name, instance_id)
    x = int(float(args[1]))
    y = int(float(args[2]))
    instance_id = int(args[3]) if len(args) > 3 else 0
    cel_idx: Optional[int] = None
    if cmd_name == "show_sprite" and len(args) > 5:
        cel_idx = int(args[5])
    elif cmd_name == "move_sprite" and len(args) > 4:
        cel_idx = int(args[4])
    if cmd_name == "show_sprite":
        return pack_show_record(name, x, y, instance_id, cel_idx)
    if cmd_name == "move_sprite":
        return pack_move_record(name, x, y, instance_id, cel_idx)
    raise ValueError(f"sprite_batch unsupported command: {cmd_name}")


def unpack_sprite_batch(binary_data: bytes) -> Iterator[Tuple[str, tuple]]:
    """Yield (command_name, args_tuple) in submission order."""
    offset = 0
    n = len(binary_data)
    while offset < n:
        op = binary_data[offset]
        offset += 1
        name, offset = _unpack_name(binary_data, offset)
        if op == OP_HIDE:
            if offset + 1 > n:
                raise ValueError("truncated hide_sprite record")
            (instance_id,) = struct.unpack("<B", binary_data[offset : offset + 1])
            offset += 1
            yield ("hide_sprite", (name, int(instance_id)))
            continue
        if op in (OP_SHOW, OP_MOVE):
            if offset + struct.calcsize("<2h2B") > n:
                raise ValueError(f"truncated {op} sprite record")
            x, y, instance_id, cel_b = struct.unpack(
                "<2h2B", binary_data[offset : offset + struct.calcsize("<2h2B")]
            )
            offset += struct.calcsize("<2h2B")
            cel_idx = None if cel_b == 255 else int(cel_b)
            cmd = "show_sprite" if op == OP_SHOW else "move_sprite"
            if cel_idx is None:
                yield (cmd, (name, x, y, int(instance_id)))
            elif cmd == "show_sprite":
                yield (cmd, (name, x, y, int(instance_id), 0, cel_idx))
            else:
                yield (cmd, (name, x, y, int(instance_id), cel_idx))
            continue
        raise ValueError(f"unknown sprite_batch op code: {op}")


def encode_sprite_buffer(records: bytes) -> str:
    return encode_buffer(records)


def decode_sprite_buffer(encoded: str) -> bytes:
    return decode_buffer(encoded)
