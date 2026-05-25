"""Condition evaluation (pixil_utils.math_functions)."""

import pytest

from pixil_utils.math_functions import evaluate_condition, evaluate_simple_condition


def test_simple_comparisons(variables):
    assert evaluate_condition("v_x > 5", variables) is True
    assert evaluate_condition("v_y < 3", variables) is False
    assert evaluate_condition("v_z == 15", variables) is True
    assert evaluate_condition("v_x != 10", variables) is False


def test_literal_true_false(variables):
    assert evaluate_condition("true", variables) is True
    assert evaluate_condition("false", variables) is False


def test_compound_and(variables):
    assert evaluate_condition("v_x > 5 and v_y < 10", variables) is True
    assert evaluate_condition("v_x > 100 and v_y < 10", variables) is False


def test_compound_or(variables):
    assert evaluate_condition("v_x > 100 or v_y < 10", variables) is True
    assert evaluate_condition("v_x > 100 or v_y < 3", variables) is False


def test_and_precedence_over_or(variables):
    # true or (false and false) => true
    assert evaluate_condition("v_a == 1 or v_b == 1 and v_z == 0", variables) is True


def test_parenthesized_group(variables):
    assert evaluate_condition("(v_x > 100) or (v_y < 10)", variables) is True
    assert evaluate_condition("(v_x > 5) and (v_y < 3)", variables) is False


def test_not_prefix(variables):
    assert evaluate_condition("not v_b == 1", variables) is True
    assert evaluate_condition("not v_a == 1", variables) is False


def test_string_equality(variables):
    variables.register("v_name")
    variables.set("v_name", "red")
    assert evaluate_simple_condition('v_name == "red"', variables) is True
    assert evaluate_simple_condition('v_name == "blue"', variables) is False


def test_empty_condition_raises(variables):
    with pytest.raises(ValueError, match="Empty condition"):
        evaluate_condition("", variables)


def test_single_equals_syntax_hint(variables):
    with pytest.raises(ValueError, match="=="):
        evaluate_condition("v_x = 5", variables)


def test_undefined_variable_hint(variables):
    with pytest.raises(ValueError, match="v_xx"):
        evaluate_simple_condition("v_xx > 5", variables)


def test_incomplete_compound_raises(variables):
    # Parser may reject as incomplete or fail evaluating trailing "and" fragment
    with pytest.raises(ValueError):
        evaluate_condition("v_x > 5 and", variables)
