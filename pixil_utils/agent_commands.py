"""Pixil dispatch for generic agent_* kernels."""

from __future__ import annotations

import re
from typing import Any, List, Optional

from .agent_engine import agent_chemotaxis
from .parameter_types import split_command_parameters, validate_command_params
from .particle_commands import (
    _eval_number,
    _named_numeric_arrays,
    _optional_count,
    _optional_token,
    _require_same_lengths,
)

_COMMANDS = frozenset({"agent_chemotaxis"})


def is_agent_command(name: str) -> bool:
    return name in _COMMANDS


def run_agent_command(command: str, tokens: List[str], variables: Any) -> int:
    tokens = validate_command_params(command, ", ".join(tokens) if tokens else "")
    if command != "agent_chemotaxis":
        raise ValueError(f"{command}: unknown agent command")

    # agent_chemotaxis(x, y, heading, field, size,
    #                  [sensor_dist], [step], [deposit], [count], [wrap])
    if len(tokens) < 5:
        raise ValueError(
            "agent_chemotaxis: requires x, y, heading, field, size "
            f"(got {len(tokens)} args)"
        )

    arrays = _named_numeric_arrays(
        command,
        tokens,
        variables,
        [(0, "x"), (1, "y"), (2, "heading"), (3, "field")],
    )
    x, y, heading, field = arrays
    _require_same_lengths(command, ("x", "y", "heading"), [x, y, heading])

    size = int(_eval_number(command, tokens[4], "size", variables))
    sensor_tok = _optional_token(tokens, 5)
    step_tok = _optional_token(tokens, 6)
    deposit_tok = _optional_token(tokens, 7)
    count_tok = _optional_token(tokens, 8)
    wrap_tok = _optional_token(tokens, 9)

    sensor_dist = 5.0 if sensor_tok is None else _eval_number(
        command, sensor_tok, "sensor_dist", variables,
    )
    step = 1.0 if step_tok is None else _eval_number(
        command, step_tok, "step", variables,
    )
    deposit = 0.55 if deposit_tok is None else _eval_number(
        command, deposit_tok, "deposit", variables,
    )
    count = _optional_count(command, count_tok, variables, x.size)
    wrap = 1.0 if wrap_tok is None else _eval_number(
        command, wrap_tok, "wrap", variables,
    )

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
