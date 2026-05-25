"""PixilArray and array access (pixil_utils.array_manager)."""

import pytest

from pixil_utils.array_manager import PixilArray, validate_array_access
from pixil_utils.variable_registry import VariableRegistry


def test_numeric_array_get_set():
    arr = PixilArray(3)
    arr[0] = 1
    arr[1] = 2.5
    arr[2] = 3
    assert arr[0] == 1
    assert arr[1] == 2.5
    assert arr[2] == 3


def test_string_array_strips_quotes_and_escapes():
    arr = PixilArray(1, array_type="string")
    arr[0] = '"hello\\nworld"'
    assert arr[0] == "hello\nworld"


def test_index_out_of_bounds():
    arr = PixilArray(2)
    with pytest.raises(IndexError):
        _ = arr[5]


def test_invalid_size():
    with pytest.raises(ValueError, match="positive"):
        PixilArray(0)


def test_validate_array_access_via_registry(variables_with_array):
    assert validate_array_access("v_values", 1, variables_with_array) == 20


def test_validate_array_access_unknown_array(variables):
    with pytest.raises(ValueError, match="not found"):
        validate_array_access("v_nope", 0, variables)
