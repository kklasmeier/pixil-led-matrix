"""Full vs fast condition evaluation parity (condition_templates enabled in production)."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.condition_templates import clear_condition_cache, evaluate_condition_fast
from pixil_utils.math_functions import evaluate_condition, evaluate_simple_condition

from tests.pixil._condition_cases import CONDITION_WITH_SETUP, LEGACY_CONDITION_CASES


@pytest.mark.parametrize("condition,expected", LEGACY_CONDITION_CASES)
def test_evaluate_condition_legacy_port(legacy_condition_vars, condition, expected):
    assert evaluate_condition(condition, legacy_condition_vars) is expected


@pytest.mark.parametrize("condition,expected", LEGACY_CONDITION_CASES)
def test_fast_path_agrees_with_full_when_template_applies(legacy_condition_vars, condition, expected):
    clear_condition_cache()
    fast = evaluate_condition_fast(condition, legacy_condition_vars)
    full = evaluate_condition(condition, legacy_condition_vars)
    if fast is not None:
        assert fast is full, condition
    else:
        assert full is expected


@pytest.mark.parametrize("condition,expected,setup", CONDITION_WITH_SETUP)
def test_condition_with_extra_variables(legacy_condition_vars, condition, expected, setup):
    for name, value in setup.items():
        legacy_condition_vars.register(name)
        legacy_condition_vars.set(name, value)
    assert evaluate_condition(condition, legacy_condition_vars) is expected


def test_array_rhs_in_parentheses_matches_lissajous_regression():
    variables = legacy_condition_vars_for_lissajous(19, 0)
    condition = "v_current_color >= (v_color_starts[v_range_index] + 20)"
    assert evaluate_condition(condition, variables) is False
    assert evaluate_condition_fast(condition, variables) is False

    variables.set("v_current_color", 20)
    assert evaluate_condition(condition, variables) is True
    assert evaluate_condition_fast(condition, variables) is True


def test_string_gt_operator_rejected(legacy_condition_vars):
    legacy_condition_vars.register("v_color")
    legacy_condition_vars.set("v_color", "red")
    with pytest.raises(ValueError, match="not supported for string"):
        evaluate_simple_condition('v_color > "blue"', legacy_condition_vars)


def test_unbalanced_paren_in_compound_condition(legacy_condition_vars):
    with pytest.raises(ValueError, match="Unbalanced"):
        evaluate_condition("(v_x > 5 and v_y < 10", legacy_condition_vars)


def test_unterminated_string_in_condition(legacy_condition_vars):
    # Broken quoted RHS may surface as split_outside_quotes or eval fallback error
    with pytest.raises(ValueError, match="Unterminated string|unterminated string|Error evaluating"):
        evaluate_condition('v_x > 5 and "broken', legacy_condition_vars)


def test_undefined_array_in_condition(legacy_condition_vars):
    with pytest.raises(ValueError, match="v_undefined_array"):
        evaluate_condition("v_undefined_array[0] == 5", legacy_condition_vars)


def test_array_index_out_of_bounds_in_condition(legacy_condition_vars):
    legacy_condition_vars.register("v_numbers")
    arr = PixilArray(3)
    for i, v in enumerate([1, 2, 3]):
        arr[i] = v
    legacy_condition_vars.set("v_numbers", arr)
    with pytest.raises(ValueError, match="out of bounds|Array index"):
        evaluate_condition("v_numbers[10] == 5", legacy_condition_vars)


def legacy_condition_vars_for_lissajous(current_color: float, range_index: int):
    from pixil_utils.variable_registry import VariableRegistry

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
