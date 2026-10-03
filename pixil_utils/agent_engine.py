"""Generic grid-following agent kernels for Pixil.

agent_chemotaxis: 8-way Physarum-style sense → turn → move → deposit.
Mutates position/heading arrays and the flat field array in place.
Does not draw and does not diffuse — pair with grid_program / grid_step.
"""

from __future__ import annotations

from typing import Optional, Union

import numpy as np

from .array_manager import PixilArray

# 8 compass steps (E, SE, S, SW, W, NW, N, NE)
_DX = np.array([1.0, 1.0, 0.0, -1.0, -1.0, -1.0, 0.0, 1.0], dtype=np.float64)
_DY = np.array([0.0, 1.0, 1.0, 1.0, 0.0, -1.0, -1.0, -1.0], dtype=np.float64)

NumericSeq = PixilArray


def agent_chemotaxis(
    x: NumericSeq,
    y: NumericSeq,
    heading: NumericSeq,
    field: NumericSeq,
    size: int,
    sensor_dist: float = 5.0,
    step: float = 1.0,
    deposit: float = 0.55,
    count: Optional[int] = None,
    wrap: Union[int, float] = 1,
) -> None:
    """Sense a flat grid field, steer 8-way headings, move, and deposit.

    ``heading[i]`` is an integer direction 0..7 (E, SE, S, SW, W, NW, N, NE).
    ``field`` is row-major length ``size * size``. Positive ``deposit`` adds
    scent at the landing cell; use 0 for pure followers. ``wrap`` non-zero
    uses toroidal edges; zero clamps agents and sensors to the field.
    """
    size_i = int(size)
    if size_i < 2:
        raise ValueError(f"agent_chemotaxis: size must be >= 2 (got {size})")
    expected = size_i * size_i
    if field.size != expected:
        raise ValueError(
            f"agent_chemotaxis: field length {field.size} != size*size ({expected})"
        )
    if x.size != y.size or x.size != heading.size:
        raise ValueError("agent_chemotaxis: x, y, heading must be the same length")
    if sensor_dist < 0 or step < 0:
        raise ValueError("agent_chemotaxis: sensor_dist and step must be >= 0")
    if deposit < 0:
        raise ValueError("agent_chemotaxis: deposit must be >= 0")

    n = x.size if count is None else int(count)
    if n < 0 or n > x.size:
        raise ValueError(f"agent_chemotaxis: count must be 0..{x.size} (got {n})")

    wrap_on = float(wrap) != 0.0
    max_c = size_i - 1
    phero = np.asarray(field.data, dtype=np.float64)
    xd = x.data
    yd = y.data
    hd = heading.data
    wrote = False

    for i in range(n):
        d = int(hd[i]) % 8
        cx = float(xd[i])
        cy = float(yd[i])
        left_d = (d - 1) % 8
        right_d = (d + 1) % 8

        # Forward / left / right sensors
        samples = []
        for sd in (d, left_d, right_d):
            sx = cx + _DX[sd] * sensor_dist
            sy = cy + _DY[sd] * sensor_dist
            if wrap_on:
                gx = int(np.floor(sx)) % size_i
                gy = int(np.floor(sy)) % size_i
            else:
                gx = int(np.floor(sx))
                gy = int(np.floor(sy))
                if gx < 0:
                    gx = 0
                elif gx > max_c:
                    gx = max_c
                if gy < 0:
                    gy = 0
                elif gy > max_c:
                    gy = max_c
            samples.append(float(phero[gy * size_i + gx]))

        fwd, left, right = samples
        if left > fwd and left >= right:
            d = left_d
        elif right > fwd:
            d = right_d

        cx = cx + _DX[d] * step
        cy = cy + _DY[d] * step

        if wrap_on:
            cx %= size_i
            cy %= size_i
            if cx < 0:
                cx += size_i
            if cy < 0:
                cy += size_i
        else:
            if cx < 0:
                cx = 0.0
            elif cx > max_c:
                cx = float(max_c)
            if cy < 0:
                cy = 0.0
            elif cy > max_c:
                cy = float(max_c)

        xd[i] = cx
        yd[i] = cy
        hd[i] = float(d)

        if deposit > 0:
            if wrap_on:
                gx = int(cx) % size_i
                gy = int(cy) % size_i
            else:
                gx = int(cx)
                gy = int(cy)
                if gx < 0:
                    gx = 0
                elif gx > max_c:
                    gx = max_c
                if gy < 0:
                    gy = 0
                elif gy > max_c:
                    gy = max_c
            idx = gy * size_i + gx
            val = phero[idx] + deposit
            phero[idx] = 1.5 if val > 1.5 else val
            wrote = True

    if wrote:
        field.data = phero.tolist()
