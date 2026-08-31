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
    integration_mode: str = "post_move",
    max_speed: Optional[ScalarOrSeq] = None,
) -> None:
    """Advance active particles by one Euler step.

    ``integration_mode`` is ``"post_move"`` (default) or ``"pre_move"``.
    Post-move order:
      vx += ax; vy += ay
      x += vx; y += vy
      vx *= damping; vy *= damping
      clamp each velocity component to max_speed, if supplied

    Pre-move order:
      vx += ax; vy += ay
      vx *= damping; vy *= damping
      clamp each velocity component to max_speed, if supplied
      x += vx; y += vy

    In either mode, components below sleep_speed are set to 0 after moving.

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
    mode = str(integration_mode).strip().lower()
    if mode not in ("post_move", "pre_move"):
        raise ValueError(
            "particle_integrate: integration_mode must be "
            f"'post_move' or 'pre_move' (got {integration_mode!r})"
        )
    pre_move = mode == "pre_move"

    for i in range(n):
        if not _is_active(ad, i):
            continue
        vxd[i] += _component(ax, i)
        vyd[i] += _component(ay, i)
        if pre_move:
            vxd[i] *= damp
            vyd[i] *= damp
        else:
            xd[i] += vxd[i]
            yd[i] += vyd[i]
            vxd[i] *= damp
            vyd[i] *= damp
        if max_speed is not None:
            limit = _component(max_speed, i)
            if limit < 0.0:
                raise ValueError(
                    "particle_integrate: max_speed must be >= 0 "
                    f"(got {limit})"
                )
            vxd[i] = max(-limit, min(limit, vxd[i]))
            vyd[i] = max(-limit, min(limit, vyd[i]))
        if pre_move:
            xd[i] += vxd[i]
            yd[i] += vyd[i]
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
    restitution: ScalarOrSeq = 1.0,
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
    left_b = float(left)
    right_b = float(right)
    top_b = float(top)
    bottom_b = float(bottom)

    for i in range(n):
        if not _is_active(ad, i):
            continue
        bounce = _component(restitution, i)
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


def particle_collide_circle_bounds(
    x: NumericSeq,
    y: NumericSeq,
    vx: NumericSeq,
    vy: NumericSeq,
    active: NumericSeq,
    center_x: float,
    center_y: float,
    boundary_radius: float,
    restitution: ScalarOrSeq = 1.0,
    radius: ScalarOrSeq = 0.0,
    angular_speed: float = 0.0,
    grip: float = 0.0,
    hit: Optional[NumericSeq] = None,
    count: Optional[int] = None,
) -> None:
    """Keep active particles inside a circular, optionally rotating boundary.

    Particle centres are projected to ``boundary_radius - radius``. Outward
    normal velocity is reflected by ``restitution``. ``grip`` moves tangential
    velocity toward the wall velocity produced by signed ``angular_speed``.
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
    cx = float(center_x)
    cy = float(center_y)
    outer = max(0.0, float(boundary_radius))
    omega = float(angular_speed)
    wall_grip = float(grip)

    for i in range(n):
        if not _is_active(ad, i):
            continue
        bounce = _component(restitution, i)
        limit = max(0.0, outer - _component(radius, i))
        rx = xd[i] - cx
        ry = yd[i] - cy
        dist_sq = rx * rx + ry * ry
        if dist_sq <= limit * limit:
            continue

        if dist_sq <= 1e-12:
            nx, ny = 1.0, 0.0
        else:
            dist = math.sqrt(dist_sq)
            nx, ny = rx / dist, ry / dist

        xd[i] = cx + nx * limit
        yd[i] = cy + ny * limit

        normal_speed = vxd[i] * nx + vyd[i] * ny
        if normal_speed > 0.0:
            vxd[i] -= nx * normal_speed * (1.0 + bounce)
            vyd[i] -= ny * normal_speed * (1.0 + bounce)

        if wall_grip != 0.0 and omega != 0.0:
            tx, ty = -ny, nx
            tangent_speed = vxd[i] * tx + vyd[i] * ty
            tangent_delta = (omega * limit - tangent_speed) * wall_grip
            vxd[i] += tx * tangent_delta
            vyd[i] += ty * tangent_delta

        _mark_hit(hit_data, i)


