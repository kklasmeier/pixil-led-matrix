"""Fast math paths for v_a[v_i] op v_b[v_j] and related particle-loop patterns."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.math_functions import (
    evaluate_math_expression,
    try_fast_array_arithmetic,
    try_fast_array_access,
    try_fast_int_var_div,
    try_fast_arithmetic,
)
from pixil_utils.variable_registry import VariableRegistry


@pytest.fixture
def particle_vars():
    """Minimal particle + field arrays matching flow-field scripts."""
    reg = VariableRegistry()
    for name in (
        "v_p", "v_fidx", "v_x", "v_y", "v_cx", "v_cy", "v_max_age",
    ):
        reg.register(name)

    px = PixilArray(80)
    py = PixilArray(80)
    age = PixilArray(80)
    fvx = PixilArray(64)
    fvy = PixilArray(64)
    pal = PixilArray(8, "string")

    px[0] = 3200
    py[0] = 4100
    age[0] = 10
    fvx[10] = 90
    fvy[10] = 45
    pal[3] = "cyan"

    reg.register("v_px")
    reg.register("v_py")
    reg.register("v_age")
    reg.register("v_field_vx")
    reg.register("v_field_vy")
    reg.register("v_pal")
    reg.register("v_cidx")

    reg.set("v_px", px)
    reg.set("v_py", py)
    reg.set("v_age", age)
    reg.set("v_field_vx", fvx)
    reg.set("v_field_vy", fvy)
    reg.set("v_pal", pal)
    reg.set("v_p", 0)
    reg.set("v_fidx", 10)
    reg.set("v_x", 32.0)
    reg.set("v_y", 41.0)
    reg.set("v_cx", 4)
    reg.set("v_cy", 5)
    reg.set("v_max_age", 200)
    reg.set("v_cidx", 3)
    return reg


def test_array_plus_array(particle_vars):
    assert try_fast_array_arithmetic(
        "v_px[v_p] + v_field_vx[v_fidx]", particle_vars
    ) == 3290.0
    assert evaluate_math_expression(
        "v_px[v_p] + v_field_vx[v_fidx]", particle_vars
    ) == 3290.0


def test_array_plus_one(particle_vars):
    assert try_fast_array_arithmetic("v_age[v_p] + 1", particle_vars) == 11.0


def test_array_div_hundred(particle_vars):
    assert try_fast_array_arithmetic("v_px[v_p] / 100", particle_vars) == 32.0
    assert try_fast_array_arithmetic("v_py[v_p] / 100", particle_vars) == 41.0


def test_field_index_mul_add(particle_vars):
    assert try_fast_arithmetic("v_cy * 8 + v_cx", particle_vars) == 44.0


def test_int_var_div(particle_vars):
    assert try_fast_int_var_div("int(v_x / 8)", particle_vars) == 4
    assert evaluate_math_expression("int(v_x / 8)", particle_vars) == 4


def test_age_brightness_expr(particle_vars):
    assert try_fast_array_arithmetic(
        "v_age[v_p] * 50 / v_max_age", particle_vars
    ) == pytest.approx(2.5)
    assert try_fast_array_arithmetic(
        "100 - v_age[v_p] * 50 / v_max_age", particle_vars
    ) == pytest.approx(97.5)


def test_array_access_still_works(particle_vars):
    assert evaluate_math_expression("v_pal[v_cidx]", particle_vars) == "cyan"


def test_fast_array_index_literal_offset():
    reg = VariableRegistry()
    reg.register("v_idx")
    reg.register("v_u")
    arr = PixilArray(4)
    arr[0] = 1.0
    arr[1] = 2.0
    arr[2] = 3.0
    reg.set("v_u", arr)
    reg.set("v_idx", 2)

    assert try_fast_array_access("v_u[v_idx - 1]", reg) == 2.0
    assert try_fast_array_access("v_u[v_idx + 1]", reg) == 0.0
    assert evaluate_math_expression("v_u[v_idx - 1]", reg) == 2.0


def test_fast_array_index_var_stride_offset():
    reg = VariableRegistry()
    for name in ("v_idx", "v_size", "v_u"):
        reg.register(name)
    arr = PixilArray(9)
    for i in range(9):
        arr[i] = float(i)
    reg.set("v_u", arr)
    reg.set("v_idx", 5)
    reg.set("v_size", 3)

    assert try_fast_array_access("v_u[v_idx - v_size]", reg) == 2.0
    assert try_fast_array_access("v_u[v_idx + v_size]", reg) == 8.0
    assert evaluate_math_expression("v_u[v_idx - v_size]", reg) == 2.0
