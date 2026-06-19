"""Tests for grid_engine numpy execution."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.grid_field_compiler import compile_grid_program
from pixil_utils.grid_engine import grid_fill, run_grid_step, run_field_render, reset_grid_runtime
from pixil_utils.variable_registry import VariableRegistry


LIFE_BODY = [
    "size 4",
    "cell 1",
    "fields v_grid",
    "steps 1",
    "boundary wrap",
    "step v_grid {",
    "v_n = neighbors(v_grid)",
    "v_alive = at(v_grid) == 1",
    "v_grid_next = where(v_alive and (v_n == 2 or v_n == 3), 1, where(v_n == 3, 1, 0))",
    "}",
    "draw {",
    "fill_field v_grid",
    "fill_color cyan",
    "fill_intensity 90",
    "}",
]


def _make_vars():
    reg = VariableRegistry()
    reg.register("v_grid")
    reg.set("v_grid", PixilArray(16))
    return reg


def test_life_blinker_step():
    reset_grid_runtime()
    prog = compile_grid_program("life", LIFE_BODY)
    variables = _make_vars()
    grid = variables.get("v_grid")
    # Horizontal blinker in middle row: indices 5,6,7 on row 1 (y=1)
    for i in range(16):
        grid[i] = 0
    grid[5] = 1
    grid[6] = 1
    grid[7] = 1

    draws = []

    def capture(cmd, args):
        draws.append((cmd, args))

    run_grid_step(prog, variables, capture)
    # Vertical blinker: cells (2,1), (6,1), (10,1) -> x=1,y=1 etc for 4x4
    # row1 col1=5, col2=6, col3=7 horizontal -> next vertical at col2: indices 2,6,10
    assert grid[2] == 1
    assert grid[6] == 1
    assert grid[10] == 1
    assert grid[5] == 0
    assert len(draws) > 0


def test_grid_fill():
    variables = _make_vars()
    grid_fill(variables, "v_grid", 0.5)
    grid = variables.get("v_grid")
    assert grid[0] == 0.5
    assert grid[15] == 0.5


def test_ripple_wave_field():
    from pixil_utils.grid_field_compiler import compile_field_program
    from pixil_utils.grid_engine import run_field_render
    from pixil_utils.variable_registry import VariableRegistry

    body = [
        "size 8",
        "sites v_source_x, v_source_y",
        "phases v_source_phase",
        "active v_source_active",
        "mode formula",
        "signed true",
        "peak_color cyan",
        "trough_color blue",
        "intensity_scale 35",
        "value {",
        "v_height = sum_sites(sin(sqrt(dist2) / 4 - phase) * pow(0.97, sqrt(dist2)))",
        "}",
    ]
    prog = compile_field_program("ripple", body)
    reg = VariableRegistry()
    for name in ("v_source_x", "v_source_y", "v_source_phase", "v_source_active"):
        reg.register(name)
        reg.set(name, PixilArray(2))
    reg.get("v_source_x")[0] = 4
    reg.get("v_source_y")[0] = 4
    reg.get("v_source_phase")[0] = 0
    reg.get("v_source_active")[0] = 1
    reg.get("v_source_active")[1] = 0

    draws = []

    def capture(cmd, args):
        draws.append((cmd, args))

    run_field_render(prog, reg, capture)
    assert len(draws) > 0


def test_fire_propagation_step():
    reset_grid_runtime()
    body = [
        "size 4",
        "cell 1",
        "fields v_heat",
        "steps 1",
        "boundary clamp",
        "step v_heat {",
        "v_heat_next = where(grid_y < 3, max(0, below_avg(v_heat) - random_field(0, 1)), at(v_heat))",
        "}",
        "draw {",
        "fire_field v_heat",
        "}",
    ]
    prog = compile_grid_program("fire", body)
    reg = VariableRegistry()
    reg.register("v_heat")
    reg.register("v_max_y")
    reg.set("v_max_y", 3)
    reg.set("v_heat", PixilArray(16))
    heat = reg.get("v_heat")
    for i in range(16):
        heat[i] = 0
    for x in range(4):
        heat[12 + x] = 100

    run_grid_step(prog, reg, lambda _c, _a: None)
    assert heat[8] > 0


def test_metaballs_field_render():
    from pixil_utils.grid_field_compiler import compile_field_program

    body = [
        "size 8",
        "sites v_px, v_py",
        "weights v_radius",
        "mode metaballs",
        "plot_if v_sum > 1",
        "color 50",
        "opacity 80",
    ]
    prog = compile_field_program("blobs", body)
    reg = VariableRegistry()
    reg.register("v_px")
    reg.register("v_py")
    reg.register("v_radius")
    reg.set("v_px", PixilArray(1))
    reg.set("v_py", PixilArray(1))
    reg.set("v_radius", PixilArray(1))
    reg.get("v_px")[0] = 4
    reg.get("v_py")[0] = 4
    reg.get("v_radius")[0] = 4

    draws = []

    def capture(cmd, args):
        draws.append((cmd, args))

    run_field_render(prog, reg, capture)
    assert len(draws) > 0
