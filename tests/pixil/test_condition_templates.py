"""Condition fast-path evaluation (pixil_utils)."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.condition_templates import (
    clear_condition_cache,
    evaluate_condition_fast,
)
from pixil_utils.math_functions import evaluate_condition
from pixil_utils.variable_registry import VariableRegistry


def _make_lissajous_vars(current_color: float, range_index: int):
    """Setup matching Lissajous_Curves.pix color range check."""
    variables = VariableRegistry()
    variables.register("v_current_color")
    variables.register("v_range_index")
    variables.register("v_color_starts")
    variables.set("v_current_color", current_color)
    variables.set("v_range_index", range_index)

    color_starts = PixilArray(5)
    for i, value in enumerate([0, 20, 40, 60, 80]):
        color_starts[i] = value
    variables.set("v_color_starts", color_starts)
    return variables


def test_array_math_rhs_in_parentheses():
    """Regression: Lissajous_Curves.pix color boundary condition."""
    clear_condition_cache()
    condition = "v_current_color >= (v_color_starts[v_range_index] + 20)"

    variables = _make_lissajous_vars(current_color=19, range_index=0)
    assert evaluate_condition_fast(condition, variables) is False

    variables.set("v_current_color", 20)
    assert evaluate_condition_fast(condition, variables) is True

    variables.set("v_current_color", 95)
    variables.set("v_range_index", 4)
    assert evaluate_condition_fast(condition, variables) is False

    variables.set("v_current_color", 100)
    assert evaluate_condition_fast(condition, variables) is True


def test_simple_conditions_still_fast():
    """Ensure basic fast-path compares are unchanged."""
    clear_condition_cache()
    variables = VariableRegistry()
    variables.register("v_x")
    variables.set("v_x", 10)

    assert evaluate_condition_fast("v_x >= 5", variables) is True
    assert evaluate_condition_fast("v_x < 5", variables) is False


@pytest.mark.parametrize(
    "condition,expected",
    [
        ("v_x > 5", True),
        ("v_z == 15", True),
        ("v_x > 5 and v_y < 10", True),
        ("v_x > 100 or v_y < 10", True),
        ("v_a == 1 or v_b == 1 and v_z == 0", True),
        ("v_x > 5 and v_y < 10 and v_z == 15", True),
        ("(v_x > 100) or (v_y < 10)", True),
        ("(v_x > 5) and (v_y < 3)", False),
    ],
)
def test_legacy_conditions_match_script_setup(legacy_condition_vars, condition, expected):
    """Port of scripts/testing/test_parentheses_conditions.pix legacy 1–6 + parens."""
    assert evaluate_condition(condition, legacy_condition_vars) is expected


def test_fast_path_agrees_with_full_evaluator(legacy_condition_vars):
    """Fast templates should match evaluate_condition when template applies."""
    cases = [
        "v_x > 5",
        "v_x > 5 and v_y < 10",
        "v_current_color >= (v_color_starts[v_range_index] + 20)",
    ]
    reg = legacy_condition_vars
    reg.register("v_current_color")
    reg.register("v_range_index")
    reg.register("v_color_starts")
    reg.set("v_current_color", 25)
    reg.set("v_range_index", 1)
    arr = PixilArray(5)
    for i, v in enumerate([0, 20, 40, 60, 80]):
        arr[i] = v
    reg.set("v_color_starts", arr)

    for cond in cases:
        clear_condition_cache()
        fast = evaluate_condition_fast(cond, reg)
        full = evaluate_condition(cond, reg)
        if fast is not None:
            assert fast is full, cond
