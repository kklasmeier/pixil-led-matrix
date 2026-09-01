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
    position_scale: float = 1.0,
) -> None:
    """Advance active particles by one Euler step.

    ``integration_mode`` is ``"post_move"`` (default) or ``"pre_move"``.
    Post-move order:
      vx += ax; vy += ay
      x += vx * position_scale; y += vy * position_scale
      vx *= damping; vy *= damping
      clamp each velocity component to max_speed, if supplied

    Pre-move order:
      vx += ax; vy += ay
      vx *= damping; vy *= damping
      clamp each velocity component to max_speed, if supplied
      x += vx * position_scale; y += vy * position_scale

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
    move_scale = float(position_scale)
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
            xd[i] += vxd[i] * move_scale
            yd[i] += vyd[i] * move_scale
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
            xd[i] += vxd[i] * move_scale
            yd[i] += vyd[i] * move_scale
        if abs(vxd[i]) < sleep:
            vxd[i] = 0.0
        if abs(vyd[i]) < sleep:
            vyd[i] = 0.0


def particle_apply_attractors(
    x: NumericSeq,
    y: NumericSeq,
    ax: NumericSeq,
    ay: NumericSeq,
    active: NumericSeq,
    attractor_x: NumericSeq,
    attractor_y: NumericSeq,
    attractor_strength: ScalarOrSeq = 1.0,
    particle_strength: ScalarOrSeq = 1.0,
    falloff: float = 1.0,
    softening: float = 0.0,
    max_acceleration: Optional[ScalarOrSeq] = None,
    count: Optional[int] = None,
    attractor_count: Optional[int] = None,
    swirl: float = 0.0,
) -> None:
    """Add the pull from fixed or moving attractors to particle acceleration.

    Positive strengths pull and negative strengths push away. The two strength
    inputs multiply, so a per-particle ``particle_strength`` supports charges
    or particle-specific response. ``falloff=-1`` is linear (spring-like),
    ``falloff=1`` is inverse-distance, and ``falloff=2`` is inverse-square.
    ``softening`` prevents extreme force near an attractor. ``swirl`` adds a
    sideways spin around each attractor (positive is counterclockwise).
    Existing acceleration is preserved so scripts may combine this with
    other forces.
    """
    xd, yd, axd, ayd, ad = (
        _data(x),
        _data(y),
        _data(ax),
        _data(ay),
        _data(active),
    )
    attractor_xd, attractor_yd = _data(attractor_x), _data(attractor_y)
    n = _count(x, y, ax, ay, active, count=count)
    attractors = _count(
        attractor_x, attractor_y, count=attractor_count,
    )
    exponent = float(falloff)
    if exponent < -1.0:
        raise ValueError(
            "particle_apply_attractors: falloff must be >= -1 "
            f"(got {falloff})"
        )
    softening_sq = float(softening) ** 2
    spin = float(swirl)

    for i in range(n):
        if not _is_active(ad, i):
            continue
        strength = _component(particle_strength, i)
        for j in range(attractors):
            dx = float(attractor_xd[j]) - xd[i]
            dy = float(attractor_yd[j]) - yd[i]
            dist_sq = dx * dx + dy * dy + softening_sq
            if dist_sq <= 1e-12:
                continue
            scale = strength * _component(attractor_strength, j)
            scale /= dist_sq ** ((exponent + 1.0) * 0.5)
            axd[i] += dx * scale
            ayd[i] += dy * scale
            if spin != 0.0:
                axd[i] += -dy * scale * spin
                ayd[i] += dx * scale * spin
        if max_acceleration is not None:
            limit = _component(max_acceleration, i)
            if limit < 0.0:
                raise ValueError(
                    "particle_apply_attractors: max_acceleration must be >= 0 "
                    f"(got {limit})"
                )
            magnitude_sq = axd[i] * axd[i] + ayd[i] * ayd[i]
            if magnitude_sq > limit * limit and magnitude_sq > 0.0:
                scale = limit / math.sqrt(magnitude_sq)
                axd[i] *= scale
                ayd[i] *= scale


def particle_verlet_integrate(
    x: NumericSeq,
    y: NumericSeq,
    old_x: NumericSeq,
    old_y: NumericSeq,
    active: NumericSeq,
    ax: ScalarOrSeq = 0.0,
    ay: ScalarOrSeq = 0.0,
    damping: float = 1.0,
    count: Optional[int] = None,
) -> None:
    """Move points using their current and previous positions.

    This is useful for cloth and ropes because links can correct positions
    directly without maintaining explicit velocity arrays.
    """
    xd, yd, old_xd, old_yd, ad = (
        _data(x),
        _data(y),
        _data(old_x),
        _data(old_y),
        _data(active),
    )
    n = _count(x, y, old_x, old_y, active, count=count)
    damp = float(damping)

    for i in range(n):
        if not _is_active(ad, i):
            continue
        current_x = xd[i]
        current_y = yd[i]
        velocity_x = (current_x - old_xd[i]) * damp
        velocity_y = (current_y - old_yd[i]) * damp
        old_xd[i] = current_x
        old_yd[i] = current_y
        xd[i] = current_x + velocity_x + _component(ax, i)
        yd[i] = current_y + velocity_y + _component(ay, i)


def _link_index(value: object, link: int, endpoint: str, point_count: int) -> int:
    numeric = float(value)
    index = int(numeric)
    if numeric != index or index < 0 or index >= point_count:
        raise ValueError(
            f"link {link} {endpoint} index must be an integer from 0 to "
            f"{point_count - 1} (got {value!r})"
        )
    return index


def particle_constrain_distances(
    x: NumericSeq,
    y: NumericSeq,
    active: NumericSeq,
    link_from: NumericSeq,
    link_to: NumericSeq,
    rest_length: ScalarOrSeq,
    stiffness: ScalarOrSeq = 0.5,
    iterations: int = 1,
    tension: Optional[NumericSeq] = None,
    count: Optional[int] = None,
    link_count: Optional[int] = None,
    min_distance: float = 0.0,
) -> int:
    """Move linked points toward their requested separation.

    ``active`` means movable here: inactive points act as fixed anchors.
    Each movable endpoint receives its normal share of the correction, so a
    link with one fixed endpoint remains intentionally softer than one where
    both endpoints move. Returns the number of link corrections performed.
    """
    xd, yd, ad = _data(x), _data(y), _data(active)
    from_data, to_data = _data(link_from), _data(link_to)
    n = _count(x, y, active, count=count)
    links = _count(link_from, link_to, count=link_count)
    tension_data = _data(tension) if tension is not None else None
    passes = int(iterations)
    minimum = float(min_distance)
    if passes < 0:
        raise ValueError(
            f"particle_constrain_distances: iterations must be >= 0 (got {iterations})"
        )
    if minimum < 0.0:
        raise ValueError(
            "particle_constrain_distances: min_distance must be >= 0 "
            f"(got {min_distance})"
        )
    corrections = 0

    if tension_data is not None:
        for link in range(links):
            tension_data[link] = 0.0

    for _ in range(passes):
        for link in range(links):
            i = _link_index(from_data[link], link, "from", n)
            j = _link_index(to_data[link], link, "to", n)
            movable_i = _is_active(ad, i)
            movable_j = _is_active(ad, j)
            if not movable_i and not movable_j:
                continue
            dx = xd[j] - xd[i]
            dy = yd[j] - yd[i]
            distance_sq = dx * dx + dy * dy
            if distance_sq <= minimum * minimum or distance_sq <= 1e-12:
                continue
            distance = math.sqrt(distance_sq)
            extension = distance - _component(rest_length, link)
            correction = extension / distance * _component(stiffness, link)
            move_x = dx * correction
            move_y = dy * correction
            if movable_i:
                xd[i] += move_x
                yd[i] += move_y
            if movable_j:
                xd[j] -= move_x
                yd[j] -= move_y
            if tension_data is not None:
                tension_data[link] = abs(extension)
            corrections += 1

    return corrections


def particle_apply_springs(
    x: NumericSeq,
    y: NumericSeq,
    force_x: NumericSeq,
    force_y: NumericSeq,
    active: NumericSeq,
    link_from: NumericSeq,
    link_to: NumericSeq,
    rest_length: ScalarOrSeq,
    stiffness: ScalarOrSeq = 1.0,
    tension: Optional[NumericSeq] = None,
    count: Optional[int] = None,
    link_count: Optional[int] = None,
) -> int:
    """Add Hooke-style spring forces for an arbitrary list of links.

    Existing force arrays are preserved so scripts can combine springs with
    gravity, wind, or attractors. Inactive endpoints act as fixed anchors.
    Returns the number of non-zero-length springs processed.
    """
    xd, yd, fxd, fyd, ad = (
        _data(x),
        _data(y),
        _data(force_x),
        _data(force_y),
        _data(active),
    )
    from_data, to_data = _data(link_from), _data(link_to)
    n = _count(x, y, force_x, force_y, active, count=count)
    links = _count(link_from, link_to, count=link_count)
    tension_data = _data(tension) if tension is not None else None
    processed = 0

    if tension_data is not None:
        for link in range(links):
            tension_data[link] = 0.0

    for link in range(links):
        i = _link_index(from_data[link], link, "from", n)
        j = _link_index(to_data[link], link, "to", n)
        active_i = _is_active(ad, i)
        active_j = _is_active(ad, j)
        if not active_i and not active_j:
            continue
        dx = xd[j] - xd[i]
        dy = yd[j] - yd[i]
        distance_sq = dx * dx + dy * dy
        if distance_sq <= 1e-12:
            continue
        distance = math.sqrt(distance_sq)
        spring_force = _component(stiffness, link) * (
            distance - _component(rest_length, link)
        )
        force_scale = spring_force / distance
        applied_x = dx * force_scale
        applied_y = dy * force_scale
        if active_i:
            fxd[i] += applied_x
            fyd[i] += applied_y
        if active_j:
            fxd[j] -= applied_x
            fyd[j] -= applied_y
        if tension_data is not None:
            tension_data[link] = abs(spring_force)
        processed += 1

    return processed


def _steering_vector(
    desired_x: float,
    desired_y: float,
    velocity_x: float,
    velocity_y: float,
    max_speed: float,
    max_force: float,
) -> tuple[float, float]:
    magnitude_sq = desired_x * desired_x + desired_y * desired_y
    if magnitude_sq <= 1e-12:
        return 0.0, 0.0
    scale = max_speed / math.sqrt(magnitude_sq)
    steer_x = desired_x * scale - velocity_x
    steer_y = desired_y * scale - velocity_y
    force_sq = steer_x * steer_x + steer_y * steer_y
    if force_sq > max_force * max_force and force_sq > 0.0:
        scale = max_force / math.sqrt(force_sq)
        steer_x *= scale
        steer_y *= scale
    return steer_x, steer_y


def particle_flock(
    x: NumericSeq,
    y: NumericSeq,
    vx: NumericSeq,
    vy: NumericSeq,
    ax: NumericSeq,
    ay: NumericSeq,
    active: NumericSeq,
    separation_distance: float,
    neighbor_distance: float,
    separation_weight: float = 1.5,
    alignment_weight: float = 1.0,
    cohesion_weight: float = 1.0,
    max_speed: float = 2.5,
    max_force: float = 0.3,
    wrap_width: float = 0.0,
    wrap_height: float = 0.0,
    count: Optional[int] = None,
) -> int:
    """Add separation, alignment, and cohesion steering to acceleration.

    Acceleration arrays are preserved so scripts can add wander, targets, or
    events before or after this call. Positive wrap dimensions use shortest
    toroidal distance; zero leaves that axis open. Returns directed neighbor
    visits, mainly for tests and diagnostics.
    """
    xd, yd, vxd, vyd, axd, ayd, ad = (
        _data(x),
        _data(y),
        _data(vx),
        _data(vy),
        _data(ax),
        _data(ay),
        _data(active),
    )
    n = _count(x, y, vx, vy, ax, ay, active, count=count)
    separation = float(separation_distance)
    neighborhood = float(neighbor_distance)
    speed_limit = float(max_speed)
    force_limit = float(max_force)
    width = float(wrap_width)
    height = float(wrap_height)
    if separation < 0.0 or neighborhood < 0.0:
        raise ValueError("particle_flock: distances must be >= 0")
    if speed_limit < 0.0 or force_limit < 0.0:
        raise ValueError("particle_flock: max_speed and max_force must be >= 0")
    if width < 0.0 or height < 0.0:
        raise ValueError("particle_flock: wrap dimensions must be >= 0")
    separation_sq = separation * separation
    neighborhood_sq = neighborhood * neighborhood
    visits = 0

    for i in range(n):
        if not _is_active(ad, i):
            continue
        sep_x = sep_y = 0.0
        align_x = align_y = 0.0
        cohesion_x = cohesion_y = 0.0
        sep_count = neighbor_count = 0

        for j in range(n):
            if i == j or not _is_active(ad, j):
                continue
            dx = xd[j] - xd[i]
            dy = yd[j] - yd[i]
            if width > 0.0 and abs(dx) > width * 0.5:
                dx -= math.copysign(width, dx)
            if height > 0.0 and abs(dy) > height * 0.5:
                dy -= math.copysign(height, dy)
            distance_sq = dx * dx + dy * dy
            if distance_sq <= 1e-12:
                continue
            inside_separation = distance_sq < separation_sq
            inside_neighborhood = distance_sq < neighborhood_sq
            if not inside_separation and not inside_neighborhood:
                continue
            visits += 1

            if inside_separation:
                inverse_distance = 1.0 / math.sqrt(distance_sq)
                sep_x -= dx * inverse_distance
                sep_y -= dy * inverse_distance
                sep_count += 1
            if inside_neighborhood:
                align_x += vxd[j]
                align_y += vyd[j]
                cohesion_x += dx
                cohesion_y += dy
                neighbor_count += 1

        total_x = total_y = 0.0
        if sep_count:
            steer_x, steer_y = _steering_vector(
                sep_x / sep_count,
                sep_y / sep_count,
                vxd[i],
                vyd[i],
                speed_limit,
                force_limit,
            )
            total_x += steer_x * float(separation_weight)
            total_y += steer_y * float(separation_weight)
        if neighbor_count:
            steer_x, steer_y = _steering_vector(
                align_x / neighbor_count,
                align_y / neighbor_count,
                vxd[i],
                vyd[i],
                speed_limit,
                force_limit,
            )
            total_x += steer_x * float(alignment_weight)
            total_y += steer_y * float(alignment_weight)
            steer_x, steer_y = _steering_vector(
                cohesion_x / neighbor_count,
                cohesion_y / neighbor_count,
                vxd[i],
                vyd[i],
                speed_limit,
                force_limit,
            )
            total_x += steer_x * float(cohesion_weight)
            total_y += steer_y * float(cohesion_weight)
        axd[i] += total_x
        ayd[i] += total_y

    return visits


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
