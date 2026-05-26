"""Tests for pixil_utils.param_bounds clamp-and-warn behavior."""

import pytest

from pixil_utils.param_bounds import (
    BURNOUT_PERMANENT,
    THROTTLE_MIN,
    clamp_burnout_duration,
    clamp_intensity,
    clamp_spectral_color,
    clamp_throttle,
)
from pixil_utils.expression_parser import format_parameter
from pixil_utils.variable_registry import VariableRegistry


def test_clamp_intensity_high_and_low(capsys):
    assert clamp_intensity(105) == 100
    assert clamp_intensity(-3) == 0
    out = capsys.readouterr().out
    assert "WARN" in out
    assert "105" in out
    assert "-3" in out


def test_clamp_intensity_no_warn_when_in_range(capsys):
    assert clamp_intensity(50, warn=False) == 50
    assert capsys.readouterr().out == ""


def test_clamp_spectral_color_high_and_low(capsys):
    assert clamp_spectral_color(112) == 99
    assert clamp_spectral_color(-1) == 0
    out = capsys.readouterr().out
    assert "WARN" in out
    assert "112" in out


def test_clamp_burnout_preserves_permanent(capsys):
    assert clamp_burnout_duration(-1) == BURNOUT_PERMANENT
    assert capsys.readouterr().out == ""


def test_clamp_burnout_negative_not_permanent(capsys):
    assert clamp_burnout_duration(-200) == 0
    out = capsys.readouterr().out
    assert "WARN" in out
    assert "-200" in out


def test_clamp_burnout_positive_unchanged(capsys):
    assert clamp_burnout_duration(1500) == 1500
    assert capsys.readouterr().out == ""


def test_clamp_throttle_low_side(capsys):
    assert clamp_throttle(0) == THROTTLE_MIN
    assert clamp_throttle(-2) == THROTTLE_MIN
    out = capsys.readouterr().out
    assert "WARN" in out
    assert "throttle" in out


def test_clamp_throttle_high_unchanged(capsys):
    assert clamp_throttle(2.5) == 2.5
    assert capsys.readouterr().out == ""


def test_format_parameter_plot_intensity_clamps_expression(capsys):
    reg = VariableRegistry()
    reg.register("v_boost")
    reg.set("v_boost", 15)
    result = format_parameter("90 + v_boost", "plot", 3, reg)
    assert result == "100"
    assert "WARN" in capsys.readouterr().out


def test_format_parameter_plot_preserves_six_args_when_intensity_clamps(capsys):
    """Regression: out-of-range intensity must not drop args (fade -> burnout bug)."""
    reg = VariableRegistry()
    reg.register("v_boost")
    reg.set("v_boost", 15)
    raw_args = ["32", "32", "red", "90 + v_boost", "100", "fade"]
    formatted = [
        format_parameter(arg, "plot", position, reg)
        for position, arg in enumerate(raw_args)
    ]
    assert len(formatted) == 6
    assert formatted[3] == "100"
    assert formatted[4] == "100"
    assert formatted[5] == "fade"
    capsys.readouterr()


def test_format_parameter_plot_numeric_color_clamps(capsys):
    reg = VariableRegistry()
    result = format_parameter("105", "plot", 2, reg)
    assert result == "99"
    assert "WARN" in capsys.readouterr().out


def test_format_parameter_plot_literal_intensity_clamps(capsys):
    reg = VariableRegistry()
    assert format_parameter("200", "plot", 3, reg) == "100"
    assert "WARN" in capsys.readouterr().out


def test_format_parameter_burnout_duration_clamps(capsys):
    reg = VariableRegistry()
    assert format_parameter("-50", "plot", 4, reg) == "0"
    assert "WARN" in capsys.readouterr().out


def test_format_parameter_rest_duration_not_burnout_clamped(capsys):
    reg = VariableRegistry()
    assert format_parameter("-0.5", "rest", 0, reg) == "-0.5"
    assert "WARN" not in capsys.readouterr().out


def test_command_queue_set_throttle_clamps(capsys):
    from shared.command_queue import MatrixCommandQueue

    q = MatrixCommandQueue()
    q.set_throttle(0)
    assert q.throttle_factor == THROTTLE_MIN
    assert "WARN" in capsys.readouterr().out
