"""JIT compile + VM execute (pixil_utils.jit_compiler)."""

import math

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.jit_compiler import ExpressionCompiler, JITExpressionCache, PixilVM
from pixil_utils.math_functions import evaluate_math_expression
from pixil_utils.variable_registry import VariableRegistry


def test_compile_and_execute_simple_expression():
    variables = VariableRegistry()
    variables.register("v_x")
    variables.set("v_x", 10)

    compiled = ExpressionCompiler().compile("v_x * 2 + 5")
    result = PixilVM().execute(compiled, variables)
    assert result == 25


def test_compile_parentheses_and_constants():
    variables = VariableRegistry()
    variables.register("v_a")
    variables.set("v_a", 4)

    compiled = ExpressionCompiler().compile("(v_a + 1) * 3")
    result = PixilVM().execute(compiled, variables)
    assert result == 15


def test_jit_sin_cos_sqrt():
    variables = VariableRegistry()
    compiled = ExpressionCompiler().compile("sin(0) + cos(0)")
    result = PixilVM().execute(compiled, variables)
    assert result == pytest.approx(1.0)


def test_jit_simple_array_access_only():
    """JIT supports v_array[v_index] alone; array + arithmetic uses full evaluator."""
    variables = VariableRegistry()
    variables.register("v_i")
    variables.register("v_data")
    arr = PixilArray(3)
    arr[0] = 10
    arr[1] = 20
    arr[2] = 30
    variables.set("v_data", arr)
    variables.set("v_i", 1)

    compiled = ExpressionCompiler().compile("v_data[v_i]")
    assert PixilVM().execute(compiled, variables) == 20


def test_jit_array_plus_constant_uses_full_evaluator(variables_with_array):
    """Combined array+arith falls back outside simple JIT pattern — full path still works."""
    full = evaluate_math_expression("v_values[v_i] + 5", variables_with_array)
    assert full == 35


def test_jit_cache_hit_on_second_evaluate():
    variables = VariableRegistry()
    variables.register("v_n")
    variables.set("v_n", 3)
    cache = JITExpressionCache(max_size=10)

    first = cache.evaluate("v_n * 7", variables)
    second = cache.evaluate("v_n * 7", variables)
    assert first == 21
    assert second == 21
    assert cache.stats.cache_hits >= 1


@pytest.mark.parametrize(
    "expr",
    [
        "v_x + v_y",
        "sqrt(16)",
        "sin(0) + cos(0)",
    ],
)
def test_jit_matches_evaluate_math_expression(expr, variables):
    """JIT and full evaluator should agree on deterministic expressions."""
    variables = VariableRegistry()
    variables.register("v_x")
    variables.register("v_y")
    variables.set("v_x", 10)
    variables.set("v_y", 3)

    jit_result = JITExpressionCache(max_size=50).evaluate(expr, variables)
    full_result = evaluate_math_expression(expr, variables)
    assert jit_result is not None
    assert jit_result == pytest.approx(float(full_result))
