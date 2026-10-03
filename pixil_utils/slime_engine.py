"""Backward-compatible slime_step() → agent_chemotaxis.

New scripts should call agent_chemotaxis(...) directly with explicit arrays.
"""

from __future__ import annotations

from typing import Any

from .agent_engine import agent_chemotaxis
from .array_manager import PixilArray
from .grid_expr import resolve_scalar


def _get_array(variables: Any, name: str) -> PixilArray:
    arr = variables.get(name) if hasattr(variables, "get") else variables[name]
    if not isinstance(arr, PixilArray):
        raise ValueError(f"{name} is not an array")
    return arr


def run_slime_step(variables: Any, append_draw=None) -> None:
    """Legacy fixed-name wrapper around agent_chemotaxis."""
    agent_chemotaxis(
        _get_array(variables, "v_x"),
        _get_array(variables, "v_y"),
        _get_array(variables, "v_dir"),
        _get_array(variables, "v_phero"),
        int(resolve_scalar("v_size", variables)),
        sensor_dist=float(resolve_scalar("v_sensor_dist", variables)),
        step=float(resolve_scalar("v_step", variables)),
        deposit=float(resolve_scalar("v_deposit", variables)),
        count=int(resolve_scalar("v_n", variables)),
        wrap=1,
    )
