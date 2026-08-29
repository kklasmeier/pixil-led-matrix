"""Pixil dispatch and validation for generic particle kernels."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple, Union

from .array_manager import PixilArray
from .math_functions import evaluate_math_expression
from .parameter_types import split_command_parameters, validate_command_params
from .particle_engine import (
    particle_collide_bounds,
    particle_collide_circles,
    particle_integrate,
)

_ARRAY_NAME = re.compile(r"^v_\w+$")

_COMMANDS = frozenset({
    "particle_integrate",
    "particle_collide_bounds",
    "particle_collide_circles",
})


def is_particle_command(name: str) -> bool:
    return name in _COMMANDS


def _cmd_error(command: str, message: str) -> ValueError:
    return ValueError(f"{command}: {message}")


def _strip_quotes(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def require_array_name(command: str, token: str, param: str) -> str:
    name = _strip_quotes(token)
    if not _ARRAY_NAME.match(name):
        raise _cmd_error(
            command,
            f"parameter '{param}' must be a numeric array name starting with v_ "
            f"(got {token!r})",
        )
    return name


def require_numeric_array(variables: Any, name: str, command: str, param: str) -> PixilArray:
    try:
        value = variables.get(name)
    except KeyError:
        raise _cmd_error(command, f"array {name!r} ({param}) is not defined") from None
    if not isinstance(value, PixilArray):
        raise _cmd_error(
            command,
            f"{name!r} ({param}) is not an array",
        )
    if value.array_type != "numeric":
        raise _cmd_error(
            command,
            f"{name!r} ({param}) must be a numeric array, not {value.array_type}",
        )
    return value


def _optional_token(tokens: List[str], index: int) -> Optional[str]:
    if index >= len(tokens):
        return None
    token = tokens[index].strip()
    return token if token else None


def _eval_number(command: str, token: str, param: str, variables: Any) -> float:
    try:
        result = evaluate_math_expression(token, variables)
    except Exception as exc:
        raise _cmd_error(
            command,
            f"parameter '{param}' is not a number ({token!r}): {exc}",
        ) from exc
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise _cmd_error(
            command,
            f"parameter '{param}' must be numeric (got {result!r} from {token!r})",
        )
    return float(result)


def resolve_scalar_or_array(
    command: str,
    token: str,
    param: str,
    variables: Any,
) -> Union[float, PixilArray]:
    name = _strip_quotes(token)
    if _ARRAY_NAME.match(name):
        try:
            value = variables.get(name)
        except KeyError:
            raise _cmd_error(
                command,
                f"value {name!r} ({param}) is not defined",
            ) from None
        if isinstance(value, PixilArray):
            if value.array_type != "numeric":
                raise _cmd_error(
                    command,
                    f"{name!r} ({param}) must be numeric, not {value.array_type}",
                )
            return value
        # Scalar variables are valid for radius, mass, and acceleration.
        return _eval_number(command, token, param, variables)
    return _eval_number(command, token, param, variables)


def _state_arrays(
    command: str,
    tokens: List[str],
    variables: Any,
) -> Tuple[PixilArray, PixilArray, PixilArray, PixilArray, PixilArray]:
    names = [
        require_array_name(command, tokens[i], param)
        for i, param in enumerate(("x", "y", "vx", "vy", "active"))
    ]
    arrays = [
        require_numeric_array(variables, name, command, param)
        for name, param in zip(names, ("x", "y", "vx", "vy", "active"))
    ]
    lengths = {name: arr.size for name, arr in zip(names, arrays)}
    if len(set(lengths.values())) != 1:
        detail = ", ".join(f"{name}={size}" for name, size in lengths.items())
        raise _cmd_error(
            command,
            f"x, y, vx, vy, and active must have the same length ({detail})",
        )
    return arrays[0], arrays[1], arrays[2], arrays[3], arrays[4]


def _optional_hit(
    command: str,
    token: Optional[str],
    variables: Any,
    state_len: int,
) -> Optional[PixilArray]:
    if token is None:
        return None
    name = require_array_name(command, token, "hit")
    hit = require_numeric_array(variables, name, command, "hit")
    if hit.size != state_len:
        raise _cmd_error(
            command,
            f"hit array {name!r} length {hit.size} does not match state length {state_len}",
        )
    return hit


def _optional_count(
    command: str,
    token: Optional[str],
    variables: Any,
    state_len: int,
) -> Optional[int]:
    if token is None:
        return None
    count = int(_eval_number(command, token, "count", variables))
    if count < 0:
        raise _cmd_error(command, f"count must be >= 0 (got {count})")
    if count > state_len:
        raise _cmd_error(
            command,
            f"count {count} exceeds array length {state_len}",
        )
    return count


def run_particle_command(command: str, tokens: List[str], variables: Any) -> int:
    """Validate tokens and run one particle kernel. Returns collide pair count or 0."""
    tokens = validate_command_params(command, ", ".join(tokens) if tokens else "")
    if command == "particle_integrate":
        x, y, vx, vy, active = _state_arrays(command, tokens, variables)
        ax = 0.0
        ay = 0.0
        damping = 1.0
        sleep_speed = 0.0
        ax_tok = _optional_token(tokens, 5)
        ay_tok = _optional_token(tokens, 6)
        damp_tok = _optional_token(tokens, 7)
        sleep_tok = _optional_token(tokens, 8)
        count_tok = _optional_token(tokens, 9)
        if ax_tok is not None:
            ax = resolve_scalar_or_array(command, ax_tok, "ax", variables)
        if ay_tok is not None:
            ay = resolve_scalar_or_array(command, ay_tok, "ay", variables)
        if damp_tok is not None:
            damping = _eval_number(command, damp_tok, "damping", variables)
        if sleep_tok is not None:
            sleep_speed = _eval_number(command, sleep_tok, "sleep_speed", variables)
        count = _optional_count(command, count_tok, variables, x.size)
        particle_integrate(
            x, y, vx, vy, active,
            ax=ax, ay=ay, damping=damping, sleep_speed=sleep_speed, count=count,
        )
        return 0

    if command == "particle_collide_bounds":
        x, y, vx, vy, active = _state_arrays(command, tokens, variables)
        left = _eval_number(command, tokens[5], "left", variables)
        right = _eval_number(command, tokens[6], "right", variables)
        top = _eval_number(command, tokens[7], "top", variables)
        bottom = _eval_number(command, tokens[8], "bottom", variables)
        rest_tok = _optional_token(tokens, 9)
        radius_tok = _optional_token(tokens, 10)
        hit_tok = _optional_token(tokens, 11)
        count_tok = _optional_token(tokens, 12)
        restitution = 1.0 if rest_tok is None else _eval_number(
            command, rest_tok, "restitution", variables,
        )
        radius: Union[float, PixilArray] = 0.0
        if radius_tok is not None:
            radius = resolve_scalar_or_array(command, radius_tok, "radius", variables)
            if isinstance(radius, PixilArray) and radius.size != x.size:
                raise _cmd_error(
                    command,
                    f"radius array length {radius.size} does not match state length {x.size}",
                )
        hit = _optional_hit(command, hit_tok, variables, x.size)
        count = _optional_count(command, count_tok, variables, x.size)
        particle_collide_bounds(
            x, y, vx, vy, active,
            left, right, top, bottom,
            restitution=restitution, radius=radius, hit=hit, count=count,
        )
        return 0

    if command == "particle_collide_circles":
        x, y, vx, vy, active = _state_arrays(command, tokens, variables)
        radius = resolve_scalar_or_array(command, tokens[5], "radius", variables)
        if isinstance(radius, PixilArray) and radius.size != x.size:
            raise _cmd_error(
                command,
                f"radius array length {radius.size} does not match state length {x.size}",
            )
        mass_tok = _optional_token(tokens, 6)
        rest_tok = _optional_token(tokens, 7)
        hit_tok = _optional_token(tokens, 8)
        count_tok = _optional_token(tokens, 9)
        mass: Union[float, PixilArray] = 1.0
        if mass_tok is not None:
            mass = resolve_scalar_or_array(command, mass_tok, "mass", variables)
            if isinstance(mass, PixilArray) and mass.size != x.size:
                raise _cmd_error(
                    command,
                    f"mass array length {mass.size} does not match state length {x.size}",
                )
        restitution = 1.0 if rest_tok is None else _eval_number(
            command, rest_tok, "restitution", variables,
        )
        hit = _optional_hit(command, hit_tok, variables, x.size)
        count = _optional_count(command, count_tok, variables, x.size)
        return particle_collide_circles(
            x, y, vx, vy, active,
            radius=radius, mass=mass, restitution=restitution, hit=hit, count=count,
        )

    raise _cmd_error(command, "unknown particle command")


def run_particle_line(line: str, variables: Any) -> int:
    match = re.match(r"^(particle_\w+)\((.*)\)\s*$", line.strip())
    if not match or not is_particle_command(match.group(1)):
        raise ValueError(f"Not a particle command: {line}")
    command = match.group(1)
    tokens = split_command_parameters(match.group(2))
    return run_particle_command(command, tokens, variables)
