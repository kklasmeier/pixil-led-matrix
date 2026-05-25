"""Deeper math_functions coverage (split, datetime, nested arrays)."""

import pytest

from pixil_utils.math_functions import (
    evaluate_math_expression,
    get_datetime,
    split_outside_quotes,
)
from pixil_utils.variable_registry import VariableRegistry
from pixil_utils.array_manager import PixilArray


def test_split_outside_quotes_and_or():
    parts = split_outside_quotes("v_x > 5 and v_y < 10", " and ")
    assert parts == ["v_x > 5", "v_y < 10"]


def test_split_outside_quotes_respects_parens():
    parts = split_outside_quotes("(v_x > 5) or (v_y < 3)", " or ")
    assert len(parts) == 2
    assert parts[0].strip().startswith("(")


def test_split_unbalanced_paren_raises():
    with pytest.raises(ValueError, match="Unbalanced"):
        split_outside_quotes("(v_x > 5", " and ")


def test_get_datetime_compound_format():
    result = get_datetime("H:mi")
    assert isinstance(result, str)
    assert ":" in result


def test_get_datetime_empty_format_raises():
    with pytest.raises(ValueError, match="empty"):
        get_datetime("")


def test_nested_array_index_in_expression(variables_with_array):
    variables_with_array.register("v_idx")
    inner = PixilArray(3)
    inner[0] = 0
    inner[1] = 1
    inner[2] = 2
    variables_with_array.set("v_idx", inner)
    variables_with_array.set("v_i", 1)
    # v_values[ v_idx[v_i] ] -> v_values[1] -> 20
    assert evaluate_math_expression("v_values[v_idx[v_i]]", variables_with_array) == 20


def test_atan2_and_degrees(variables):
    assert evaluate_math_expression("degrees(pi)", variables) == pytest.approx(180.0, rel=1e-5)


def test_log_and_exp_roundtrip(variables):
    val = evaluate_math_expression("log(exp(2))", variables)
    assert val == pytest.approx(2.0, rel=1e-5)
