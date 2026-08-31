"""Pixil dispatch and validation for generic particle kernels."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple, Union

from .array_manager import PixilArray
from .math_functions import evaluate_math_expression
from .parameter_types import split_command_parameters, validate_command_params
from .particle_engine import (
    particle_collide_bounds,
    particle_collide_circle_bounds,
    particle_collide_circles,
    particle_collide_static_circles,
    particle_integrate,
)

_ARRAY_NAME = re.compile(r"^v_\w+$")

_COMMANDS = frozenset({
    "particle_integrate",
    "particle_collide_bounds",
    "particle_collide_circle_bounds",
    "particle_collide_circles",
    "particle_collide_static_circles",
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


def resolve_particle_scalar_or_array(
    command: str,
    token: str,
    param: str,
    variables: Any,
    expected_size: int,
) -> Union[float, PixilArray]:
    value = resolve_scalar_or_array(command, token, param, variables)
    if isinstance(value, PixilArray) and value.size != expected_size:
        raise _cmd_error(
            command,
            f"{param} array length {value.size} does not match expected length {expected_size}",
        )
    return value


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


def _parse_response(command: str, token: Optional[str]) -> str:
    if token is None:
        return "impulse"
    mode = _strip_quotes(token).strip().lower()
    if mode not in ("impulse", "reflect"):
        raise _cmd_error(
            command,
            "parameter 'response' must be 'impulse' or 'reflect' "
            f"(got {token!r})",
        )
    return mode


def _parse_integration_mode(command: str, token: Optional[str]) -> str:
    if token is None:
        return "post_move"
    mode = _strip_quotes(token).strip().lower()
    if mode not in ("post_move", "pre_move"):
        raise _cmd_error(
            command,
            "parameter 'integration_mode' must be 'post_move' or 'pre_move' "
            f"(got {token!r})",
        )
    return mode


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
        mode_tok = _optional_token(tokens, 10)
        max_speed_tok = _optional_token(tokens, 11)
        if ax_tok is not None:
            ax = resolve_scalar_or_array(command, ax_tok, "ax", variables)
        if ay_tok is not None:
            ay = resolve_scalar_or_array(command, ay_tok, "ay", variables)
        if damp_tok is not None:
            damping = _eval_number(command, damp_tok, "damping", variables)
        if sleep_tok is not None:
            sleep_speed = _eval_number(command, sleep_tok, "sleep_speed", variables)
        count = _optional_count(command, count_tok, variables, x.size)
        integration_mode = _parse_integration_mode(command, mode_tok)
        max_speed: Optional[Union[float, PixilArray]] = None
        if max_speed_tok is not None:
            max_speed = resolve_particle_scalar_or_array(
                command, max_speed_tok, "max_speed", variables, x.size,
            )
        particle_integrate(
            x, y, vx, vy, active,
            ax=ax, ay=ay, damping=damping, sleep_speed=sleep_speed, count=count,
            integration_mode=integration_mode, max_speed=max_speed,
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
        restitution: Union[float, PixilArray] = 1.0
        if rest_tok is not None:
            restitution = resolve_particle_scalar_or_array(
                command, rest_tok, "restitution", variables, x.size,
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
        restitution: Union[float, PixilArray] = 1.0
        if rest_tok is not None:
            restitution = resolve_particle_scalar_or_array(
                command, rest_tok, "restitution", variables, x.size,
            )
        hit = _optional_hit(command, hit_tok, variables, x.size)
        count = _optional_count(command, count_tok, variables, x.size)
        return particle_collide_circles(
            x, y, vx, vy, active,
            radius=radius, mass=mass, restitution=restitution, hit=hit, count=count,
        )

    if command == "particle_collide_static_circles":
        x, y, vx, vy, active = _state_arrays(command, tokens, variables)
        obstacle_x_name = require_array_name(command, tokens[5], "obstacle_x")
        obstacle_y_name = require_array_name(command, tokens[6], "obstacle_y")
        obstacle_x = require_numeric_array(
            variables, obstacle_x_name, command, "obstacle_x",
        )
        obstacle_y = require_numeric_array(
            variables, obstacle_y_name, command, "obstacle_y",
        )
        if obstacle_x.size != obstacle_y.size:
            raise _cmd_error(
                command,
                "obstacle_x and obstacle_y must have the same length",
            )
        radius = resolve_scalar_or_array(command, tokens[7], "radius", variables)
        obstacle_radius = resolve_scalar_or_array(
            command, tokens[8], "obstacle_radius", variables,
        )
        for value, name, expected in (
            (radius, "radius", x.size),
            (obstacle_radius, "obstacle_radius", obstacle_x.size),
        ):
            if isinstance(value, PixilArray) and value.size != expected:
                raise _cmd_error(
                    command,
                    f"{name} array length {value.size} does not match expected length {expected}",
                )
        rest_tok = _optional_token(tokens, 9)
        hit_tok = _optional_token(tokens, 10)
        count_tok = _optional_token(tokens, 11)
        obstacle_count_tok = _optional_token(tokens, 12)
        response_tok = _optional_token(tokens, 13)
        restitution: Union[float, PixilArray] = 1.0
        if rest_tok is not None:
            restitution = resolve_particle_scalar_or_array(
                command, rest_tok, "restitution", variables, x.size,
            )
        hit = _optional_hit(command, hit_tok, variables, x.size)
        count = _optional_count(command, count_tok, variables, x.size)
        obstacles = _optional_count(
            command, obstacle_count_tok, variables, obstacle_x.size,
        )
        response = _parse_response(command, response_tok)
        return particle_collide_static_circles(
            x, y, vx, vy, active,
            obstacle_x, obstacle_y, radius, obstacle_radius,
            restitution=restitution, hit=hit, count=count,
            obstacle_count=obstacles, response=response,
        )

    if command == "particle_collide_circle_bounds":
        x, y, vx, vy, active = _state_arrays(command, tokens, variables)
        center_x = _eval_number(command, tokens[5], "center_x", variables)
        center_y = _eval_number(command, tokens[6], "center_y", variables)
        boundary_radius = _eval_number(
            command, tokens[7], "boundary_radius", variables,
        )
        rest_tok = _optional_token(tokens, 8)
        radius_tok = _optional_token(tokens, 9)
        angular_tok = _optional_token(tokens, 10)
        grip_tok = _optional_token(tokens, 11)
        hit_tok = _optional_token(tokens, 12)
        count_tok = _optional_token(tokens, 13)
        restitution: Union[float, PixilArray] = 1.0
        if rest_tok is not None:
            restitution = resolve_particle_scalar_or_array(
                command, rest_tok, "restitution", variables, x.size,
            )
        radius: Union[float, PixilArray] = 0.0
        if radius_tok is not None:
            radius = resolve_scalar_or_array(command, radius_tok, "radius", variables)
            if isinstance(radius, PixilArray) and radius.size != x.size:
                raise _cmd_error(
                    command,
                    f"radius array length {radius.size} does not match state length {x.size}",
                )
        angular_speed = 0.0 if angular_tok is None else _eval_number(
            command, angular_tok, "angular_speed", variables,
        )
        grip = 0.0 if grip_tok is None else _eval_number(
            command, grip_tok, "grip", variables,
        )
        hit = _optional_hit(command, hit_tok, variables, x.size)
        count = _optional_count(command, count_tok, variables, x.size)
        particle_collide_circle_bounds(
            x, y, vx, vy, active,
            center_x, center_y, boundary_radius,
            restitution=restitution, radius=radius,
            angular_speed=angular_speed, grip=grip,
            hit=hit, count=count,
        )
        return 0

    raise _cmd_error(command, "unknown particle command")


def run_particle_line(line: str, variables: Any) -> int:
    match = re.match(r"^(particle_\w+)\((.*)\)\s*$", line.strip())
    if not match or not is_particle_command(match.group(1)):
        raise ValueError(f"Not a particle command: {line}")
    command = match.group(1)
    tokens = split_command_parameters(match.group(2))
    return run_particle_command(command, tokens, variables)
