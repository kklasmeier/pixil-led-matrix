"""Assignment expression semantics (mirrors Pixil.py v_x = expr without line parsing)."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.math_functions import evaluate_math_expression
from pixil_utils.variable_registry import VariableRegistry


def _assign_like_pixil(expr: str, variables: VariableRegistry):
    """Same value resolution as Pixil.py variable assignment block."""
    if expr.startswith('"') and expr.endswith('"'):
        return expr[1:-1]
    if expr.lower() == "true":
        return True
    if expr.lower() == "false":
        return False
    return evaluate_math_expression(expr, variables)


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("10", 10),
        ("3.5", 3.5),
        ('"hello"', "hello"),
        ("true", True),
        ("false", False),
        ("v_x + v_y", 15),
        ("(v_x - 2) * (v_y + 1)", 48),
        ('"Hi "& v_label', "Hi Score"),
    ],
)
def test_assignment_expression_values(variables, expr, expected):
    variables.register("v_label")
    variables.set("v_label", "Score")
    result = _assign_like_pixil(expr, variables)
    if isinstance(expected, float) and isinstance(result, float):
        assert result == pytest.approx(expected)
    else:
        assert result == expected


def test_assignment_updates_registry(variables):
    variables.register("v_result")
    variables.set("v_result", _assign_like_pixil("v_x * 2", variables))
    assert variables.get("v_result") == 20


def test_assignment_array_index_expression(variables_with_array):
    assert _assign_like_pixil("v_values[v_i]", variables_with_array) == 30


def test_create_array_size_from_expression(variables):
    """create_array(v_grid, v_size * v_size) — size expr only (Tier 1)."""
    variables.register("v_size")
    variables.set("v_size", 4)
    size = evaluate_math_expression("v_size * v_size", variables)
    arr = PixilArray(int(size))
    assert arr.size == 16
    arr[0] = 1
    arr[15] = 2
    assert arr[0] == 1
    assert arr[15] == 2


def test_create_array_explicit_numeric_type():
    arr = PixilArray(8, array_type="numeric")
    arr[0] = 42
    assert arr.get_type() == "numeric"
    assert arr[0] == 42


def test_flat_index_expression_in_assignment(variables):
    """v_idx = v_y * v_size + v_x (game-of-life indexing)."""
    variables.register("v_size")
    variables.register("v_x")
    variables.register("v_y")
    variables.register("v_idx")
    variables.set("v_size", 4)
    variables.set("v_x", 2)
    variables.set("v_y", 3)
    variables.set("v_idx", evaluate_math_expression("v_y * v_size + v_x", variables))
    assert variables.get("v_idx") == 14


def test_numeric_array_assign_via_math(variables_with_array):
    variables_with_array.set("v_i", 0)
    value = evaluate_math_expression("v_values[v_i] + 5", variables_with_array)
    variables_with_array.fast_array_assign("v_values", "v_i", value)
    assert variables_with_array.fast_array_access("v_values", "v_i") == 15


def test_string_array_stores_unquoted_content():
    arr = PixilArray(2, array_type="string")
    arr[0] = '"red"'
    arr[1] = "plain"
    assert arr[0] == "red"
    assert arr[1] == "plain"
