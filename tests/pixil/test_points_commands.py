"""Validation and dispatch for points_project3d / array_lerp Pixil commands."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.parameter_types import validate_command_params
from pixil_utils.points_commands import run_points_command, run_points_line
from pixil_utils.variable_registry import VariableRegistry


def _arr(size, fill=0.0):
    a = PixilArray(size)
    for i in range(size):
        a[i] = fill
    return a


def _vars(n=2):
    variables = VariableRegistry()
    for name in (
        "v_x", "v_y", "v_z", "v_sx", "v_sy", "v_depth",
        "v_a", "v_b", "v_out",
    ):
        variables.set(name, _arr(n, 0.0))
    variables.set("v_t", 0.5)
    variables.set("v_count", n)
    return variables


def test_validate_points_requires_twelve_params():
    with pytest.raises(ValueError, match="at least 12"):
        validate_command_params("points_project3d", "v_x, v_y, v_z")


def test_validate_lerp_requires_four_params():
    with pytest.raises(ValueError, match="at least 4"):
        validate_command_params("array_lerp", "v_a, v_b, v_out")


def test_missing_array_name_is_clear():
    variables = _vars()
    with pytest.raises(ValueError, match="must be a numeric array name"):
        run_points_command(
            "array_lerp",
            ["10", "v_b", "v_out", "0.5"],
            variables,
        )


def test_length_mismatch_is_clear():
    variables = _vars()
    variables.set("v_b", _arr(4))
    with pytest.raises(ValueError, match="same length"):
        run_points_command(
            "array_lerp",
            ["v_a", "v_b", "v_out", "0.5"],
            variables,
        )


def test_count_exceeds_length_is_clear():
    variables = _vars(n=2)
    with pytest.raises(ValueError, match="exceeds array length"):
        run_points_command(
            "array_lerp",
            ["v_a", "v_b", "v_out", "0.5", "9"],
            variables,
        )


def test_array_lerp_line_mixes():
    variables = _vars(n=1)
    variables.get("v_a")[0] = 0
    variables.get("v_b")[0] = 10
    run_points_line("array_lerp(v_a, v_b, v_out, 0.25)", variables)
    assert variables.get("v_out")[0] == pytest.approx(2.5)


def test_points_project3d_line_writes_screen_and_depth():
    variables = _vars(n=1)
    variables.get("v_x")[0] = 1
    run_points_line(
        "points_project3d(v_x, v_y, v_z, v_sx, v_sy, 0, 0, 0, 10, 50, 32, 32, v_depth)",
        variables,
    )
    assert variables.get("v_sx")[0] == pytest.approx(42.0)
    assert variables.get("v_sy")[0] == pytest.approx(32.0)
    assert variables.get("v_depth")[0] == pytest.approx(0.0)


def test_points_project3d_count_without_depth():
    variables = _vars(n=2)
    variables.get("v_x")[0] = 1
    variables.get("v_x")[1] = 2
    run_points_line(
        "points_project3d(v_x, v_y, v_z, v_sx, v_sy, 0, 0, 0, 10, 50, 0, 0, 1)",
        variables,
    )
    assert variables.get("v_sx")[0] == pytest.approx(10.0)
    assert variables.get("v_sx")[1] == 0.0  # untouched beyond count


def test_points_project3d_depth_and_count():
    variables = _vars(n=2)
    variables.get("v_x")[0] = 1
    variables.get("v_x")[1] = 2
    run_points_line(
        "points_project3d(v_x, v_y, v_z, v_sx, v_sy, 0, 0, 0, 10, 50, 0, 0, v_depth, 1)",
        variables,
    )
    assert variables.get("v_sx")[0] == pytest.approx(10.0)
    assert variables.get("v_depth")[0] == pytest.approx(0.0)
    assert variables.get("v_sx")[1] == 0.0
