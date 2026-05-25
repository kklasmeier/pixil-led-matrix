"""Unit tests for condition template fast-path evaluation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pixil_utils.array_manager import PixilArray
from pixil_utils.condition_templates import evaluate_condition_fast, clear_condition_cache
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


if __name__ == "__main__":
    test_array_math_rhs_in_parentheses()
    test_simple_conditions_still_fast()
    print("All condition template tests passed.")
