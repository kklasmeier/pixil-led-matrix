"""Generic particle kernels for Pixil (no show-specific rules).

These functions mutate caller-owned arrays in place. They do not draw, allocate
per-frame buffers, or know about pockets, cues, scoring, or colours.

Arrays may be PixilArray objects or plain Python lists of numbers.
A radius, mass, or acceleration argument may be a scalar or a per-particle
array of the same length as the state arrays.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Union

from .array_manager import PixilArray

NumericSeq = Union[PixilArray, Sequence[float], list]
ScalarOrSeq = Union[float, int, NumericSeq]


def _data(value: NumericSeq) -> list:
    if isinstance(value, PixilArray):
        return value.data
    return value  # type: ignore[return-value]


def _count(*arrays: NumericSeq, count: Optional[int] = None) -> int:
    lengths = [len(_data(a)) for a in arrays]
    n = min(lengths)
    if count is not None:
        n = min(n, int(count))
    return n


def _is_active(active: list, i: int) -> bool:
    return float(active[i]) != 0.0


def _component(value: ScalarOrSeq, i: int) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return float(_data(value)[i])


def _zero_hit(hit: Optional[NumericSeq], n: int) -> Optional[list]:
    if hit is None:
        return None
    data = _data(hit)
    for i in range(n):
        data[i] = 0.0
    return data


def _mark_hit(hit: Optional[list], i: int) -> None:
    if hit is not None:
        hit[i] = 1.0


def particle_integrate(
    x: NumericSeq,
    y: NumericSeq,
    vx: NumericSeq,
    vy: NumericSeq,
    active: NumericSeq,
    ax: ScalarOrSeq = 0.0,
    ay: ScalarOrSeq = 0.0,
    damping: float = 1.0,
    sleep_speed: float = 0.0,
    count: Optional[int] = None,
) -> None:
    """Advance active particles by one velocity-Verlet-free Euler step.

    For each active particle:
      vx += ax; vy += ay
      x += vx; y += vy
      vx *= damping; vy *= damping
      clamp |vx| / |vy| below sleep_speed to 0

    Inactive particles are left unchanged. Does not write a hit array.
    """
    xd, yd, vxd, vyd, ad = (
        _data(x),
        _data(y),
        _data(vx),
        _data(vy),
        _data(active),
    )
    n = _count(x, y, vx, vy, active, count=count)
    damp = float(damping)
    sleep = float(sleep_speed)

    for i in range(n):
        if not _is_active(ad, i):
            continue
        vxd[i] += _component(ax, i)
        vyd[i] += _component(ay, i)
        xd[i] += vxd[i]
        yd[i] += vyd[i]
        vxd[i] *= damp
        vyd[i] *= damp
        if abs(vxd[i]) < sleep:
            vxd[i] = 0.0
        if abs(vyd[i]) < sleep:
            vyd[i] = 0.0


def particle_collide_bounds(
    x: NumericSeq,
    y: NumericSeq,
    vx: NumericSeq,
    vy: NumericSeq,
    active: NumericSeq,
    left: float,
    right: float,
    top: float,
    bottom: float,
    restitution: float = 1.0,
    radius: ScalarOrSeq = 0.0,
    hit: Optional[NumericSeq] = None,
    count: Optional[int] = None,
) -> None:
    """Bounce active particle centres off a rectangle.

    ``radius`` (scalar or array) insets the bounds so the circle stays inside
    the rectangle. ``hit[i]`` is set to 1 if particle i hit any wall this call
    (the array is cleared first). Restitution is applied to the bounced axis.
    """
    xd, yd, vxd, vyd, ad = (
        _data(x),
        _data(y),
        _data(vx),
        _data(vy),
        _data(active),
    )
    n = _count(x, y, vx, vy, active, count=count)
    hit_data = _zero_hit(hit, n)
    bounce = float(restitution)
    left_b = float(left)
    right_b = float(right)
    top_b = float(top)
    bottom_b = float(bottom)

    for i in range(n):
        if not _is_active(ad, i):
            continue
        r = _component(radius, i)
        lo_x = left_b + r
        hi_x = right_b - r
        lo_y = top_b + r
        hi_y = bottom_b - r
        if hi_x < lo_x:
            lo_x = hi_x = 0.5 * (left_b + right_b)
        if hi_y < lo_y:
            lo_y = hi_y = 0.5 * (top_b + bottom_b)

        if xd[i] < lo_x:
            xd[i] = lo_x
            vxd[i] = abs(vxd[i]) * bounce
            _mark_hit(hit_data, i)
        elif xd[i] > hi_x:
            xd[i] = hi_x
            vxd[i] = -abs(vxd[i]) * bounce
            _mark_hit(hit_data, i)

        if yd[i] < lo_y:
            yd[i] = lo_y
            vyd[i] = abs(vyd[i]) * bounce
            _mark_hit(hit_data, i)
        elif yd[i] > hi_y:
            yd[i] = hi_y
            vyd[i] = -abs(vyd[i]) * bounce
            _mark_hit(hit_data, i)


def particle_collide_circles(
    x: NumericSeq,
    y: NumericSeq,
    vx: NumericSeq,
    vy: NumericSeq,
    active: NumericSeq,
    radius: ScalarOrSeq,
    mass: ScalarOrSeq = 1.0,
    restitution: float = 1.0,
    hit: Optional[NumericSeq] = None,
    count: Optional[int] = None,
) -> int:
    """Resolve overlapping active circles with equal- or unequal-mass impulses.

    Returns the number of overlapping pairs processed this call (including
    pairs already separating, which still get positional correction).
    ``hit[i]`` is cleared then set to 1 for any particle that overlapped.

    Two fully stationary overlapping particles are still separated so a
    packed rack does not remain stuck; impulse is skipped if relative
    velocity along the normal is not approaching.
    """
    xd, yd, vxd, vyd, ad = (
        _data(x),
        _data(y),
        _data(vx),
        _data(vy),
        _data(active),
    )
    n = _count(x, y, vx, vy, active, count=count)
    hit_data = _zero_hit(hit, n)
    bounce = float(restitution)
    pair_hits = 0

    for i in range(n - 1):
        if not _is_active(ad, i):
            continue
        ri = _component(radius, i)
        mi = _component(mass, i)
        if mi <= 0.0:
            continue
        speed_i = abs(vxd[i]) + abs(vyd[i])
        for j in range(i + 1, n):
            if not _is_active(ad, j):
                continue
            rj = _component(radius, j)
            mj = _component(mass, j)
            if mj <= 0.0:
                continue
            min_dist = ri + rj
            dx = xd[j] - xd[i]
            if abs(dx) >= min_dist:
                continue
            dy = yd[j] - yd[i]
            if abs(dy) >= min_dist:
                continue
            dist_sq = dx * dx + dy * dy
            if dist_sq >= min_dist * min_dist:
                continue

            pair_hits += 1
            _mark_hit(hit_data, i)
            _mark_hit(hit_data, j)

            if dist_sq <= 1e-12:
                nx, ny = 1.0, 0.0
                dist = 0.0
            else:
                dist = math.sqrt(dist_sq)
                nx = dx / dist
                ny = dy / dist

            overlap = min_dist - dist
            inv_i = 1.0 / mi
            inv_j = 1.0 / mj
            inv_sum = inv_i + inv_j
            if inv_sum <= 0.0:
                continue
            corr_i = overlap * (inv_i / inv_sum)
            corr_j = overlap * (inv_j / inv_sum)
            xd[i] -= nx * corr_i
            yd[i] -= ny * corr_i
            xd[j] += nx * corr_j
            yd[j] += ny * corr_j

            if speed_i + abs(vxd[j]) + abs(vyd[j]) == 0.0:
                continue
            relative = (vxd[j] - vxd[i]) * nx + (vyd[j] - vyd[i]) * ny
            if relative >= 0.0:
                continue
            impulse = -(1.0 + bounce) * relative / inv_sum
            vxd[i] -= (impulse * inv_i) * nx
            vyd[i] -= (impulse * inv_i) * ny
            vxd[j] += (impulse * inv_j) * nx
            vyd[j] += (impulse * inv_j) * ny

    return pair_hits
