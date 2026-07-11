"""Tests for escape_iter fractal builtin."""

import numpy as np
import pytest

from pixil_utils.fractal_escape import escape_iter, escape_perturb, escape_zoom
from pixil_utils.grid_field_compiler import compile_field_program
from pixil_utils.grid_engine import run_field_render, reset_grid_runtime
from pixil_utils.grid_expr import FieldEvalContext, eval_expr, parse_expr
from pixil_utils.array_manager import PixilArray
from pixil_utils.variable_registry import VariableRegistry


def test_escape_iter_mandelbrot_interior():
    esc = escape_iter(np.array([0.0]), np.array([0.0]), 32)
    assert esc[0] == 32


def test_escape_iter_mandelbrot_exterior():
    esc = escape_iter(np.array([3.0]), np.array([0.0]), 32)
    assert esc[0] == 1


def test_escape_iter_julia_constant_c():
    z_re = np.array([0.0, 2.0])
    z_im = np.array([0.0, 0.0])
    esc = escape_iter(np.array(-0.8), np.array(0.156), 48, z0_re=z_re, z0_im=z_im)
    assert esc.shape == (2,)
    assert esc[1] < 48


def test_escape_iter_via_expr_parser():
    size = 4
    xs, ys = np.mgrid[0:size, 0:size].astype(np.float64)
    ctx = FieldEvalContext(
        scalars={"v_max_iter": 16.0},
        temps={},
        site_vars={},
        grid_vars={"grid_x": xs, "grid_y": ys},
        sum_sites_fn=lambda _e: np.zeros((size, size)),
    )
    node = parse_expr("escape_iter(grid_x / 2 - 1.5, grid_y / 2 - 1.5, v_max_iter)")
    result = eval_expr(node, ctx)
    assert result.shape == (size, size)
    assert np.any(result < 16)


MANDEL_BODY = [
    "size 8",
    "sites v_dummy_x, v_dummy_y",
    "mode formula",
    "value {",
    "v_re = grid_x / 8 - 0.5",
    "v_im = grid_y / 8 - 0.5",
    "v_iter = escape_iter(v_re, v_im, 24)",
    "}",
    "plot_if v_iter < 24",
    "color clamp(v_iter * 4, 1, 99)",
    "opacity 80",
]


def test_mandelbrot_field_render():
    reset_grid_runtime()
    prog = compile_field_program("mandel", MANDEL_BODY)
    reg = VariableRegistry()
    for name in ("v_dummy_x", "v_dummy_y"):
        reg.register(name)
        reg.set(name, PixilArray(1))
    reg.get("v_dummy_x")[0] = 4
    reg.get("v_dummy_y")[0] = 4

    draws = []

    def capture(cmd, args):
        draws.append((cmd, args))

    run_field_render(prog, reg, capture)
    assert len(draws) > 0


def test_escape_perturb_deep_zoom_has_pixel_variation():
    half = 32
    xs, ys = np.mgrid[0:64, 0:64].astype(np.float64)
    eff = 2.0e6
    dc_re = (xs - half) / eff
    dc_im = (ys - half) / eff
    esc = escape_perturb(-0.743643887, 0.131825904, dc_re, dc_im, 280)
    assert np.std(esc[esc < 280]) > 10.0


def test_escape_zoom_uses_perturb_when_dc_tiny():
    half = 32
    xs, ys = np.mgrid[0:64, 0:64].astype(np.float64)
    eff = 5.0e6
    dc_re = (xs - half) / eff
    dc_im = (ys - half) / eff
    esc = escape_zoom(-0.743643887, 0.131825904, dc_re, dc_im, 260)
    assert len(np.unique(esc)) > 20


def test_escape_zoom_uses_direct_when_dc_large():
    half = 16
    xs, ys = np.mgrid[0:32, 0:32].astype(np.float64)
    eff = 40.0
    dc_re = (xs - half) / eff
    dc_im = (ys - half) / eff
    ar, ai = -0.743643887, 0.131825904
    direct = escape_iter(ar + dc_re, ai + dc_im, 120)
    zoomed = escape_zoom(ar, ai, dc_re, dc_im, 120)
    assert np.mean(np.abs(direct - zoomed)) < 0.01
