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


def test_integrate_line_supports_pre_move_mode_and_component_cap():
    variables = _vars(n=1)
    variables.get("v_x")[0] = 10
    variables.get("v_vx")[0] = 3
    variables.get("v_vy")[0] = 1
    run_particle_line(
        "particle_integrate(v_x, v_y, v_vx, v_vy, v_active, 0, 2, 0.5, 0, 1, pre_move, 1.25)",
        variables,
    )

    assert variables.get("v_x")[0] == 11.25
    assert variables.get("v_y")[0] == 1.25
    assert variables.get("v_vx")[0] == 1.25
    assert variables.get("v_vy")[0] == 1.25


def test_integrate_line_supports_position_scale():
    variables = _vars(n=1)
    variables.get("v_x")[0] = 10
    variables.get("v_vx")[0] = 2
    run_particle_line(
        "particle_integrate(v_x, v_y, v_vx, v_vy, v_active, 0, 0, 1, 0, 1, post_move, 10, 0.5)",
        variables,
    )

    assert variables.get("v_x")[0] == 11
    assert variables.get("v_vx")[0] == 2


def test_integrate_line_rejects_unknown_mode():
    variables = _vars(n=1)
    with pytest.raises(ValueError, match="post_move' or 'pre_move"):
        run_particle_line(
            "particle_integrate(v_x, v_y, v_vx, v_vy, v_active, 0, 0, 1, 0, 1, legacy)",
            variables,
        )


def test_verlet_line_moves_points():
    variables = _vars(n=1)
    variables.set("v_old_x", _arr(1))
    variables.set("v_old_y", _arr(1))
    variables.get("v_x")[0] = 10
    variables.get("v_old_x")[0] = 9

    run_particle_line(
        "particle_verlet_integrate(v_x, v_y, v_old_x, v_old_y, v_active, 0, 0.5, 0.9, 1)",
        variables,
    )

    assert variables.get("v_x")[0] == pytest.approx(10.9)
    assert variables.get("v_y")[0] == pytest.approx(0.5)


def test_distance_constraint_line_moves_links():
    variables = _vars(n=2)
    variables.set("v_from", _arr(1))
    variables.set("v_to", _arr(1))
    variables.set("v_tension", _arr(1))
    variables.get("v_to")[0] = 1
    variables.get("v_x")[1] = 12

    result = run_particle_line(
        "particle_constrain_distances(v_x, v_y, v_active, v_from, v_to, 10, 0.5, 1, v_tension, 2, 1, 0)",
        variables,
    )

    assert result == 1
    assert variables.get("v_x")[0] == pytest.approx(1)
    assert variables.get("v_x")[1] == pytest.approx(11)
    assert variables.get("v_tension")[0] == pytest.approx(2)


def test_spring_force_line_accumulates_forces():
    variables = _vars(n=2)
    variables.set("v_fx", _arr(2))
    variables.set("v_fy", _arr(2))
    variables.set("v_from", _arr(1))
    variables.set("v_to", _arr(1))
    variables.set("v_tension", _arr(1))
    variables.get("v_to")[0] = 1
    variables.get("v_x")[1] = 12

    result = run_particle_line(
        "particle_apply_springs(v_x, v_y, v_fx, v_fy, v_active, v_from, v_to, 10, 0.5, v_tension, 2, 1)",
        variables,
    )

    assert result == 1
    assert variables.get("v_fx")[0] == pytest.approx(1)
    assert variables.get("v_fx")[1] == pytest.approx(-1)
    assert variables.get("v_tension")[0] == pytest.approx(1)


def test_flock_line_applies_separation():
    variables = _vars(n=2)
    variables.set("v_ax", _arr(2))
    variables.set("v_ay", _arr(2))
    variables.get("v_x")[1] = 1

    result = run_particle_line(
        "particle_flock(v_x, v_y, v_vx, v_vy, v_ax, v_ay, v_active, 5, 0, 1, 0, 0, 2, 10, 64, 64, 2)",
        variables,
    )

    assert result == 2
    assert variables.get("v_ax")[0] == pytest.approx(-2)
    assert variables.get("v_ax")[1] == pytest.approx(2)


def test_attractors_line_accumulates_force_and_accepts_array_strengths():
    variables = _vars(n=2)
    variables.set("v_ax", _arr(2))
    variables.set("v_ay", _arr(2))
    variables.set("v_well_x", _arr(2))
    variables.set("v_well_y", _arr(2))
    variables.set("v_well_strength", _arr(2))
    variables.set("v_charge", _arr(2))
    variables.get("v_well_x")[0] = 3
    variables.get("v_well_y")[0] = 4
    variables.get("v_well_strength")[0] = 10
    variables.get("v_charge")[0] = 1
    variables.get("v_charge")[1] = -1

    run_particle_line(
        "particle_apply_attractors(v_x, v_y, v_ax, v_ay, v_active, v_well_x, v_well_y, v_well_strength, v_charge, 1, 0, 10, 2, 1)",
        variables,
    )

    assert variables.get("v_ax")[0] == pytest.approx(1.2)
    assert variables.get("v_ay")[0] == pytest.approx(1.6)
    assert variables.get("v_ax")[1] == pytest.approx(-1.2)
    assert variables.get("v_ay")[1] == pytest.approx(-1.6)


