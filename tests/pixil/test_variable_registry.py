"""VariableRegistry (pixil_utils.variable_registry)."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.variable_registry import VariableRegistry


def test_register_get_set():
    reg = VariableRegistry()
    reg.register("v_x")
    reg.set("v_x", 42)
    assert reg.get("v_x") == 42
    assert "v_x" in reg


def test_get_missing_raises():
    reg = VariableRegistry()
    with pytest.raises(KeyError, match="v_missing"):
        reg.get("v_missing")


def test_dict_style_access():
    reg = VariableRegistry()
    reg.register("v_n")
    reg["v_n"] = 7
    assert reg["v_n"] == 7


def test_fast_array_access(variables_with_array):
    assert variables_with_array.fast_array_access("v_values", "v_i") == 30


def test_fast_array_assign(variables_with_array):
    variables_with_array.fast_array_assign("v_values", "v_i", 99)
    assert variables_with_array.fast_array_access("v_values", "v_i") == 99
