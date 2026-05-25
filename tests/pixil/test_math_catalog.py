"""MATH_FUNCTIONS catalog and fast-math paths (production path with JIT off)."""

import math

import pytest

from pixil_utils.math_functions import (
    MATH_FUNCTIONS,
    evaluate_math_expression,
    substitute_variables,
    try_fast_arithmetic,
    try_fast_array_access,
    try_fast_number,
    try_fast_random,
    try_fast_trig,
)
from pixil_utils.variable_registry import VariableRegistry

from tests.pixil._math_cases import FAST_MATH_CASES, MATH_EXPR_CASES


@pytest.mark.parametrize("expr,expected", MATH_EXPR_CASES)
def test_math_functions_catalog(expr, expected, variables):
    result = evaluate_math_expression(expr, variables)
    if isinstance(expected, float):
        assert result == pytest.approx(expected)
    else:
        assert result == expected


@pytest.mark.parametrize("name", sorted(MATH_FUNCTIONS.keys()))
def test_every_math_function_key_is_catalogued_or_builtin(name):
    """Each MATH_FUNCTIONS entry is exercised in MATH_EXPR_CASES or dedicated tests."""
    catalogued = {
        "cos", "sin", "tan", "abs", "pow", "sqrt", "exp", "log", "log10",
        "trunc", "int", "asin", "acos", "atan", "atan2", "degrees", "radians",
        "min", "max", "pi", "e", "tau", "copysign", "fabs", "remainder", "fmod",
    }
    dedicated = {"random", "get_datetime", "get_system", "round", "floor", "ceil"}
    assert name in catalogued | dedicated


@pytest.mark.parametrize("expr,expected", FAST_MATH_CASES)
def test_fast_math_paths(expr, expected, variables):
    assert evaluate_math_expression(expr, variables) == expected


def test_try_fast_number_and_trig():
    assert try_fast_number("99") == 99
    assert try_fast_trig("sin(0)", None) == pytest.approx(0.0)
    assert try_fast_trig("cos(0)", None) == pytest.approx(1.0)


def test_try_fast_random_fixed_bounds(variables):
    assert try_fast_random("random(4, 4, 0)", variables) == 4


def test_try_fast_arithmetic_var_combinations(variables):
    variables.register("v_offset")
    variables.set("v_offset", 2)
    assert try_fast_arithmetic("v_x + v_offset", variables) == 12
    assert try_fast_arithmetic("v_x * v_offset", variables) == 20


def test_substitute_variables_leaves_literals(variables):
    variables.register("v_n")
    variables.set("v_n", 7)
    assert substitute_variables("v_n + 1", variables) == "7 + 1"


def test_substitute_variables_unknown_raises(variables):
    with pytest.raises(ValueError, match="v_missing"):
        substitute_variables("v_missing + 1", variables)


def test_round_floor_ceil_via_evaluator(variables):
    assert evaluate_math_expression("round(2.5)", variables) == 2
    assert evaluate_math_expression("floor(2.9)", variables) == 2
    assert evaluate_math_expression("ceil(2.1)", variables) == 3