def test_attractors_line_accepts_swirl():
    variables = _vars(n=1)
    variables.set("v_ax", _arr(1))
    variables.set("v_ay", _arr(1))
    variables.set("v_well_x", _arr(1))
    variables.set("v_well_y", _arr(1))
    variables.get("v_x")[0] = 42
    variables.get("v_y")[0] = 32
    variables.get("v_well_x")[0] = 32
    variables.get("v_well_y")[0] = 32

    run_particle_line(
        "particle_apply_attractors(v_x, v_y, v_ax, v_ay, v_active, v_well_x, v_well_y, 0.1, 1, -1, 0, 10, 1, 1, -3)",
        variables,
    )

    assert variables.get("v_ax")[0] == pytest.approx(-1.0)
    assert variables.get("v_ay")[0] == pytest.approx(3.0)


def test_attractors_line_rejects_wrong_sized_well_strength():
    variables = _vars(n=1)
    variables.set("v_ax", _arr(1))
    variables.set("v_ay", _arr(1))
    variables.set("v_well_x", _arr(2))
    variables.set("v_well_y", _arr(2))
    variables.set("v_well_strength", _arr(1))

    with pytest.raises(ValueError, match="does not match attractor length"):
        run_particle_line(
            "particle_apply_attractors(v_x, v_y, v_ax, v_ay, v_active, v_well_x, v_well_y, v_well_strength)",
            variables,
        )


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


def test_circle_bounds_line_projects_particle_and_marks_hit():
    variables = _vars(n=1)
    variables.set("v_radius", 1.0)
    variables.get("v_x")[0] = 12
    variables.get("v_vx")[0] = 2
    run_particle_line(
        "particle_collide_circle_bounds(v_x, v_y, v_vx, v_vy, v_active, 0, 0, 10, 0.5, v_radius, 0, 0, v_hit)",
        variables,
    )
    assert variables.get("v_x")[0] == 9
    assert variables.get("v_vx")[0] == -1
    assert variables.get("v_hit")[0] == 1


def test_static_circle_line_bounces_particle_and_marks_hit():
    variables = _vars(n=1)
    variables.set("v_peg_x", _arr(2))
    variables.set("v_peg_y", _arr(2))
    variables.get("v_peg_x")[0] = 10
    variables.get("v_peg_y")[0] = 10
    variables.get("v_x")[0] = 10.5
    variables.get("v_y")[0] = 10
    variables.get("v_vx")[0] = -1

    run_particle_line(
        "particle_collide_static_circles(v_x, v_y, v_vx, v_vy, v_active, v_peg_x, v_peg_y, 0.5, 1, 0.85, v_hit, 1, 1)",
        variables,
    )

    assert variables.get("v_x")[0] == 11.5
    assert variables.get("v_vx")[0] == pytest.approx(0.85)
    assert variables.get("v_hit")[0] == 1


def test_static_circle_line_reflect_response_scales_full_velocity():
    variables = _vars(n=1)
    variables.set("v_peg_x", _arr(2))
    variables.set("v_peg_y", _arr(2))
    variables.get("v_peg_x")[0] = 10
    variables.get("v_peg_y")[0] = 10
    variables.get("v_x")[0] = 10.5
    variables.get("v_y")[0] = 10
    variables.get("v_vx")[0] = -1
    variables.get("v_vy")[0] = 0.5

    run_particle_line(
        "particle_collide_static_circles(v_x, v_y, v_vx, v_vy, v_active, v_peg_x, v_peg_y, 0.5, 1, 0.82, v_hit, 1, 1, reflect)",
        variables,
    )

    assert variables.get("v_x")[0] == 11.5
    assert variables.get("v_vx")[0] == pytest.approx(0.82)
    assert variables.get("v_vy")[0] == pytest.approx(0.41)


def test_static_circle_line_rejects_unknown_response():
    variables = _vars(n=1)
    variables.set("v_peg_x", _arr(2))
    variables.set("v_peg_y", _arr(2))
    with pytest.raises(ValueError, match="impulse' or 'reflect"):
        run_particle_line(
            "particle_collide_static_circles(v_x, v_y, v_vx, v_vy, v_active, v_peg_x, v_peg_y, 0.5, 1, 0.82, v_hit, 1, 1, bounce)",
            variables,
        )


def test_static_circle_line_accepts_restitution_array():
    variables = _vars(n=2)
    variables.set("v_peg_x", _arr(2))
    variables.set("v_peg_y", _arr(2))
    variables.set("v_restitution", _arr(2))
    variables.get("v_peg_x")[0] = 10
    variables.get("v_peg_x")[1] = 20
    variables.get("v_peg_y")[0] = 10
    variables.get("v_peg_y")[1] = 20
    variables.get("v_x")[0] = 10.5
    variables.get("v_x")[1] = 20.5
    variables.get("v_y")[0] = 10
    variables.get("v_y")[1] = 20
    variables.get("v_vx")[0] = -1
    variables.get("v_vx")[1] = -1
    variables.get("v_restitution")[0] = 0.95
    variables.get("v_restitution")[1] = 0.35

    run_particle_line(
        "particle_collide_static_circles(v_x, v_y, v_vx, v_vy, v_active, v_peg_x, v_peg_y, 0.5, 1, v_restitution, v_hit, 2, 2)",
        variables,
    )

    assert variables.get("v_vx")[0] == pytest.approx(0.95)
    assert variables.get("v_vx")[1] == pytest.approx(0.35)
