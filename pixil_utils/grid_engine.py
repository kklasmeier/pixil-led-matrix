"""NumPy execution for grid_program and field_program."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .array_manager import PixilArray
from .grid_expr import (
    ExprNode,
    FieldEvalContext,
    GridEvalContext,
    eval_expr,
    resolve_scalar,
    resolve_size,
)
from .grid_field_compiler import FieldProgram, GridDrawSpec, GridProgram, StepBlock


@dataclass
class _GridRuntime:
    size: int
    boundary: str
    active_idx: Dict[str, int] = field(default_factory=dict)
    buffers: Dict[str, List[np.ndarray]] = field(default_factory=dict)


_RUNTIME: Dict[str, _GridRuntime] = {}


def _build_scalars(variables: Any) -> Dict[str, float]:
    scalars: Dict[str, float] = {}
    for name in variables.name_to_index:
        val = variables.get(name)
        if isinstance(val, PixilArray):
            continue
        if isinstance(val, bool):
            scalars[name] = 1.0 if val else 0.0
        elif isinstance(val, (int, float)):
            scalars[name] = float(val)
    return scalars


def _get_array(variables: Any, name: str) -> PixilArray:
    arr = variables.get(name) if hasattr(variables, "get") else variables[name]
    if not isinstance(arr, PixilArray):
        raise ValueError(f"{name} is not an array")
    return arr


def _array_to_numpy(arr: PixilArray) -> np.ndarray:
    return np.asarray(arr.data, dtype=np.float64)


def _write_back(arr: PixilArray, data: np.ndarray) -> None:
    flat = np.asarray(data, dtype=np.float64).ravel()
    for i, val in enumerate(flat):
        arr.data[i] = float(val)


def grid_fill(variables: Any, array_name: str, value: float) -> None:
    arr = _get_array(variables, array_name)
    fill = float(value)
    for i in range(arr.size):
        arr.data[i] = fill


def _ensure_runtime(program: GridProgram, variables: Any) -> _GridRuntime:
    size = resolve_size(program.size, variables)
    key = program.name
    if key not in _RUNTIME:
        rt = _GridRuntime(size=size, boundary=program.boundary)
        for fname in program.fields:
            src = _array_to_numpy(_get_array(variables, fname))
            if src.size != size * size:
                raise ValueError(
                    f"Field {fname} size {src.size} != {size * size}"
                )
            rt.buffers[fname] = [src.copy(), src.copy()]
            rt.active_idx[fname] = 0
        _RUNTIME[key] = rt
    rt = _RUNTIME[key]
    rt.size = size
    rt.boundary = program.boundary
    return rt


def _reshape(field: np.ndarray, size: int) -> np.ndarray:
    return field.reshape(size, size)


def _laplacian_4(field: np.ndarray, size: int, boundary: str) -> np.ndarray:
    grid = _reshape(field, size)
    if boundary == "wrap":
        up = np.roll(grid, 1, axis=0)
        down = np.roll(grid, -1, axis=0)
        left = np.roll(grid, 1, axis=1)
        right = np.roll(grid, -1, axis=1)
    else:
        up = np.vstack([grid[0:1, :], grid[:-1, :]])
        down = np.vstack([grid[1:, :], grid[-1:, :]])
        left = np.hstack([grid[:, 0:1], grid[:, :-1]])
        right = np.hstack([grid[:, 1:], grid[:, -1:]])
    lap = left + right + up + down - 4.0 * grid
    return lap.ravel()


def _neighbor_count(field: np.ndarray, size: int, boundary: str, orthogonal: bool) -> np.ndarray:
    alive = (_reshape(field, size) > 0.5).astype(np.float64)
    if boundary == "wrap":
        total = np.zeros_like(alive)
        shifts = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        if not orthogonal:
            shifts += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dy, dx in shifts:
            total += np.roll(np.roll(alive, dy, axis=0), dx, axis=1)
        return total.ravel()
    padded = np.pad(alive, 1, mode="edge")
    total = np.zeros_like(alive)
    offsets = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    if not orthogonal:
        offsets += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    h, w = alive.shape
    for dy, dx in offsets:
        y0, y1 = 1 + dy, 1 + dy + h
        x0, x1 = 1 + dx, 1 + dx + w
        total += padded[y0:y1, x0:x1]
    return total.ravel()


def _grid_coords(size: int) -> Dict[str, np.ndarray]:
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float64)
    return {"grid_x": xs.ravel(), "grid_y": ys.ravel()}


def _below_avg(field: np.ndarray, size: int) -> np.ndarray:
    g = _reshape(field, size)
    out = g.copy()
    for y in range(size - 1):
        below_y = y + 1
        for x in range(size):
            total = g[below_y, x]
            count = 1
            if x > 0:
                total += g[below_y, x - 1]
                count += 1
            if x < size - 1:
                total += g[below_y, x + 1]
                count += 1
            out[y, x] = total / count
    return out.ravel()


def _random_field(lo: float, hi: float, size: int) -> np.ndarray:
    return np.random.uniform(lo, hi, size * size)


def _read_fields(rt: _GridRuntime, names: List[str]) -> Dict[str, np.ndarray]:
    return {name: rt.buffers[name][rt.active_idx[name]] for name in names}


def _write_field(rt: _GridRuntime, name: str, data: np.ndarray) -> None:
    idx = 1 - rt.active_idx[name]
    rt.buffers[name][idx][:] = np.asarray(data, dtype=np.float64).ravel()


def _swap_fields(rt: _GridRuntime, names: List[str]) -> None:
    for name in names:
        rt.active_idx[name] = 1 - rt.active_idx[name]


def _execute_step_block(
    block: StepBlock,
    rt: _GridRuntime,
    program: GridProgram,
    variables: Any,
) -> None:
    read_fields = _read_fields(rt, program.fields)
    temps: Dict[str, np.ndarray] = {}
    scalars = _build_scalars(variables)

    def lap_fn(field_name: str) -> np.ndarray:
        if field_name not in read_fields:
            raise KeyError(field_name)
        return _laplacian_4(read_fields[field_name], rt.size, rt.boundary)

    def neighbors_fn(field_name: str, orthogonal: bool) -> np.ndarray:
        if field_name not in read_fields:
            raise KeyError(field_name)
        return _neighbor_count(read_fields[field_name], rt.size, rt.boundary, orthogonal)

    def below_avg_fn(field_name: str) -> np.ndarray:
        if field_name not in read_fields:
            raise KeyError(field_name)
        return _below_avg(read_fields[field_name], rt.size)

    def random_field_fn(lo: float, hi: float) -> np.ndarray:
        return _random_field(lo, hi, rt.size)

    ctx = GridEvalContext(
        scalars=scalars,
        fields=read_fields,
        temps=temps,
        grid_vars=_grid_coords(rt.size),
        size=rt.size,
        boundary=rt.boundary,
        laplacian_fn=lap_fn,
        neighbors_fn=neighbors_fn,
        below_avg_fn=below_avg_fn,
        random_field_fn=random_field_fn,
    )

    output_name = f"{block.field}_next"
    result: Optional[np.ndarray] = None
    for target, expr in block.assignments:
        value = eval_expr(expr, ctx)
        if isinstance(value, np.ndarray):
            temps[target] = value
        else:
            temps[target] = np.full(rt.size * rt.size, float(value), dtype=np.float64)
        if target == output_name:
            result = temps[target]

    if result is None:
        raise ValueError(f"step {block.field}: missing assignment to {output_name}")
    _write_field(rt, block.field, result)


def _clamp_palette_color(base: float, scale: float, field_val: np.ndarray) -> np.ndarray:
    colors = base + np.floor(field_val * scale)
    colors = np.where(colors > 99, colors - 98, colors)
    colors = np.where(colors < 1, 1, colors)
    return colors


def _render_grid(
    program: GridProgram,
    rt: _GridRuntime,
    variables: Any,
    append_draw: Callable[[str, List[Any]], None],
) -> None:
    size = rt.size
    cell = max(1, resolve_size(program.cell, variables))
    draw = program.draw
    active = _read_fields(rt, program.fields)

    if draw.mode == "palette":
        field_name = draw.palette_field or program.fields[-1]
        field_vals = active[field_name]
        base = resolve_scalar(draw.color_base, variables)
        scale = resolve_scalar(draw.color_scale, variables)
        i_base = resolve_scalar(draw.intensity_base, variables)
        i_scale = resolve_scalar(draw.intensity_scale, variables)
        colors = _clamp_palette_color(base, scale, field_vals)
        intensities = np.clip(i_base + np.floor(field_vals * i_scale), 0, 100)
        grid = _reshape(field_vals, size)
        color_grid = _reshape(colors, size)
        int_grid = _reshape(intensities, size)
        for y in range(size):
            for x in range(size):
                px = x * cell
                py = y * cell
                color = int(color_grid[y, x])
                intensity = int(int_grid[y, x])
                if cell == 1:
                    append_draw("mplot", [px, py, color, intensity])
                else:
                    append_draw(
                        "draw_rectangle",
                        [px, py, cell, cell, color, intensity, True],
                    )
        return

    if draw.mode == "fill":
        field_name = draw.fill_field or program.fields[0]
        field_vals = active[field_name]
        grid = _reshape(field_vals, size)
        color = draw.fill_color
        intensity = int(resolve_scalar(draw.fill_intensity, variables))
        for y in range(size):
            for x in range(size):
                if grid[y, x] <= 0.5:
                    continue
                px = x * cell
                py = y * cell
                if cell == 1:
                    append_draw("mplot", [px, py, color, intensity])
                else:
                    append_draw(
                        "draw_rectangle",
                        [px, py, cell, cell, color, intensity, True],
                    )
        return

        return

    if draw.mode == "fire":
        field_name = draw.fire_field or program.fields[0]
        heat = _reshape(active[field_name], size)
        for y in range(size):
            for x in range(size):
                h = heat[y, x]
                if h <= 0:
                    continue
                if h < 20:
                    color: Any = 0
                    intensity = int(h * 3)
                elif h < 40:
                    color = "red"
                    intensity = int((h - 20) * 3 + 20)
                elif h < 70:
                    color = "orange"
                    intensity = int((h - 40) * 2 + 40)
                else:
                    color = "yellow"
                    intensity = int(min(h, 100))
                px = x * cell
                py = y * cell
                if cell == 1:
                    append_draw("mplot", [px, py, color, intensity])
                else:
                    append_draw(
                        "draw_rectangle",
                        [px, py, cell, cell, color, intensity, True],
                    )
        return

    if draw.mode == "expr":
        read_fields = active
        temps: Dict[str, np.ndarray] = {}
        scalars = _build_scalars(variables)

        def lap_fn(field_name: str) -> np.ndarray:
            return _laplacian_4(read_fields[field_name], size, rt.boundary)

        def neighbors_fn(field_name: str, orthogonal: bool) -> np.ndarray:
            return _neighbor_count(read_fields[field_name], size, rt.boundary, orthogonal)

        def below_avg_fn(field_name: str) -> np.ndarray:
            return _below_avg(read_fields[field_name], size)

        def random_field_fn(lo: float, hi: float) -> np.ndarray:
            return _random_field(lo, hi, size)

        ctx = GridEvalContext(
            scalars=scalars,
            fields=read_fields,
            temps=temps,
            grid_vars=_grid_coords(size),
            size=size,
            boundary=rt.boundary,
            laplacian_fn=lap_fn,
            neighbors_fn=neighbors_fn,
            below_avg_fn=below_avg_fn,
            random_field_fn=random_field_fn,
        )
        mask = eval_expr(draw.plot_if, ctx) if draw.plot_if else np.ones(size * size, dtype=bool)
        if not isinstance(mask, np.ndarray):
            mask = np.full(size * size, bool(mask))
        colors = eval_expr(draw.color_expr, ctx) if draw.color_expr else np.full(size * size, 1.0)
        opacities = eval_expr(draw.opacity_expr, ctx) if draw.opacity_expr else np.full(size * size, 100.0)
        if not isinstance(colors, np.ndarray):
            colors = np.full(size * size, float(colors))
        if not isinstance(opacities, np.ndarray):
            opacities = np.full(size * size, float(opacities))
        mask_grid = _reshape(mask.astype(np.float64), size) > 0
        color_grid = _reshape(colors, size)
        opacity_grid = _reshape(opacities, size)
        for y in range(size):
            for x in range(size):
                if not mask_grid[y, x]:
                    continue
                px = x * cell
                py = y * cell
                color_val = color_grid[y, x]
                color: Any = int(color_val) if float(color_val).is_integer() else int(round(color_val))
                intensity = int(np.clip(opacity_grid[y, x], 0, 100))
                if cell == 1:
                    append_draw("mplot", [px, py, color, intensity])
                else:
                    append_draw(
                        "draw_rectangle",
                        [px, py, cell, cell, color, intensity, True],
                    )
        return

    raise ValueError(f"Unknown draw mode: {draw.mode}")


def run_grid_step(
    program: GridProgram,
    variables: Any,
    append_draw: Callable[[str, List[Any]], None],
) -> None:
    rt = _ensure_runtime(program, variables)
    step_count = max(1, resolve_size(program.steps, variables))
    for _ in range(step_count):
        for block in program.step_blocks:
            _execute_step_block(block, rt, program, variables)
        _swap_fields(rt, program.fields)

    for fname in program.fields:
        active = rt.buffers[fname][rt.active_idx[fname]]
        _write_back(_get_array(variables, fname), active)

    _render_grid(program, rt, variables, append_draw)


def _site_arrays(
    variables: Any,
    xs_name: str,
    ys_name: str,
    weights_name: Optional[str] = None,
    phases_name: Optional[str] = None,
    active_name: Optional[str] = None,
) -> tuple:
    xs = _get_array(variables, xs_name)
    ys = _get_array(variables, ys_name)
    n = xs.size
    px = np.asarray([xs[i] for i in range(n)], dtype=np.float64)
    py = np.asarray([ys[i] for i in range(n)], dtype=np.float64)
    weights = None
    if weights_name:
        w_arr = _get_array(variables, weights_name)
        weights = np.asarray([w_arr[i] for i in range(n)], dtype=np.float64)
    phases = None
    if phases_name:
        p_arr = _get_array(variables, phases_name)
        phases = np.asarray([p_arr[i] for i in range(n)], dtype=np.float64)
    active = None
    if active_name:
        a_arr = _get_array(variables, active_name)
        active = np.asarray([a_arr[i] for i in range(n)], dtype=np.float64)
    return px, py, weights, phases, active, n


def _eval_value_formula(
    program: FieldProgram,
    variables: Any,
    size: int,
) -> np.ndarray:
    px, py, weights, phases, active, n = _site_arrays(
        variables,
        program.sites_x,
        program.sites_y,
        program.weights,
        program.phases,
        program.active,
    )
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float64)
    grid_vars = {"grid_x": xs, "grid_y": ys}
    scalars = _build_scalars(variables)
    temps: Dict[str, np.ndarray] = {}

    if program.mode == "metaballs":
        result = np.zeros((size, size), dtype=np.float64)
        for i in range(n):
            if active is not None and active[i] <= 0:
                continue
            dx = xs - px[i]
            dy = ys - py[i]
            dist2 = np.maximum(dx * dx + dy * dy, 1.0)
            w = weights[i] if weights is not None else 1.0
            result += (w * w) / dist2
        return result

    def sum_sites_fn(expr: ExprNode) -> np.ndarray:
        acc = np.zeros((size, size), dtype=np.float64)
        for i in range(n):
            if active is not None and active[i] <= 0:
                continue
            dx = xs - px[i]
            dy = ys - py[i]
            dist2 = dx * dx + dy * dy
            w = weights[i] if weights is not None else 1.0
            ph = phases[i] if phases is not None else 0.0
            site_ctx = FieldEvalContext(
                scalars=scalars,
                temps=temps,
                site_vars={
                    "dx": dx,
                    "dy": dy,
                    "dist2": dist2,
                    "weight": np.full_like(dx, w),
                    "phase": np.full_like(dx, ph),
                    "active": np.full_like(dx, active[i] if active is not None else 1.0),
                },
                grid_vars=grid_vars,
                sum_sites_fn=sum_sites_fn,
            )
            val = eval_expr(expr, site_ctx)
            if not isinstance(val, np.ndarray):
                val = np.full((size, size), float(val))
            acc += val
        return acc

    for target, expr in program.value_assignments:
        ctx = FieldEvalContext(
            scalars=scalars,
            temps=temps,
            site_vars={},
            grid_vars=grid_vars,
            sum_sites_fn=sum_sites_fn,
        )
        value = eval_expr(expr, ctx)
        if isinstance(value, np.ndarray):
            temps[target] = value
        else:
            temps[target] = np.full((size, size), float(value))

    if program.value_result and program.value_result in temps:
        return temps[program.value_result]
    raise ValueError("field_program formula produced no value")


def _render_voronoi(
    program: FieldProgram,
    variables: Any,
    size: int,
    append_draw: Callable[[str, List[Any]], None],
) -> None:
    px, py, _, _, _, n = _site_arrays(
        variables, program.sites_x, program.sites_y, program.weights
    )
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float64)
    dist2 = (xs[None, :, :] - px[:, None, None]) ** 2 + (ys[None, :, :] - py[:, None, None]) ** 2
    closest = np.argmin(dist2, axis=0)
    sorted_d = np.sort(dist2, axis=0)
    min_dist = sorted_d[0]
    second_dist = sorted_d[1]
    edge_ratio = resolve_scalar(program.edge_ratio, variables)
    edge_mask = second_dist < min_dist * edge_ratio

    site_colors = None
    if program.site_colors:
        site_colors = _get_array(variables, program.site_colors)

    fill_opacity = int(resolve_scalar(program.fill_opacity, variables))
    edge_opacity = int(resolve_scalar(program.edge_opacity, variables))
    edge_color = program.edge_color

    for y in range(size):
        for x in range(size):
            if program.edges and edge_mask[y, x]:
                append_draw("mplot", [x, y, edge_color, edge_opacity])
            else:
                ci = int(closest[y, x])
                if site_colors is not None:
                    color = int(site_colors[ci])
                else:
                    color = (ci * 17) % 99 + 1
                append_draw("mplot", [x, y, color, fill_opacity])


def _resolve_color_name(name: str, variables: Any) -> str:
    text = name.strip()
    if text.startswith("v_"):
        val = variables.get(text) if hasattr(variables, "get") else variables[text]
        if isinstance(val, str):
            if val.startswith('"') and val.endswith('"'):
                return val[1:-1]
            return val
    return text


def _render_field_signed(
    program: FieldProgram,
    value_grid: np.ndarray,
    variables: Any,
    size: int,
    append_draw: Callable[[str, List[Any]], None],
) -> None:
    peak = _resolve_color_name(program.peak_color, variables)
    trough = _resolve_color_name(program.trough_color, variables)
    scale = resolve_scalar(program.intensity_scale, variables)
    grid = value_grid
    for y in range(size):
        for x in range(size):
            h = grid[y, x]
            intensity = int(np.clip(abs(h) * scale, 0, 99))
            if intensity <= 0:
                continue
            color = peak if h > 0 else trough
            append_draw("mplot", [x, y, color, intensity])


def run_field_render(
    program: FieldProgram,
    variables: Any,
    append_draw: Callable[[str, List[Any]], None],
) -> None:
    size = resolve_size(program.size, variables)

    if program.mode == "voronoi":
        _render_voronoi(program, variables, size, append_draw)
        return

    value_grid = _eval_value_formula(program, variables, size)

    if program.signed:
        _render_field_signed(program, value_grid, variables, size, append_draw)
        return

    flat = value_grid.ravel()
    result_name = program.value_result or "v_sum"
    scalars = _build_scalars(variables)
    temps = {result_name: flat, "v_sum": flat}
    ctx = FieldEvalContext(
        scalars=scalars,
        temps=temps,
        site_vars={},
        grid_vars={},
        sum_sites_fn=lambda _e: flat,
    )

    if program.plot_if is not None:
        mask = eval_expr(program.plot_if, ctx)
        if not isinstance(mask, np.ndarray):
            mask = np.full(size * size, bool(mask))
    else:
        mask = np.ones(size * size, dtype=bool)

    colors = eval_expr(program.color_expr, ctx) if program.color_expr else np.full(size * size, 50.0)
    opacities = eval_expr(program.opacity_expr, ctx) if program.opacity_expr else np.full(size * size, 75.0)
    if not isinstance(colors, np.ndarray):
        colors = np.full(size * size, float(colors))
    if not isinstance(opacities, np.ndarray):
        opacities = np.full(size * size, float(opacities))

    grid = _reshape(value_grid.ravel(), size)
    mask_grid = _reshape(mask.astype(np.float64), size) > 0
    color_grid = _reshape(colors, size)
    opacity_grid = _reshape(opacities, size)

    for y in range(size):
        for x in range(size):
            if not mask_grid[y, x]:
                continue
            color_val = color_grid[y, x]
            color: Any = int(round(color_val))
            intensity = int(np.clip(opacity_grid[y, x], 0, 100))
            append_draw("mplot", [x, y, color, intensity])


def reset_grid_runtime(name: Optional[str] = None) -> None:
    if name is None:
        _RUNTIME.clear()
    elif name in _RUNTIME:
        del _RUNTIME[name]
