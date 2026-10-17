"""Generic point / array kernels for Pixil (producer-side, no drawing).

These functions mutate caller-owned arrays. They do not draw, queue sprites,
or encode show-specific rules. Pixil owns morph timing, camera scalars, and
rendering.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Union

from .array_manager import PixilArray

NumericSeq = Union[PixilArray, Sequence[float], list]

# Minimum perspective denominator (camera - z'). Keeps projection stable when
# a point passes near or behind the camera plane.
_DEFAULT_Z_MIN = 1.0


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


def array_lerp(
    a: NumericSeq,
    b: NumericSeq,
    out: NumericSeq,
    t: float,
    count: Optional[int] = None,
) -> None:
    """Mix two numeric arrays: ``out[i] = a[i]*(1-t) + b[i]*t``.

    ``t`` is not clamped. ``out`` may alias ``a`` or ``b``. Optional ``count``
    limits processing to a leading prefix.
    """
    n = _count(a, b, out, count=count)
    ad = _data(a)
    bd = _data(b)
    od = _data(out)
    t = float(t)
    one_m = 1.0 - t
    for i in range(n):
        od[i] = float(ad[i]) * one_m + float(bd[i]) * t


def points_project3d(
    x: NumericSeq,
    y: NumericSeq,
    z: NumericSeq,
    sx: NumericSeq,
    sy: NumericSeq,
    ax: float,
    ay: float,
    az: float,
    scale: float,
    camera: float,
    cx: float,
    cy: float,
    depth: Optional[NumericSeq] = None,
    count: Optional[int] = None,
    z_min: float = _DEFAULT_Z_MIN,
) -> None:
    """Rotate world points (X then Y then Z) and perspective-project to screen.

    For each point:
      1. Rotate by ``ax``, ``ay``, ``az`` (radians), order Rx → Ry → Rz
      2. ``denom = max(camera - z', z_min)``
      3. ``ps = scale * camera / denom``
      4. ``sx = cx + x'*ps``, ``sy = cy + y'*ps``

    Optional ``depth`` receives post-rotate ``z'`` (before perspective), useful
    for cel / z_index choices in Pixil. Does not mutate input ``x,y,z``.
    """
    arrays = [x, y, z, sx, sy]
    if depth is not None:
        arrays.append(depth)
    n = _count(*arrays, count=count)

    xd = _data(x)
    yd = _data(y)
    zd = _data(z)
    sxd = _data(sx)
    syd = _data(sy)
    depth_d = _data(depth) if depth is not None else None

    ax = float(ax)
    ay = float(ay)
    az = float(az)
    scale = float(scale)
    camera = float(camera)
    cx = float(cx)
    cy = float(cy)
    z_min = float(z_min)
    if z_min <= 0.0:
        raise ValueError(f"points_project3d: z_min must be > 0 (got {z_min})")

    sxr = math.sin(ax)
    cxr = math.cos(ax)
    syr = math.sin(ay)
    cyr = math.cos(ay)
    szr = math.sin(az)
    czr = math.cos(az)

    for i in range(n):
        x0 = float(xd[i])
        y0 = float(yd[i])
        z0 = float(zd[i])

        # Rotate X
        y1 = y0 * cxr - z0 * sxr
        z1 = y0 * sxr + z0 * cxr
        # Rotate Y
        x2 = x0 * cyr + z1 * syr
        z2 = -x0 * syr + z1 * cyr
        # Rotate Z
        x3 = x2 * czr - y1 * szr
        y3 = x2 * szr + y1 * czr
        z3 = z2

        if depth_d is not None:
            depth_d[i] = z3

        denom = camera - z3
        if denom < z_min:
            denom = z_min
        ps = scale * camera / denom
        sxd[i] = cx + x3 * ps
        syd[i] = cy + y3 * ps
