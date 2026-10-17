"""Pixil dispatch and validation for points_project3d and array_lerp."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

from .array_manager import PixilArray
from .parameter_types import split_command_parameters, validate_command_params
from .particle_commands import (
    _eval_number,
    _optional_count,
    _optional_token,
    require_array_name,
    require_numeric_array,
)
from .points_engine import array_lerp, points_project3d

_ARRAY_NAME = re.compile(r"^v_\w+$")

_COMMANDS = frozenset({
    "points_project3d",
    "array_lerp",
})


def is_points_command(name: str) -> bool:
    return name in _COMMANDS


def _cmd_error(command: str, message: str) -> ValueError:
    return ValueError(f"{command}: {message}")


def _strip_quotes(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def _same_length(command: str, arrays: List[Tuple[str, PixilArray]]) -> int:
    length = arrays[0][1].size
    for name, arr in arrays[1:]:
        if arr.size != length:
            raise _cmd_error(
                command,
                f"arrays must be the same length "
                f"({arrays[0][0]}={length}, {name}={arr.size})",
            )
    return length


def _looks_like_array_name(token: str) -> bool:
    return bool(_ARRAY_NAME.match(_strip_quotes(token)))


def _optional_depth_and_count(
    command: str,
    tokens: List[str],
    start: int,
    variables: Any,
    state_len: int,
) -> Tuple[Optional[PixilArray], Optional[int]]:
    """Parse optional [depth_array], [count].

    A ``v_*`` token is depth. A numeric token (with no prior depth) is count.
    """
    tok0 = _optional_token(tokens, start)
    if tok0 is None:
        return None, None

    if _looks_like_array_name(tok0):
        name = require_array_name(command, tok0, "depth")
        depth = require_numeric_array(variables, name, command, "depth")
        if depth.size != state_len:
            raise _cmd_error(
                command,
                f"depth array {name!r} length {depth.size} does not match "
                f"state length {state_len}",
            )
        count = _optional_count(
            command, _optional_token(tokens, start + 1), variables, state_len,
        )
        return depth, count

    count = _optional_count(command, tok0, variables, state_len)
    return None, count


def run_points_command(command: str, tokens: List[str], variables: Any) -> int:
    """Validate tokens and run one points/array kernel. Returns 0."""
    tokens = validate_command_params(command, ", ".join(tokens) if tokens else "")

    if command == "array_lerp":
        a_name = require_array_name(command, tokens[0], "a")
        b_name = require_array_name(command, tokens[1], "b")
        out_name = require_array_name(command, tokens[2], "out")
        a = require_numeric_array(variables, a_name, command, "a")
        b = require_numeric_array(variables, b_name, command, "b")
        out = require_numeric_array(variables, out_name, command, "out")
        _same_length(command, [(a_name, a), (b_name, b), (out_name, out)])
        t = _eval_number(command, tokens[3], "t", variables)
        count = _optional_count(
            command, _optional_token(tokens, 4), variables, a.size,
        )
        array_lerp(a, b, out, t, count=count)
        return 0

    if command == "points_project3d":
        names = [
            ("x", tokens[0]),
            ("y", tokens[1]),
            ("z", tokens[2]),
            ("sx", tokens[3]),
            ("sy", tokens[4]),
        ]
        arrays: List[Tuple[str, PixilArray]] = []
        for param, tok in names:
            name = require_array_name(command, tok, param)
            arr = require_numeric_array(variables, name, command, param)
            arrays.append((name, arr))
        state_len = _same_length(command, arrays)
        x, y, z = arrays[0][1], arrays[1][1], arrays[2][1]
        sx, sy = arrays[3][1], arrays[4][1]

        ax = _eval_number(command, tokens[5], "ax", variables)
        ay = _eval_number(command, tokens[6], "ay", variables)
        az = _eval_number(command, tokens[7], "az", variables)
        scale = _eval_number(command, tokens[8], "scale", variables)
        camera = _eval_number(command, tokens[9], "camera", variables)
        cx = _eval_number(command, tokens[10], "cx", variables)
        cy = _eval_number(command, tokens[11], "cy", variables)

        depth, count = _optional_depth_and_count(
            command, tokens, 12, variables, state_len,
        )
        points_project3d(
            x, y, z, sx, sy,
            ax, ay, az, scale, camera, cx, cy,
            depth=depth, count=count,
        )
        return 0

    raise _cmd_error(command, "unknown points command")


def run_points_line(line: str, variables: Any) -> int:
    match = re.match(r"^(points_\w+|array_lerp)\((.*)\)\s*$", line.strip())
    if not match or not is_points_command(match.group(1)):
        raise ValueError(f"Not a points/array command: {line}")
    command = match.group(1)
    tokens = split_command_parameters(match.group(2))
    return run_points_command(command, tokens, variables)
