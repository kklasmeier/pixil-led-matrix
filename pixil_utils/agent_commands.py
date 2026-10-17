"""Pixil dispatch for agent_* kernels."""

from __future__ import annotations

import re
from typing import Any, List

from .agent_engine import agent_chemotaxis
from .parameter_types import split_command_parameters, validate_command_params
from .particle_commands import (
    _eval_number,
    _optional_count,
    _optional_token,
    require_array_name,
    require_numeric_array,
)

_COMMANDS = frozenset({"agent_chemotaxis"})


def is_agent_command(name: str) -> bool:
    return name in _COMMANDS


def _cmd_error(command: str, message: str) -> ValueError:
    return ValueError(f"{command}: {message}")


def run_agent_command(command: str, tokens: List[str], variables: Any) -> int:
    tokens = validate_command_params(command, ", ".join(tokens) if tokens else "")

    if command != "agent_chemotaxis":
        raise _cmd_error(command, "unknown agent command")

    x_name = require_array_name(command, tokens[0], "x")
    y_name = require_array_name(command, tokens[1], "y")
    h_name = require_array_name(command, tokens[2], "heading")
    f_name = require_array_name(command, tokens[3], "field")
    x = require_numeric_array(variables, x_name, command, "x")
    y = require_numeric_array(variables, y_name, command, "y")
    heading = require_numeric_array(variables, h_name, command, "heading")
    field = require_numeric_array(variables, f_name, command, "field")

    if x.size != y.size or x.size != heading.size:
        raise _cmd_error(
            command,
            f"x/y/heading lengths must match "
            f"({x_name}={x.size}, {y_name}={y.size}, {h_name}={heading.size})",
        )

    size = int(_eval_number(command, tokens[4], "size", variables))
    if field.size < size * size:
        raise _cmd_error(
            command,
            f"field {f_name!r} length {field.size} < size*size ({size * size})",
        )

    sensor_dist = 5.0
    step = 1.0
    deposit = 0.55
    count = None
    wrap = True

    if _optional_token(tokens, 5) is not None:
        sensor_dist = _eval_number(command, tokens[5], "sensor_dist", variables)
    if _optional_token(tokens, 6) is not None:
        step = _eval_number(command, tokens[6], "step", variables)
    if _optional_token(tokens, 7) is not None:
        deposit = _eval_number(command, tokens[7], "deposit", variables)
    if _optional_token(tokens, 8) is not None:
        count = _optional_count(command, tokens[8], variables, x.size)
    if _optional_token(tokens, 9) is not None:
        wrap = _eval_number(command, tokens[9], "wrap", variables) != 0

    agent_chemotaxis(
        x, y, heading, field, size,
        sensor_dist=sensor_dist,
        step=step,
        deposit=deposit,
        count=count,
        wrap=wrap,
    )
    return 0


def run_agent_line(line: str, variables: Any) -> int:
    match = re.match(r"^(agent_\w+)\((.*)\)\s*$", line.strip())
    if not match or not is_agent_command(match.group(1)):
        raise ValueError(f"Not an agent command: {line}")
    command = match.group(1)
    tokens = split_command_parameters(match.group(2))
    return run_agent_command(command, tokens, variables)
