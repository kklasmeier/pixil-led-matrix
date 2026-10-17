"""Producer-side agent kernels (chemotaxis / trail followers).

Mutate caller-owned arrays and field buffers. Do not draw.
"""

from __future__ import annotations

from typing import Optional, Sequence, Union

import numpy as np

from .array_manager import PixilArray

NumericSeq = Union[PixilArray, Sequence[float], list]

# 8-way: 0=E 1=SE 2=S 3=SW 4=W 5=NW 6=N 7=NE
_DX = np.array([1.0, 1.0, 0.0, -1.0, -1.0, -1.0, 0.0, 1.0], dtype=np.float64)
_DY = np.array([0.0, 1.0, 1.0, 1.0, 0.0, -1.0, -1.0, -1.0], dtype=np.float64)

_DEFAULT_SENSOR = 5.0
_DEFAULT_STEP = 1.0
_DEFAULT_DEPOSIT = 0.55
_FIELD_CAP = 1.5


def _data(value: NumericSeq) -> list:
    if isinstance(value, PixilArray):
        return value.data
    return value  # type: ignore[return-value]


def _count(*arrays: NumericSeq, count: Optional[int] = None) -> int:
    n = min(len(_data(a)) for a in arrays)
    if count is not None:
        n = min(n, int(count))
    return n


def agent_chemotaxis(
    x: NumericSeq,
    y: NumericSeq,
    heading: NumericSeq,
    field: NumericSeq,
    size: int,
    sensor_dist: float = _DEFAULT_SENSOR,
    step: float = _DEFAULT_STEP,
    deposit: float = _DEFAULT_DEPOSIT,
    count: Optional[int] = None,
    wrap: bool = True,
) -> None:
    """Sense a scent field, turn toward the strongest sample, step, deposit.

    ``heading`` uses 8-way codes 0..7 (E, SE, S, SW, W, NW, N, NE).
    ``field`` is a flat row-major ``size*size`` pheromone buffer. Deposits are
    capped at 1.5 so grid evaporation can keep trails bounded.
    """
    size = int(size)
    if size < 2:
        raise ValueError(f"agent_chemotaxis: size must be >= 2 (got {size})")

    n = _count(x, y, heading, count=count)
    if n <= 0:
        return

    fd = _data(field)
    if len(fd) < size * size:
        raise ValueError(
            f"agent_chemotaxis: field length {len(fd)} < size*size ({size * size})"
        )

    xd = _data(x)
    yd = _data(y)
    hd = _data(heading)

    xa = np.asarray(xd[:n], dtype=np.float64)
    ya = np.asarray(yd[:n], dtype=np.float64)
    h = np.floor(np.asarray(hd[:n], dtype=np.float64)).astype(np.int64) % 8

    grid = np.asarray(fd[: size * size], dtype=np.float64).reshape(size, size)

    sensor_dist = float(sensor_dist)
    step = float(step)
    deposit = float(deposit)

    def _sample(dirs: np.ndarray) -> np.ndarray:
        sx = xa + _DX[dirs] * sensor_dist
        sy = ya + _DY[dirs] * sensor_dist
        if wrap:
            ix = np.floor(sx).astype(np.int64) % size
            iy = np.floor(sy).astype(np.int64) % size
        else:
            ix = np.clip(np.floor(sx).astype(np.int64), 0, size - 1)
            iy = np.clip(np.floor(sy).astype(np.int64), 0, size - 1)
        return grid[iy, ix]

    hl = (h - 1) % 8
    hr = (h + 1) % 8
    fl = _sample(hl)
    fa = _sample(h)
    fr = _sample(hr)

    # Prefer ahead on ties; otherwise turn toward the stronger side.
    turn = np.zeros(n, dtype=np.int64)
    best = fa.copy()
    left_wins = fl > best
    turn = np.where(left_wins, -1, turn)
    best = np.where(left_wins, fl, best)
    right_wins = fr > best
    turn = np.where(right_wins, 1, turn)

    h = (h + turn) % 8
    xa = xa + _DX[h] * step
    ya = ya + _DY[h] * step

    if wrap:
        xa = np.mod(xa, size)
        ya = np.mod(ya, size)
    else:
        xa = np.clip(xa, 0.0, size - 1.0000001)
        ya = np.clip(ya, 0.0, size - 1.0000001)

    for i in range(n):
        xd[i] = float(xa[i])
        yd[i] = float(ya[i])
        hd[i] = float(h[i])

    if deposit != 0.0:
        if wrap:
            ix = np.floor(xa).astype(np.int64) % size
            iy = np.floor(ya).astype(np.int64) % size
        else:
            ix = np.clip(np.floor(xa).astype(np.int64), 0, size - 1)
            iy = np.clip(np.floor(ya).astype(np.int64), 0, size - 1)
        np.add.at(grid, (iy, ix), deposit)
        np.clip(grid, 0.0, _FIELD_CAP, out=grid)
        fd[: size * size] = grid.ravel().tolist()
