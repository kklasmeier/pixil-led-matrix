"""String concat and datetime helpers (pixil_utils.math_functions)."""

import time

import pytest

from pixil_utils.math_functions import (
    evaluate_string_concatenation,
    get_datetime,
    get_system,
    set_script_start_time,
)
from pixil_utils.variable_registry import VariableRegistry


def test_string_concat_literals_and_variables(variables):
    variables.register("v_label")
    variables.set("v_label", "Score")
    result = evaluate_string_concatenation('"Hi "& v_label & ": 10"', variables)
    assert result == "Hi Score: 10"


def test_string_concat_with_array(variables_with_array):
    result = evaluate_string_concatenation('"val="& v_values[v_i]', variables_with_array)
    assert result == "val=30.0"  # numeric array elements are floats


def test_get_datetime_single_codes():
    hour = get_datetime("H")
    assert isinstance(hour, int)
    assert 0 <= hour <= 23
    assert isinstance(get_datetime("mi"), int)
    assert 0 <= get_datetime("mi") <= 59


def test_get_datetime_empty_format_raises():
    with pytest.raises(ValueError, match="empty"):
        get_datetime("")


def test_get_system_runtime():
    set_script_start_time(time.time() - 2.0)
    runtime = get_system("runtime")
    assert isinstance(runtime, int)
    assert runtime >= 1


def test_get_system_unknown_metric():
    with pytest.raises(ValueError, match="Unknown system metric"):
        get_system("not_a_metric")
