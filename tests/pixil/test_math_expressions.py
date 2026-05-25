"""Math expression evaluation (pixil_utils.math_functions)."""

import math

import pytest

from pixil_utils.math_functions import (
    evaluate_math_expression,
    has_math_expression,
    try_fast_number,
    try_fast_arithmetic,
    try_fast_array_access,
)
from pixil_utils.variable_registry import VariableRegistry


def test_literal_and_arithmetic(variables):
    assert evaluate_math_expression("2 + 3 * 4", variables) == 14


def test_variable_arithmetic(variables):
    assert evaluate_math_expression("v_x + v_y", variables) == 15


def test_nested_parentheses(variables):
    # v_x=10, v_y=5 -> (8) * (6) = 48
    assert evaluate_math_expression("(v_x - 2) * (v_y + 1)", variables) == 48


def test_modulo_and_division(variables):
    assert evaluate_math_expression("v_x % 3", variables) == 1
    assert evaluate_math_expression("v_x / 4", variables) == 2.5


def test_direct_variable_lookup(variables):
    assert evaluate_math_expression("v_x", variables) == 10


def test_array_index_in_expression(variables_with_array):
    assert evaluate_math_expression("v_values[v_i]", variables_with_array) == 30
    variables_with_array.set("v_i", 0)
    assert evaluate_math_expression("v_values[v_i] + 5", variables_with_array) == 15


def test_trig_and_sqrt(variables):
    assert evaluate_math_expression("sin(0)", variables) == pytest.approx(0.0)
    assert evaluate_math_expression("cos(0)", variables) == pytest.approx(1.0)
    assert evaluate_math_expression("sqrt(16)", variables) == pytest.approx(4.0)


def test_round_floor_ceil(variables):
    assert evaluate_math_expression("round(3.7)", variables) == 4
    assert evaluate_math_expression("floor(3.9)", variables) == 3
    assert evaluate_math_expression("ceil(3.1)", variables) == 4


def test_min_max_pow(variables):
    assert evaluate_math_expression("min(3, 7)", variables) == 3
    assert evaluate_math_expression("max(3, 7)", variables) == 7
    assert evaluate_math_expression("pow(2, 3)", variables) == 8


def test_random_fixed_bounds(variables):
    assert evaluate_math_expression("random(5, 5, 0)", variables) == 5


def test_constants_pi(variables):
    assert evaluate_math_expression("pi", variables) == pytest.approx(math.pi)


def test_fast_number_literal():
    assert try_fast_number("42") == 42
    assert try_fast_number("3.5") == 3.5
    assert try_fast_number("v_x") is None


def test_fast_arithmetic_var_plus_number(variables):
    assert try_fast_arithmetic("v_x + 5", variables) == 15


def test_fast_array_access(variables_with_array):
    assert try_fast_array_access("v_values[v_i]", variables_with_array) == 30


def test_has_math_expression_detects_operators():
    assert has_math_expression("v_x + 1") is True
    # Bare v_ names count as math-ish (may need evaluation)
    assert has_math_expression("v_x") is True
    assert has_math_expression('"hello"') is False
    assert has_math_expression("plain") is False
