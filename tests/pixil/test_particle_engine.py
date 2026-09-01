"""Unit tests for generic particle kernels (no Pixil command wiring)."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.particle_engine import (
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


def _arr(values):
    a = PixilArray(len(values))
    for i, val in enumerate(values):
        a[i] = val
    return a


def test_integrate_moves_and_applies_acceleration_and_damping():
    x = _arr([10.0])
    y = _arr([10.0])
    vx = _arr([1.0])
    vy = _arr([0.0])
    active = _arr([1.0])

    particle_integrate(x, y, vx, vy, active, ax=0.0, ay=2.0, damping=0.5)

    assert x[0] == 11.0
    assert y[0] == 12.0
    assert vx[0] == 0.5
    assert vy[0] == 1.0


def test_integrate_pre_move_matches_damped_accelerated_step_with_component_cap():
    x = _arr([10.0])
    y = _arr([20.0])
    vx = _arr([3.0])
    vy = _arr([1.0])
    active = _arr([1.0])

    particle_integrate(
        x, y, vx, vy, active,
        ax=0.0, ay=2.0, damping=0.5,
        integration_mode="pre_move", max_speed=1.25,
    )

    assert vx[0] == 1.25
    assert vy[0] == 1.25
    assert x[0] == 11.25
    assert y[0] == 21.25


def test_integrate_scales_position_without_scaling_velocity():
    x = _arr([10.0])
    y = _arr([20.0])
    vx = _arr([2.0])
    vy = _arr([-4.0])
    active = _arr([1.0])

    particle_integrate(
        x, y, vx, vy, active,
        position_scale=0.5,
    )

    assert x[0] == 11.0
    assert y[0] == 18.0
    assert vx[0] == 2.0
    assert vy[0] == -4.0


def test_integrate_rejects_unknown_mode_and_negative_max_speed():
    args = (_arr([0.0]), _arr([0.0]), _arr([1.0]), _arr([0.0]), _arr([1.0]))

    with pytest.raises(ValueError, match="post_move' or 'pre_move"):
        particle_integrate(*args, integration_mode="legacy")
    with pytest.raises(ValueError, match="max_speed must be >= 0"):
        particle_integrate(*args, max_speed=-1)


def test_integrate_skips_inactive_and_sleeps_tiny_velocity():
    x = _arr([5.0, 5.0])
    y = _arr([5.0, 5.0])
    vx = _arr([0.01, 2.0])
    vy = _arr([0.01, 0.0])
    active = _arr([1.0, 0.0])

    particle_integrate(x, y, vx, vy, active, sleep_speed=0.05)

    assert vx[0] == 0.0
    assert vy[0] == 0.0
    assert x[0] == 5.01
    assert x[1] == 5.0
    assert vx[1] == 2.0


def test_attractors_add_pull_and_support_signed_particle_strength():
    x = _arr([0.0, 0.0])
    y = _arr([0.0, 0.0])
    ax = _arr([0.0, 0.0])
    ay = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])
    well_x = _arr([3.0])
    well_y = _arr([4.0])
    particle_strength = _arr([1.0, -1.0])

    particle_apply_attractors(
        x, y, ax, ay, active, well_x, well_y,
        attractor_strength=10.0, particle_strength=particle_strength,
        falloff=1.0,
    )

    assert ax[0] == pytest.approx(1.2)
    assert ay[0] == pytest.approx(1.6)
    assert ax[1] == pytest.approx(-1.2)
    assert ay[1] == pytest.approx(-1.6)


def test_attractors_soften_limit_and_skip_inactive_particles():
    x = _arr([0.0, 0.0])
    y = _arr([0.0, 0.0])
    ax = _arr([0.0, 5.0])
    ay = _arr([0.0, 0.0])
    active = _arr([1.0, 0.0])
    well_x = _arr([1.0])
    well_y = _arr([0.0])

    particle_apply_attractors(
        x, y, ax, ay, active, well_x, well_y,
        attractor_strength=100.0, softening=1.0, max_acceleration=2.0,
    )

    assert ax[0] == pytest.approx(2.0)
    assert ay[0] == pytest.approx(0.0)
    assert ax[1] == pytest.approx(5.0)


def test_attractors_swirl_adds_clockwise_spin_around_the_well():
    x = _arr([42.0])
    y = _arr([32.0])
    ax = _arr([0.0])
    ay = _arr([0.0])
    active = _arr([1.0])
    well_x = _arr([32.0])
    well_y = _arr([32.0])

    particle_apply_attractors(
        x, y, ax, ay, active, well_x, well_y,
        attractor_strength=0.1, falloff=-1, swirl=-3,
    )

    assert ax[0] == pytest.approx(-1.0)
    assert ay[0] == pytest.approx(3.0)


def test_attractors_support_linear_pull_and_reject_invalid_values():
    args = (
        _arr([0.0]), _arr([0.0]), _arr([0.0]), _arr([0.0]), _arr([1.0]),
        _arr([1.0]), _arr([0.0]),
    )

    particle_apply_attractors(*args, attractor_strength=0.25, falloff=-1)
    assert args[2][0] == pytest.approx(0.25)

    with pytest.raises(ValueError, match="falloff must be >= -1"):
        particle_apply_attractors(*args, falloff=-1.1)
    with pytest.raises(ValueError, match="max_acceleration must be >= 0"):
        particle_apply_attractors(*args, max_acceleration=-1)


def test_verlet_integrate_moves_free_points_and_preserves_pins():
    x = _arr([10.0, 20.0])
    y = _arr([10.0, 20.0])
    old_x = _arr([9.0, 18.0])
    old_y = _arr([10.0, 19.0])
    active = _arr([1.0, 0.0])

    particle_verlet_integrate(
        x, y, old_x, old_y, active, ay=0.5, damping=0.9,
    )

    assert x[0] == pytest.approx(10.9)
    assert y[0] == pytest.approx(10.5)
    assert old_x[0] == 10.0
    assert old_y[0] == 10.0
    assert x[1] == 20.0
    assert old_x[1] == 18.0


def test_distance_constraints_move_linked_points_and_respect_fixed_anchor():
    x = _arr([0.0, 12.0, 30.0])
    y = _arr([0.0, 0.0, 0.0])
    active = _arr([0.0, 1.0, 1.0])
    link_from = _arr([0.0, 1.0])
    link_to = _arr([1.0, 2.0])
    tension = _arr([0.0, 0.0])

    corrections = particle_constrain_distances(
        x, y, active, link_from, link_to,
        rest_length=10.0, stiffness=0.5, iterations=1, tension=tension,
    )

    assert corrections == 2
    assert x[0] == 0.0
    assert x[1] == pytest.approx(15.5)
    assert x[2] == pytest.approx(25.5)
    assert tension[0] == pytest.approx(2.0)
    assert tension[1] == pytest.approx(9.0)


def test_distance_constraints_reject_invalid_link_index():
    with pytest.raises(ValueError, match="link 0 to index"):
        particle_constrain_distances(
            _arr([0.0]), _arr([0.0]), _arr([1.0]),
            _arr([0.0]), _arr([1.0]), rest_length=1.0,
        )


def test_spring_forces_accumulate_and_report_tension():
    x = _arr([0.0, 12.0])
    y = _arr([0.0, 0.0])
    force_x = _arr([1.0, 0.0])
    force_y = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])
    link_from = _arr([0.0])
    link_to = _arr([1.0])
    tension = _arr([0.0])

    processed = particle_apply_springs(
        x, y, force_x, force_y, active, link_from, link_to,
        rest_length=10.0, stiffness=0.5, tension=tension,
    )

    assert processed == 1
    assert force_x[0] == pytest.approx(2.0)
    assert force_x[1] == pytest.approx(-1.0)
    assert tension[0] == pytest.approx(1.0)


def test_flock_applies_separation_steering():
    x = _arr([0.0, 1.0])
    y = _arr([0.0, 0.0])
    vx = _arr([0.0, 0.0])
    vy = _arr([0.0, 0.0])
    ax = _arr([0.0, 0.0])
    ay = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])

    visits = particle_flock(
        x, y, vx, vy, ax, ay, active,
        separation_distance=5, neighbor_distance=0,
        separation_weight=1, alignment_weight=0, cohesion_weight=0,
        max_speed=2, max_force=10,
    )

    assert visits == 2
    assert ax[0] == pytest.approx(-2)
    assert ax[1] == pytest.approx(2)


def test_flock_uses_shortest_wraparound_direction_for_cohesion():
    x = _arr([1.0, 63.0])
    y = _arr([10.0, 10.0])
    vx = _arr([0.0, 0.0])
    vy = _arr([0.0, 0.0])
    ax = _arr([0.0, 0.0])
    ay = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])

    particle_flock(
        x, y, vx, vy, ax, ay, active,
        separation_distance=0, neighbor_distance=5,
        separation_weight=0, alignment_weight=0, cohesion_weight=1,
        max_speed=2, max_force=10, wrap_width=64, wrap_height=64,
    )

    assert ax[0] == pytest.approx(-2)
    assert ax[1] == pytest.approx(2)


def test_flock_rejects_negative_limits():
    args = (
        _arr([0.0]), _arr([0.0]), _arr([0.0]), _arr([0.0]),
        _arr([0.0]), _arr([0.0]), _arr([1.0]),
    )
    with pytest.raises(ValueError, match="distances must be >= 0"):
        particle_flock(*args, separation_distance=-1, neighbor_distance=5)
    with pytest.raises(ValueError, match="wrap dimensions must be >= 0"):
        particle_flock(
            *args, separation_distance=1, neighbor_distance=5, wrap_width=-1,
        )


def test_bounds_bounce_and_marks_hit():
    x = _arr([0.0, 50.0])
    y = _arr([10.0, 10.0])
    vx = _arr([-3.0, 0.0])
    vy = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])
    hit = _arr([1.0, 1.0])

    particle_collide_bounds(
        x, y, vx, vy, active,
        left=5, right=58, top=5, bottom=58,
        restitution=0.5, radius=0.0, hit=hit,
    )

    assert x[0] == 5.0
    assert vx[0] > 0
    assert hit[0] == 1.0
    assert hit[1] == 0.0


def test_bounds_respects_radius_inset():
    x = _arr([5.0])
    y = _arr([32.0])
    vx = _arr([-1.0])
    vy = _arr([0.0])
    active = _arr([1.0])

    particle_collide_bounds(
        x, y, vx, vy, active,
        left=5, right=58, top=5, bottom=58,
        restitution=1.0, radius=1.65,
    )

    assert x[0] == 6.65
    assert vx[0] > 0


def test_bounds_accepts_per_particle_restitution():
    x = _arr([0.0, 0.0])
    y = _arr([10.0, 20.0])
    vx = _arr([-2.0, -2.0])
    vy = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])
    restitution = _arr([0.9, 0.4])

    particle_collide_bounds(
        x, y, vx, vy, active,
        left=5, right=58, top=5, bottom=58,
        restitution=restitution,
    )

    assert vx[0] == pytest.approx(1.8)
    assert vx[1] == pytest.approx(0.8)


def test_circle_bounds_projects_and_bounces_outward_particle():
    x = _arr([12.0])
    y = _arr([0.0])
    vx = _arr([2.0])
    vy = _arr([0.0])
    active = _arr([1.0])
    hit = _arr([0.0])

    particle_collide_circle_bounds(
        x, y, vx, vy, active,
        center_x=0, center_y=0, boundary_radius=10,
        restitution=0.5, radius=1, hit=hit,
    )

    assert x[0] == 9.0
    assert y[0] == 0.0
    assert vx[0] == -1.0
    assert hit[0] == 1.0


def test_rotating_circle_bounds_applies_tangential_grip():
    x = _arr([10.0])
    y = _arr([0.0])
    vx = _arr([0.0])
    vy = _arr([0.0])
    active = _arr([1.0])

    particle_collide_circle_bounds(
        x, y, vx, vy, active,
        center_x=0, center_y=0, boundary_radius=9,
        angular_speed=0.1, grip=0.5,
    )

    assert x[0] == 9.0
    assert vy[0] == 0.45


def test_circle_collision_transfers_equal_mass_velocity():
    x = _arr([20.0, 22.5])
    y = _arr([30.0, 30.0])
    vx = _arr([1.0, 0.0])
    vy = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])
    hit = _arr([0.0, 0.0])

    pairs = particle_collide_circles(
        x, y, vx, vy, active,
        radius=1.65, mass=1.0, restitution=1.0, hit=hit,
    )

    assert pairs == 1
    assert vx[0] < 0.1
    assert vx[1] > 0.9
    assert hit[0] == 1.0
    assert hit[1] == 1.0


def test_circle_collision_skips_inactive_and_distant_pairs():
    x = _arr([10.0, 40.0, 10.0])
    y = _arr([10.0, 40.0, 10.0])
    vx = _arr([1.0, 0.0, 0.0])
    vy = _arr([0.0, 0.0, 0.0])
    active = _arr([1.0, 1.0, 0.0])
    hit = _arr([1.0, 1.0, 1.0])

    pairs = particle_collide_circles(
        x, y, vx, vy, active, radius=1.65, hit=hit,
    )

    assert pairs == 0
    assert hit[0] == 0.0
    assert hit[1] == 0.0
    assert hit[2] == 0.0
    assert vx[0] == 1.0


def test_heavier_particle_moves_less_on_impact():
    x = _arr([20.0, 23.2])
    y = _arr([30.0, 30.0])
    vx = _arr([1.0, 0.0])
    vy = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])
    mass = _arr([1.0, 10.0])

    particle_collide_circles(
        x, y, vx, vy, active, radius=1.65, mass=mass, restitution=1.0,
    )

    assert abs(vx[1]) < abs(vx[0])


def test_circle_collision_uses_lower_material_restitution():
    x = _arr([20.0, 22.5])
    y = _arr([30.0, 30.0])
    vx = _arr([1.0, -1.0])
    vy = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])
    restitution = _arr([0.95, 0.4])

    particle_collide_circles(
        x, y, vx, vy, active,
        radius=1.65, mass=1.0, restitution=restitution,
    )

    assert vx[0] == pytest.approx(-0.4)
    assert vx[1] == pytest.approx(0.4)


def test_static_circle_projects_and_bounces_particle():
    x = _arr([10.5])
    y = _arr([10.0])
    vx = _arr([-1.0])
    vy = _arr([0.0])
    active = _arr([1.0])
    peg_x = _arr([10.0])
    peg_y = _arr([10.0])
    hit = _arr([0.0])

    contacts = particle_collide_static_circles(
        x, y, vx, vy, active, peg_x, peg_y,
        radius=0.5, obstacle_radius=1.0, restitution=0.85, hit=hit,
    )

    assert contacts == 1
    assert x[0] == 11.5
    assert vx[0] == pytest.approx(0.85)
    assert hit[0] == 1.0


def test_static_circle_reflect_response_scales_full_velocity():
    x = _arr([10.5])
    y = _arr([10.0])
    vx = _arr([-1.0])
    vy = _arr([0.5])
    active = _arr([1.0])
    peg_x = _arr([10.0])
    peg_y = _arr([10.0])

    particle_collide_static_circles(
        x, y, vx, vy, active, peg_x, peg_y,
        radius=0.5, obstacle_radius=1.0, restitution=0.82,
        response="reflect",
    )

    assert x[0] == 11.5
    assert vx[0] == pytest.approx(0.82)
    assert vy[0] == pytest.approx(0.41)


def test_static_circle_rejects_unknown_response():
    x = _arr([10.5])
    y = _arr([10.0])
    vx = _arr([-1.0])
    vy = _arr([0.0])
    active = _arr([1.0])
    peg_x = _arr([10.0])
    peg_y = _arr([10.0])

    with pytest.raises(ValueError, match="impulse' or 'reflect"):
        particle_collide_static_circles(
            x, y, vx, vy, active, peg_x, peg_y,
            radius=0.5, obstacle_radius=1.0, response="galton",
        )


def test_static_circle_accepts_per_particle_restitution():
    x = _arr([10.5, 20.5])
    y = _arr([10.0, 20.0])
    vx = _arr([-1.0, -1.0])
    vy = _arr([0.0, 0.0])
    active = _arr([1.0, 1.0])
    peg_x = _arr([10.0, 20.0])
    peg_y = _arr([10.0, 20.0])
    restitution = _arr([0.95, 0.35])

    particle_collide_static_circles(
        x, y, vx, vy, active, peg_x, peg_y,
        radius=0.5, obstacle_radius=1.0,
        restitution=restitution,
    )

    assert vx[0] == pytest.approx(0.95)
    assert vx[1] == pytest.approx(0.35)


def test_static_circle_handles_large_sparse_obstacle_pool_with_array_radii():
    x = _arr([50.5])
    y = _arr([50.0])
    vx = _arr([-1.0])
    vy = _arr([0.0])
    active = _arr([1.0])
    peg_x = _arr([float(i * 10) for i in range(100)])
    peg_y = _arr([200.0] * 100)
    peg_radius = _arr([0.25] * 100)
    peg_x[73] = 50.0
    peg_y[73] = 50.0
    peg_radius[73] = 1.0

    contacts = particle_collide_static_circles(
        x, y, vx, vy, active, peg_x, peg_y,
        radius=0.5, obstacle_radius=peg_radius, restitution=0.8,
    )

    assert contacts == 1
    assert x[0] == pytest.approx(51.5)
    assert vx[0] == pytest.approx(0.8)


def test_static_circle_respects_active_and_obstacle_count():
    x = _arr([10.5, 20.5])
    y = _arr([10.0, 20.0])
    vx = _arr([-1.0, -1.0])
    vy = _arr([0.0, 0.0])
    active = _arr([0.0, 1.0])
    peg_x = _arr([10.0, 20.0])
    peg_y = _arr([10.0, 20.0])
    hit = _arr([1.0, 1.0])

    contacts = particle_collide_static_circles(
        x, y, vx, vy, active, peg_x, peg_y,
        radius=0.5, obstacle_radius=1.0, hit=hit, obstacle_count=1,
    )

    assert contacts == 0
    assert hit[0] == 0.0
    assert hit[1] == 0.0
