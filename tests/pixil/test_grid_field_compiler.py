"""Tests for grid_program / field_program compiler."""

import pytest

from pixil_utils.grid_field_compiler import compile_field_program, compile_grid_program
from pixil_utils.grid_expr import parse_expr, eval_expr, GridEvalContext
import numpy as np


GRAY_SCOTT_BODY = [
    "size v_size",
    "cell v_cell",
    "fields v_u, v_v",
    "steps 1",
    "boundary clamp",
    "step v_u {",
    "v_lap_u = lap(v_u)",
    "v_uvv = at(v_u) * at(v_v) * at(v_v)",
    "v_u_next = at(v_u) + v_dt * (v_du * v_lap_u - v_uvv + v_f * (1 - at(v_u)))",
    "v_u_next = clamp(v_u_next, 0, 1)",
    "}",
    "step v_v {",
    "v_lap_v = lap(v_v)",
    "v_uvv = at(v_u) * at(v_v) * at(v_v)",
    "v_v_next = at(v_v) + v_dt * (v_dv * v_lap_v + v_uvv - (v_f + v_k) * at(v_v))",
    "v_v_next = clamp(v_v_next, 0, 1)",
    "}",
    "draw {",
    "palette_field v_v",
    "color_base v_color_base",
    "color_scale 65",
    "intensity_base 28",
    "intensity_scale 72",
    "}",
]


def test_collect_nested_grid_program_block():
    from pixil_utils.grid_field_compiler import collect_brace_block_lines, compile_grid_program

    lines = iter([
        "    size v_size",
        "    step v_u {",
        "        v_u_next = clamp(at(v_u), 0, 1)",
        "    }",
        "    draw {",
        "        palette_field v_v",
        "    }",
        "}",
    ])
    body = collect_brace_block_lines(lines)
    assert len(body) == 7
    assert body[1].startswith("step v_u")


def test_compile_gray_scott_program():
    prog = compile_grid_program("gray_scott", GRAY_SCOTT_BODY)
    assert prog.name == "gray_scott"
    assert prog.fields == ["v_u", "v_v"]
    assert len(prog.step_blocks) == 2
    assert prog.draw.palette_field == "v_v"


def test_compile_metaballs_field_program():
    body = [
        "size 64",
        "sites v_pos_x, v_pos_y",
        "weights v_radius",
        "mode formula",
        "value {",
        "v_sum = sum_sites((weight * weight) / max(dist2, 1))",
        "}",
        "plot_if v_sum > 1",
        "color min(v_sum * 15, 95)",
        "opacity 75",
    ]
    prog = compile_field_program("my_blobs", body)
    assert prog.mode == "formula"
    assert prog.value_result == "v_sum"
    assert prog.sites_x == "v_pos_x"


def test_laplace_numpy():
    from pixil_utils.grid_engine import _laplacian_4

    field = np.array([0, 0, 0, 1], dtype=np.float64)
    lap = _laplacian_4(field, 2, "clamp")
    assert lap.shape == (4,)
    assert lap[3] == -2.0


def test_compile_voronoi_field_program():
    body = [
        "size 64",
        "sites v_px, v_py",
        "mode voronoi",
        "site_colors v_colors",
        "edges true",
        "edge_ratio 1.05",
    ]
    prog = compile_field_program("voronoi_anim", body)
    assert prog.mode == "voronoi"
    assert prog.edges is True
