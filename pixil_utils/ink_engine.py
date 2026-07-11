"""Vectorized ink-in-water particle step for Ink_In_Water.pix."""

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


def _resolve_color(name: str, variables: Any) -> str:
    text = name.strip()
    if text.startswith("v_"):
        val = variables.get(text) if hasattr(variables, "get") else variables[text]
        if isinstance(val, str):
            if val.startswith('"') and val.endswith('"'):
                return val[1:-1]
            return val
    return text


def _set_scalar(variables: Any, name: str, value: float) -> None:
    if hasattr(variables, "set"):
        variables.set(name, value)
    else:
        variables[name] = value


def run_ink_step(
    variables: Any,
    append_draw: Callable[[str, List[Any]], None],
) -> None:
    px = _get_array(variables, "v_px")
    py = _get_array(variables, "v_py")
    vx = _get_array(variables, "v_vx")
    vy = _get_array(variables, "v_vy")
    intensity = _get_array(variables, "v_intensity")
    alive = _get_array(variables, "v_alive")
    curve_x = _get_array(variables, "v_curve_x")
    curve_y = _get_array(variables, "v_curve_y")

    drop_x = resolve_scalar("v_drop_x", variables)
    drop_y = resolve_scalar("v_drop_y", variables)
    drift_x = resolve_scalar("v_drift_x", variables)
    drift_y = resolve_scalar("v_drift_y", variables)
    swirl_active = resolve_scalar("v_swirl_active", variables)
    swirl_strength = resolve_scalar("v_swirl_strength", variables)
    swirl_dir = resolve_scalar("v_swirl_dir", variables)
    fade_rate = resolve_scalar("v_fade_rate", variables)

    color_bright = _resolve_color("v_color_bright", variables)
    color_mid = _resolve_color("v_color_mid", variables)
    color_dark = _resolve_color("v_color_dark", variables)

    n = px.size
    any_alive = 0.0

    for i in range(n):
        if alive[i] <= 0:
            continue

        x = float(px[i])
        y = float(py[i])
        ivx = float(vx[i])
        ivy = float(vy[i])

        ivx = ivx * 0.98 + float(curve_x[i]) + drift_x
        ivy = ivy * 0.98 + float(curve_y[i]) + drift_y

        if swirl_active >= 1:
            dx = x - drop_x
            dy = y - drop_y
            ivx += dy * swirl_strength * swirl_dir * -1.0
            ivy += dx * swirl_strength * swirl_dir

        x += ivx
        y += ivy
        inten = float(intensity[i]) - fade_rate

        vx[i] = ivx
        vy[i] = ivy
        px[i] = x
        py[i] = y

        if inten <= 0:
            alive[i] = 0
            intensity[i] = 0
            continue

        alive[i] = 1
        intensity[i] = inten
        any_alive = 1.0

        draw_intensity = int(inten)
        if draw_intensity > 60:
            color = color_bright
            plot_intensity = draw_intensity
        elif draw_intensity > 30:
            color = color_mid
            plot_intensity = draw_intensity + 20
        else:
            color = color_dark
            plot_intensity = draw_intensity + 30

        plot_intensity = int(np.clip(plot_intensity, 0, 100))
        ix = int(x)
        iy = int(y)
        if 0 <= ix <= 63 and 0 <= iy <= 63:
            append_draw("mplot", [ix, iy, color, plot_intensity])

    _set_scalar(variables, "v_any_alive", any_alive)
