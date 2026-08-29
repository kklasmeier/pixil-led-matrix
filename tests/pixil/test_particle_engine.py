"""Unit tests for generic particle kernels (no Pixil command wiring)."""

from pixil_utils.array_manager import PixilArray
from pixil_utils.particle_engine import (
    particle_collide_bounds,
    particle_collide_circles,
    particle_integrate,
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
