"""Pixil dispatch and validation for generic particle kernels."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple, Union

from .array_manager import PixilArray
from .math_functions import evaluate_math_expression
from .parameter_types import split_command_parameters, validate_command_params
from .particle_engine import (
    particle_apply_attractors,
    particle_apply_springs,
    particle_collide_bounds,
    particle_collide_circle_bounds,
    particle_collide_circles,
    particle_collide_static_circles,
    particle_constrain_distances,
    particle_flock,
    particle_integrate,
    particle_verlet_integrate,
)

_ARRAY_NAME = re.compile(r"^v_\w+$")

_COMMANDS = frozenset({
    "particle_apply_attractors",
    "particle_apply_springs",
    "particle_integrate",
    "particle_verlet_integrate",
    "particle_constrain_distances",
    "particle_flock",
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


def _acceleration_state_arrays(
    command: str,
    tokens: List[str],
    variables: Any,
) -> Tuple[PixilArray, PixilArray, PixilArray, PixilArray, PixilArray]:
    names = [
        require_array_name(command, tokens[i], param)
        for i, param in enumerate(("x", "y", "ax", "ay", "active"))
    ]
    arrays = [
        require_numeric_array(variables, name, command, param)
        for name, param in zip(names, ("x", "y", "ax", "ay", "active"))
    ]
    lengths = {name: arr.size for name, arr in zip(names, arrays)}
    if len(set(lengths.values())) != 1:
        detail = ", ".join(f"{name}={size}" for name, size in lengths.items())
        raise _cmd_error(
            command,
            f"x, y, ax, ay, and active must have the same length ({detail})",
        )
    return arrays[0], arrays[1], arrays[2], arrays[3], arrays[4]


def _named_numeric_arrays(
    command: str,
    tokens: List[str],
    variables: Any,
    positions_and_names: List[Tuple[int, str]],
) -> List[PixilArray]:
    arrays = []
    for position, param in positions_and_names:
        name = require_array_name(command, tokens[position], param)
        arrays.append(require_numeric_array(variables, name, command, param))
    return arrays


def _require_same_lengths(
    command: str,
    names: Tuple[str, ...],
    arrays: List[PixilArray],
) -> None:
    lengths = {name: array.size for name, array in zip(names, arrays)}
    if len(set(lengths.values())) != 1:
        detail = ", ".join(f"{name}={size}" for name, size in lengths.items())
        raise _cmd_error(command, f"{', '.join(names)} must have the same length ({detail})")


def _optional_numeric_array(
    command: str,
    token: Optional[str],
    param: str,
    variables: Any,
    expected_size: int,
) -> Optional[PixilArray]:
    if token is None:
        return None
    name = require_array_name(command, token, param)
    array = require_numeric_array(variables, name, command, param)
    if array.size != expected_size:
        raise _cmd_error(
            command,
            f"{param} array length {array.size} does not match expected length "
            f"{expected_size}",
        )
    return array


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
    if command == "particle_flock":
        arrays = _named_numeric_arrays(
            command, tokens, variables,
            [
                (0, "x"), (1, "y"), (2, "vx"), (3, "vy"),
                (4, "ax"), (5, "ay"), (6, "active"),
            ],
        )
        _require_same_lengths(
            command, ("x", "y", "vx", "vy", "ax", "ay", "active"), arrays,
        )
        x, y, vx, vy, ax, ay, active = arrays
        separation_distance = _eval_number(
            command, tokens[7], "separation_distance", variables,
        )
        neighbor_distance = _eval_number(
            command, tokens[8], "neighbor_distance", variables,
        )
        defaults = (1.5, 1.0, 1.0, 2.5, 0.3, 0.0, 0.0)
        names = (
            "separation_weight", "alignment_weight", "cohesion_weight",
            "max_speed", "max_force", "wrap_width", "wrap_height",
        )
        values = []
        for offset, (default, name) in enumerate(zip(defaults, names), start=9):
            token = _optional_token(tokens, offset)
            values.append(
                default if token is None else _eval_number(
                    command, token, name, variables,
                )
            )
        count = _optional_count(
            command, _optional_token(tokens, 16), variables, x.size,
        )
        return particle_flock(
            x, y, vx, vy, ax, ay, active,
            separation_distance, neighbor_distance,
            separation_weight=values[0],
            alignment_weight=values[1],
            cohesion_weight=values[2],
            max_speed=values[3],
            max_force=values[4],
            wrap_width=values[5],
            wrap_height=values[6],
            count=count,
        )

    if command == "particle_verlet_integrate":
        arrays = _named_numeric_arrays(
            command, tokens, variables,
            [(0, "x"), (1, "y"), (2, "old_x"), (3, "old_y"), (4, "active")],
        )
        _require_same_lengths(
            command, ("x", "y", "old_x", "old_y", "active"), arrays,
        )
        x, y, old_x, old_y, active = arrays
        ax_tok = _optional_token(tokens, 5)
        ay_tok = _optional_token(tokens, 6)
        damping_tok = _optional_token(tokens, 7)
        count_tok = _optional_token(tokens, 8)
        ax: Union[float, PixilArray] = 0.0
        ay: Union[float, PixilArray] = 0.0
        if ax_tok is not None:
            ax = resolve_particle_scalar_or_array(
                command, ax_tok, "ax", variables, x.size,
            )
        if ay_tok is not None:
            ay = resolve_particle_scalar_or_array(
                command, ay_tok, "ay", variables, x.size,
            )
        damping = 1.0 if damping_tok is None else _eval_number(
            command, damping_tok, "damping", variables,
        )
        count = _optional_count(command, count_tok, variables, x.size)
        particle_verlet_integrate(
            x, y, old_x, old_y, active,
            ax=ax, ay=ay, damping=damping, count=count,
        )
        return 0

    if command == "particle_constrain_distances":
        point_arrays = _named_numeric_arrays(
            command, tokens, variables,
            [(0, "x"), (1, "y"), (2, "active")],
        )
        _require_same_lengths(command, ("x", "y", "active"), point_arrays)
        x, y, active = point_arrays
        link_arrays = _named_numeric_arrays(
            command, tokens, variables,
            [(3, "link_from"), (4, "link_to")],
        )
        _require_same_lengths(command, ("link_from", "link_to"), link_arrays)
        link_from, link_to = link_arrays
        rest_length = resolve_particle_scalar_or_array(
            command, tokens[5], "rest_length", variables, link_from.size,
        )
        stiffness_tok = _optional_token(tokens, 6)
        iterations_tok = _optional_token(tokens, 7)
        tension_tok = _optional_token(tokens, 8)
        count_tok = _optional_token(tokens, 9)
        link_count_tok = _optional_token(tokens, 10)
        min_distance_tok = _optional_token(tokens, 11)
        stiffness: Union[float, PixilArray] = 0.5
        if stiffness_tok is not None:
            stiffness = resolve_particle_scalar_or_array(
                command, stiffness_tok, "stiffness", variables, link_from.size,
            )
        iterations = 1 if iterations_tok is None else int(
            _eval_number(command, iterations_tok, "iterations", variables)
        )
        tension = _optional_numeric_array(
            command, tension_tok, "tension", variables, link_from.size,
        )
        count = _optional_count(command, count_tok, variables, x.size)
        link_count = _optional_count(
            command, link_count_tok, variables, link_from.size,
        )
        min_distance = 0.0 if min_distance_tok is None else _eval_number(
            command, min_distance_tok, "min_distance", variables,
        )
        return particle_constrain_distances(
            x, y, active, link_from, link_to, rest_length,
            stiffness=stiffness, iterations=iterations, tension=tension,
            count=count, link_count=link_count, min_distance=min_distance,
        )

    if command == "particle_apply_springs":
        point_arrays = _named_numeric_arrays(
            command, tokens, variables,
            [(0, "x"), (1, "y"), (2, "force_x"), (3, "force_y"), (4, "active")],
        )
        _require_same_lengths(
            command, ("x", "y", "force_x", "force_y", "active"), point_arrays,
        )
        x, y, force_x, force_y, active = point_arrays
        link_arrays = _named_numeric_arrays(
            command, tokens, variables,
            [(5, "link_from"), (6, "link_to")],
        )
        _require_same_lengths(command, ("link_from", "link_to"), link_arrays)
        link_from, link_to = link_arrays
        rest_length = resolve_particle_scalar_or_array(
            command, tokens[7], "rest_length", variables, link_from.size,
        )
        stiffness_tok = _optional_token(tokens, 8)
        tension_tok = _optional_token(tokens, 9)
        count_tok = _optional_token(tokens, 10)
        link_count_tok = _optional_token(tokens, 11)
        stiffness: Union[float, PixilArray] = 1.0
        if stiffness_tok is not None:
            stiffness = resolve_particle_scalar_or_array(
                command, stiffness_tok, "stiffness", variables, link_from.size,
            )
        tension = _optional_numeric_array(
            command, tension_tok, "tension", variables, link_from.size,
        )
        count = _optional_count(command, count_tok, variables, x.size)
        link_count = _optional_count(
            command, link_count_tok, variables, link_from.size,
        )
        return particle_apply_springs(
            x, y, force_x, force_y, active, link_from, link_to, rest_length,
            stiffness=stiffness, tension=tension,
            count=count, link_count=link_count,
        )

    if command == "particle_apply_attractors":
        x, y, ax, ay, active = _acceleration_state_arrays(command, tokens, variables)
        attractor_x_name = require_array_name(command, tokens[5], "attractor_x")
        attractor_y_name = require_array_name(command, tokens[6], "attractor_y")
        attractor_x = require_numeric_array(
            variables, attractor_x_name, command, "attractor_x",
        )
        attractor_y = require_numeric_array(
            variables, attractor_y_name, command, "attractor_y",
        )
        if attractor_x.size != attractor_y.size:
            raise _cmd_error(
                command,
                "attractor_x and attractor_y must have the same length",
            )
        strength_tok = _optional_token(tokens, 7)
        particle_strength_tok = _optional_token(tokens, 8)
        falloff_tok = _optional_token(tokens, 9)
        softening_tok = _optional_token(tokens, 10)
        max_acceleration_tok = _optional_token(tokens, 11)
        count_tok = _optional_token(tokens, 12)
        attractor_count_tok = _optional_token(tokens, 13)
        swirl_tok = _optional_token(tokens, 14)
        attractor_strength: Union[float, PixilArray] = 1.0
        if strength_tok is not None:
            attractor_strength = resolve_scalar_or_array(
                command, strength_tok, "attractor_strength", variables,
            )
            if (
                isinstance(attractor_strength, PixilArray)
                and attractor_strength.size != attractor_x.size
            ):
                raise _cmd_error(
                    command,
                    "attractor_strength array length "
                    f"{attractor_strength.size} does not match attractor length "
                    f"{attractor_x.size}",
                )
        particle_strength: Union[float, PixilArray] = 1.0
        if particle_strength_tok is not None:
            particle_strength = resolve_particle_scalar_or_array(
                command, particle_strength_tok, "particle_strength",
                variables, x.size,
            )
        falloff = 1.0 if falloff_tok is None else _eval_number(
            command, falloff_tok, "falloff", variables,
        )
        softening = 0.0 if softening_tok is None else _eval_number(
            command, softening_tok, "softening", variables,
        )
        max_acceleration: Optional[Union[float, PixilArray]] = None
        if max_acceleration_tok is not None:
            max_acceleration = resolve_particle_scalar_or_array(
                command, max_acceleration_tok, "max_acceleration",
                variables, x.size,
            )
        count = _optional_count(command, count_tok, variables, x.size)
        attractor_count = _optional_count(
            command, attractor_count_tok, variables, attractor_x.size,
        )
        swirl = 0.0 if swirl_tok is None else _eval_number(
            command, swirl_tok, "swirl", variables,
        )
        particle_apply_attractors(
            x, y, ax, ay, active, attractor_x, attractor_y,
            attractor_strength=attractor_strength,
            particle_strength=particle_strength,
            falloff=falloff,
            softening=softening,
            max_acceleration=max_acceleration,
            count=count,
            attractor_count=attractor_count,
            swirl=swirl,
        )
        return 0

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
        position_scale_tok = _optional_token(tokens, 12)
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
        position_scale = 1.0 if position_scale_tok is None else _eval_number(
            command, position_scale_tok, "position_scale", variables,
        )
        particle_integrate(
            x, y, vx, vy, active,
            ax=ax, ay=ay, damping=damping, sleep_speed=sleep_speed, count=count,
            integration_mode=integration_mode, max_speed=max_speed,
            position_scale=position_scale,
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
