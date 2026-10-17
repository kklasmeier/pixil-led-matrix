"""Unit tests for points_project3d and array_lerp kernels."""

import math

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.points_engine import array_lerp, points_project3d


def _arr(values):
    a = PixilArray(len(values))
    for i, val in enumerate(values):
        a[i] = val
    return a


def test_array_lerp_mixes_and_allows_alias_out():
    a = _arr([0.0, 10.0])
    b = _arr([10.0, 0.0])
    out = _arr([0.0, 0.0])

    array_lerp(a, b, out, 0.25)
    assert out[0] == pytest.approx(2.5)
    assert out[1] == pytest.approx(7.5)

    array_lerp(a, b, a, 0.5)
    assert a[0] == pytest.approx(5.0)
    assert a[1] == pytest.approx(5.0)


def test_array_lerp_respects_count_prefix():
    a = _arr([0.0, 0.0, 0.0])
    b = _arr([10.0, 10.0, 10.0])
    out = _arr([1.0, 1.0, 1.0])

    array_lerp(a, b, out, 1.0, count=2)
    assert out[0] == 10.0
    assert out[1] == 10.0
    assert out[2] == 1.0


def test_points_project3d_identity_at_origin():
    x = _arr([1.0])
    y = _arr([0.0])
    z = _arr([0.0])
    sx = _arr([0.0])
    sy = _arr([0.0])
    depth = _arr([0.0])

    points_project3d(
        x, y, z, sx, sy,
        ax=0.0, ay=0.0, az=0.0,
        scale=10.0, camera=50.0, cx=32.0, cy=32.0,
        depth=depth,
    )

    # ps = 10 * 50 / 50 = 10; sx = 32 + 1*10
    assert sx[0] == pytest.approx(42.0)
    assert sy[0] == pytest.approx(32.0)
    assert depth[0] == pytest.approx(0.0)


def test_points_project3d_rotation_x_moves_y_into_z():
    x = _arr([0.0])
    y = _arr([1.0])
    z = _arr([0.0])
    sx = _arr([0.0])
    sy = _arr([0.0])
    depth = _arr([0.0])

    points_project3d(
        x, y, z, sx, sy,
        ax=math.pi / 2, ay=0.0, az=0.0,
        scale=10.0, camera=50.0, cx=0.0, cy=0.0,
        depth=depth,
    )

    # Rx(90): (0,1,0) -> (0, 0, 1)
    assert depth[0] == pytest.approx(1.0, abs=1e-9)
    # denom = 50 - 1 = 49; ps = 500/49; sx = 0; sy = 0
    assert sx[0] == pytest.approx(0.0, abs=1e-9)
    assert sy[0] == pytest.approx(0.0, abs=1e-9)


def test_points_project3d_clamps_near_camera():
    x = _arr([1.0])
    y = _arr([0.0])
    z = _arr([100.0])  # camera - z would be negative
    sx = _arr([0.0])
    sy = _arr([0.0])

    points_project3d(
        x, y, z, sx, sy,
        ax=0.0, ay=0.0, az=0.0,
        scale=1.0, camera=50.0, cx=0.0, cy=0.0,
        z_min=2.0,
    )

    # denom clamped to 2; ps = 50/2 = 25
    assert sx[0] == pytest.approx(25.0)
    assert sy[0] == pytest.approx(0.0)


def test_points_project3d_rejects_non_positive_z_min():
    args = (_arr([0.0]), _arr([0.0]), _arr([0.0]), _arr([0.0]), _arr([0.0]))
    with pytest.raises(ValueError, match="z_min must be > 0"):
        points_project3d(*args, 0, 0, 0, 1, 50, 0, 0, z_min=0.0)
