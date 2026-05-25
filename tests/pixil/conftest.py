"""Shared fixtures for pixil_utils unit tests."""

import pytest

from pixil_utils.array_manager import PixilArray
from pixil_utils.math_functions import clear_all_math_caches
from pixil_utils.condition_templates import clear_condition_cache
from pixil_utils.variable_registry import VariableRegistry


@pytest.fixture
def variables():
    reg = VariableRegistry()
    reg.register("v_x")
    reg.register("v_y")
    reg.register("v_z")
    reg.register("v_a")
    reg.register("v_b")
    reg.set("v_x", 10)
    reg.set("v_y", 5)
    reg.set("v_z", 15)
    reg.set("v_a", 1)
    reg.set("v_b", 0)
    return reg


@pytest.fixture
def legacy_condition_vars(variables):
    """Same setup as scripts/testing/test_parentheses_conditions.pix (legacy block)."""
    return variables


@pytest.fixture
def variables_with_array(variables):
    """Registry with v_values numeric array (5 elements)."""
    arr = PixilArray(5)
    for i, val in enumerate([10, 20, 30, 40, 50]):
        arr[i] = val
    variables.register("v_i")
    variables.register("v_values")
    variables.set("v_values", arr)
    variables.set("v_i", 2)
    return variables


@pytest.fixture(autouse=True)
def reset_caches():
    """Isolate tests from global math/JIT/condition caches."""
    clear_all_math_caches()
    clear_condition_cache()
    yield
    clear_all_math_caches()
    clear_condition_cache()
