"""Vectorized Chladni particle settle step for Chladni_Patterns.pix."""

from __future__ import annotations

from typing import Any, Callable, List

import numpy as np

from .array_manager import PixilArray
from .grid_expr import resolve_scalar


def _get_array(variables: Any, name: str) -> PixilArray:
    arr = variables.get(name) if hasattr(variables, "get") else variables[name]
    if not isinstance(arr, PixilArray):
        raise ValueError(f"{name} is not an array")
    return arr


def _chladni_value(x: float, y: float, n_scale: float, m_scale: float) -> float:
    cx = x - 32.0
    cy = y - 32.0
    term1 = np.cos(n_scale * cx) * np.cos(m_scale * cy)
    term2 = np.cos(m_scale * cx) * np.cos(n_scale * cy)
    return float(np.abs(term1 + term2))


def _clamp_particle(x: float, y: float) -> tuple[float, float]:
    if x < 2:
        x = 2.0
    if x > 61:
        x = 61.0
    if y < 2:
        y = 2.0
    if y > 61:
        y = 61.0
    return x, y


def _move_particle(
    x: float,
    y: float,
    n_scale: float,
    m_scale: float,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    current_val = _chladni_value(x, y, n_scale, m_scale)
    best_x = x
    best_y = y
    best_val = current_val

    axis = int(rng.integers(0, 2))
    if axis == 0:
        if x > 2:
            tx = x - 1
            test_val = _chladni_value(tx, y, n_scale, m_scale)
            if test_val < best_val:
                best_val = test_val
                best_x = tx
        if x < 61:
            tx = x + 1
            test_val = _chladni_value(tx, y, n_scale, m_scale)
            if test_val < best_val:
                best_val = test_val
                best_x = tx
    else:
        if y > 2:
            ty = y - 1
            test_val = _chladni_value(x, ty, n_scale, m_scale)
            if test_val < best_val:
                best_val = test_val
                best_y = ty
        if y < 61:
            ty = y + 1
            test_val = _chladni_value(x, ty, n_scale, m_scale)
            if test_val < best_val:
                best_val = test_val
                best_y = ty

    roll = int(rng.integers(0, 100))

    if current_val > 0.8:
        nx = x + (best_x - x) * 2
        ny = y + (best_y - y) * 2
        nx, ny = _clamp_particle(nx, ny)
    elif current_val > 0.4:
        if roll < 90:
            nx, ny = best_x, best_y
        else:
            nx, ny = x, y
    elif current_val > 0.15:
        if roll < 70:
            nx, ny = best_x, best_y
        else:
            nx, ny = x, y
    else:
        if roll < 20:
            nx = x + float(rng.integers(-1, 2))
            ny = y + float(rng.integers(-1, 2))
            if nx <= 2 or nx >= 61:
                nx = x
            if ny <= 2 or ny >= 61:
                ny = y
        else:
            nx, ny = x, y

    return nx, ny, current_val


def _color_for_value(val: float) -> tuple[Any, int]:
    if val < 0.15:
        return "white", 100
    if val < 0.4:
        return "light_gray", 85
    return "gold", 65


def run_chladni_step(
    variables: Any,
    px_name: str,
    py_name: str,
    n_scale_name: str,
    m_scale_name: str,
    append_draw: Callable[[str, List[Any]], None],
) -> None:
    px_arr = _get_array(variables, px_name)
    py_arr = _get_array(variables, py_name)
    n_scale = resolve_scalar(n_scale_name, variables)
    m_scale = resolve_scalar(m_scale_name, variables)
    n = px_arr.size
    rng = np.random.default_rng()

    for i in range(n):
        x = float(px_arr[i])
        y = float(py_arr[i])
        nx, ny, settle_val = _move_particle(x, y, n_scale, m_scale, rng)
        px_arr[i] = nx
        py_arr[i] = ny
        color, intensity = _color_for_value(settle_val)
        ix = int(nx)
        iy = int(ny)
        if 0 <= ix <= 63 and 0 <= iy <= 63:
            append_draw("mplot", [ix, iy, color, intensity])
