"""Expression parser helpers (pixil_utils.expression_parser)."""

import pytest

from pixil_utils.expression_parser import (
    escape_string,
    format_numeric_for_display,
    format_parameter,
    validate_color_value,
)
from pixil_utils.variable_registry import VariableRegistry


def test_validate_color_value_int_and_round():
    assert validate_color_value(50) == 50
    assert validate_color_value(49.6) == 50


def test_validate_color_value_out_of_range_clamps():
    assert validate_color_value(101) == 100
    assert validate_color_value(-1) == 0


def test_validate_color_value_fractional_string():
    """scripts/testing/test_math.pix uses plot(..., 0.1) for low intensity."""
    assert validate_color_value("0.1") == 0
    assert validate_color_value("99.6") == 100


def test_format_parameter_plot_fractional_intensity():
    reg = VariableRegistry()
    assert format_parameter("0.1", "plot", 3, reg) == "0"


def test_format_numeric_for_display():
    assert format_numeric_for_display(3.0) == "3"
    assert format_numeric_for_display(3.14) == "3.14"


def test_escape_string_quotes():
    assert escape_string('say "hi"') == 'say \\"hi\\"'


def test_format_parameter_plot_intensity_from_expression():
    reg = VariableRegistry()
    reg.register("v_x")
    reg.set("v_x", 75)
    result = format_parameter("v_x", "plot", 3, reg)
    assert result == "75"


def test_format_parameter_draw_text_quoted_passthrough():
    reg = VariableRegistry()
    assert format_parameter('"Hello"', "draw_text", 2, reg) == '"Hello"'


def test_format_parameter_draw_text_variable_resolves():
    reg = VariableRegistry()
    reg.register("v_msg")
    reg.set("v_msg", "Hi")
    assert format_parameter("v_msg", "draw_text", 2, reg) == '"Hi"'


def test_format_parameter_bool_lowercase():
    reg = VariableRegistry()
    assert format_parameter("true", "draw_rectangle", 6, reg) == "true"


def test_format_parameter_invalid_intensity_clamps(capsys):
    reg = VariableRegistry()
    assert format_parameter("200", "plot", 3, reg) == "100"
    assert "WARN" in capsys.readouterr().out


def test_escape_string_non_string_passthrough():
    assert escape_string(42) == 42


def test_format_parameter_strips_quoted_string_for_int_type():
    reg = VariableRegistry()
    assert format_parameter('"10"', "plot", 0, reg) == "10"


def test_format_parameter_draw_text_from_variable():
    reg = VariableRegistry()
    reg.register("v_msg")
    reg.set("v_msg", 42)
    result = format_parameter("v_msg", "draw_text", 2, reg)
    assert result == '"42"'
