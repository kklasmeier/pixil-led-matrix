"""Legacy slime_step() wrapper around agent_chemotaxis."""

from __future__ import annotations

from typing import Any

from .agent_engine import agent_chemotaxis
from .particle_commands import require_numeric_array


def run_slime_step(variables: Any) -> None:
    """Call agent_chemotaxis with the fixed Slime_Mold array names."""
    x = require_numeric_array(variables, "v_x", "slime_step", "x")
    y = require_numeric_array(variables, "v_y", "slime_step", "y")
    heading = require_numeric_array(variables, "v_dir", "slime_step", "heading")
    field = require_numeric_array(variables, "v_phero", "slime_step", "field")

    def _scalar(name: str, default: float) -> float:
        try:
            return float(variables.get(name))
        except Exception:
            return default

    size = int(_scalar("v_size", 32))
    sensor_dist = _scalar("v_sensor_dist", 5.0)
    step = _scalar("v_step", 1.0)
    deposit = _scalar("v_deposit", 0.55)
    n = int(_scalar("v_n", x.size))

    agent_chemotaxis(
        x, y, heading, field, size,
        sensor_dist=sensor_dist,
        step=step,
        deposit=deposit,
        count=n,
        wrap=True,
    )
