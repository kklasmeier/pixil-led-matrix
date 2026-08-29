"""Validation errors and dispatch for particle_* Pixil commands."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.parameter_types import validate_command_params
from pixil_utils.particle_commands import run_particle_command, run_particle_line
from pixil_utils.variable_registry import VariableRegistry


def _arr(size, fill=0.0):
    a = PixilArray(size)
    for i in range(size):
        a[i] = fill
    return a


def _vars(n=2):
    variables = VariableRegistry()
    for name in ("v_x", "v_y", "v_vx", "v_vy", "v_active", "v_hit"):
        variables.set(name, _arr(n, 1.0 if name == "v_active" else 0.0))
    variables.set("v_left", 5)
    variables.set("v_right", 58)
    return variables


def test_validate_integrate_requires_five_arrays():
    with pytest.raises(ValueError, match="at least 5"):
        validate_command_params("particle_integrate", "v_x, v_y, v_vx")


def test_missing_array_name_is_clear():
    variables = _vars()
    with pytest.raises(ValueError, match="must be a numeric array name"):
        run_particle_command(
            "particle_integrate",
            ["10", "v_y", "v_vx", "v_vy", "v_active"],
            variables,
        )


def test_undefined_array_is_clear():
    variables = _vars()
    with pytest.raises(ValueError, match="is not defined"):
        run_particle_command(
            "particle_integrate",
            ["v_missing", "v_y", "v_vx", "v_vy", "v_active"],
            variables,
        )


def test_length_mismatch_is_clear():
    variables = _vars()
    variables.set("v_y", _arr(4))
    with pytest.raises(ValueError, match="same length"):
        run_particle_command(
            "particle_integrate",
            ["v_x", "v_y", "v_vx", "v_vy", "v_active"],
            variables,
        )


def test_count_exceeds_length_is_clear():
    variables = _vars(n=2)
    with pytest.raises(ValueError, match="exceeds array length"):
        run_particle_command(
            "particle_integrate",
            ["v_x", "v_y", "v_vx", "v_vy", "v_active", "0", "0", "1", "0", "9"],
            variables,
        )


def test_integrate_line_moves_particle():
    variables = _vars(n=1)
    variables.get("v_x")[0] = 10
    variables.get("v_vx")[0] = 2
    run_particle_line(
        "particle_integrate(v_x, v_y, v_vx, v_vy, v_active)",
        variables,
    )
    assert variables.get("v_x")[0] == 12


def test_collide_bounds_line_uses_variables_for_edges():
    variables = _vars(n=1)
    variables.set("v_radius", 0.0)
    variables.get("v_x")[0] = 0
    variables.get("v_vx")[0] = -1
    run_particle_line(
        "particle_collide_bounds(v_x, v_y, v_vx, v_vy, v_active, v_left, v_right, 5, 58, 1, v_radius, v_hit)",
        variables,
    )
    assert variables.get("v_x")[0] == 5
    assert variables.get("v_hit")[0] == 1