def particle_collide_circles(
    x: NumericSeq,
    y: NumericSeq,
    vx: NumericSeq,
    vy: NumericSeq,
    active: NumericSeq,
    radius: ScalarOrSeq,
    mass: ScalarOrSeq = 1.0,
    restitution: ScalarOrSeq = 1.0,
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
            bounce = min(_component(restitution, i), _component(restitution, j))
            impulse = -(1.0 + bounce) * relative / inv_sum
            vxd[i] -= (impulse * inv_i) * nx
            vyd[i] -= (impulse * inv_i) * ny
            vxd[j] += (impulse * inv_j) * nx
            vyd[j] += (impulse * inv_j) * ny

    return pair_hits


def _static_circle_candidate_grid(
    obstacle_x: list,
    obstacle_y: list,
    obstacle_radius: ScalarOrSeq,
    obstacle_count: int,
    max_particle_radius: float,
) -> tuple[dict[tuple[int, int], list[int]], float, float]:
    """Build a transient uniform grid for generic static-circle queries."""
    max_obstacle_radius = max(
        (max(0.0, _component(obstacle_radius, j)) for j in range(obstacle_count)),
        default=0.0,
    )
    reach = max_particle_radius + max_obstacle_radius
    cell_size = max(1.0, reach)
    grid: dict[tuple[int, int], list[int]] = {}

    for j in range(obstacle_count):
        obstacle_r = max(0.0, _component(obstacle_radius, j))
        x0 = math.floor((float(obstacle_x[j]) - obstacle_r) / cell_size)
        x1 = math.floor((float(obstacle_x[j]) + obstacle_r) / cell_size)
        y0 = math.floor((float(obstacle_y[j]) - obstacle_r) / cell_size)
        y1 = math.floor((float(obstacle_y[j]) + obstacle_r) / cell_size)
        for cell_x in range(x0, x1 + 1):
            for cell_y in range(y0, y1 + 1):
                grid.setdefault((cell_x, cell_y), []).append(j)

    return grid, cell_size, max_obstacle_radius


def particle_collide_static_circles(
    x: NumericSeq,
    y: NumericSeq,
    vx: NumericSeq,
    vy: NumericSeq,
    active: NumericSeq,
    obstacle_x: NumericSeq,
    obstacle_y: NumericSeq,
    radius: ScalarOrSeq,
    obstacle_radius: ScalarOrSeq,
    restitution: ScalarOrSeq = 1.0,
    hit: Optional[NumericSeq] = None,
    count: Optional[int] = None,
    obstacle_count: Optional[int] = None,
    response: str = "impulse",
) -> int:
    """Bounce active particles off fixed circular obstacles.

    The obstacles have infinite mass and are never modified. Overlapping
    particles are projected to contact.

    ``response`` is ``"impulse"`` (default) or ``"reflect"``:
    - impulse: change velocity only while approaching; only the normal
      component is scaled by restitution (tangent is kept).
    - reflect: every overlap reflects the full velocity, then scales the
      whole vector by restitution.

    Returns the number of contacts resolved.
    """
    xd, yd, vxd, vyd, ad = (
        _data(x),
        _data(y),
        _data(vx),
        _data(vy),
        _data(active),
    )
    oxd, oyd = _data(obstacle_x), _data(obstacle_y)
    n = _count(x, y, vx, vy, active, count=count)
    obstacles = _count(obstacle_x, obstacle_y, count=obstacle_count)
    hit_data = _zero_hit(hit, n)
    contacts = 0
    mode = str(response).strip().lower()
    if mode not in ("impulse", "reflect"):
        raise ValueError(
            "particle_collide_static_circles: response must be "
            f"'impulse' or 'reflect' (got {response!r})"
        )
    full_reflect = mode == "reflect"
    max_particle_radius = max(
        (max(0.0, _component(radius, i)) for i in range(n)),
        default=0.0,
    )
    obstacle_grid, cell_size, max_obstacle_radius = _static_circle_candidate_grid(
        oxd, oyd, obstacle_radius, obstacles, max_particle_radius,
    )

    for i in range(n):
        if not _is_active(ad, i):
            continue
        bounce = _component(restitution, i)
        particle_r = _component(radius, i)
        reach = max(0.0, particle_r) + max_obstacle_radius
        # Positional correction can move the particle by up to ``reach``.
        # Include that possible destination so subsequent contacts retain
        # the original obstacle-index order within this call.
        query_reach = reach * 2.0
        x0 = math.floor((xd[i] - query_reach) / cell_size)
        x1 = math.floor((xd[i] + query_reach) / cell_size)
        y0 = math.floor((yd[i] - query_reach) / cell_size)
        y1 = math.floor((yd[i] + query_reach) / cell_size)
        candidate_indices = set()
        for cell_x in range(x0, x1 + 1):
            for cell_y in range(y0, y1 + 1):
                candidate_indices.update(obstacle_grid.get((cell_x, cell_y), ()))
        for j in sorted(candidate_indices):
            min_dist = particle_r + _component(obstacle_radius, j)
            dx = xd[i] - float(oxd[j])
            if abs(dx) >= min_dist:
                continue
            dy = yd[i] - float(oyd[j])
            if abs(dy) >= min_dist:
                continue
            dist_sq = dx * dx + dy * dy
            if dist_sq >= min_dist * min_dist:
                continue

            contacts += 1
            _mark_hit(hit_data, i)
            if dist_sq <= 1e-12:
                speed = math.hypot(vxd[i], vyd[i])
                if speed > 1e-12:
                    nx, ny = -vxd[i] / speed, -vyd[i] / speed
                else:
                    nx, ny = 1.0, 0.0
            else:
                dist = math.sqrt(dist_sq)
                nx, ny = dx / dist, dy / dist

            xd[i] = float(oxd[j]) + nx * min_dist
            yd[i] = float(oyd[j]) + ny * min_dist
            normal_speed = vxd[i] * nx + vyd[i] * ny
            if full_reflect:
                vxd[i] = (vxd[i] - 2.0 * normal_speed * nx) * bounce
                vyd[i] = (vyd[i] - 2.0 * normal_speed * ny) * bounce
            elif normal_speed < 0.0:
                vxd[i] -= nx * normal_speed * (1.0 + bounce)
                vyd[i] -= ny * normal_speed * (1.0 + bounce)

    return contacts
