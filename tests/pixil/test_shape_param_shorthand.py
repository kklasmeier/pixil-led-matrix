"""Legacy draw_* commands that omit intensity before filled/burnout."""

from pixil_utils.expression_parser import format_parameter
from pixil_utils.parameter_types import expand_legacy_shape_params
from pixil_utils.variable_registry import VariableRegistry


def test_expand_rectangle_inserts_intensity():
    raw = ["5", "5", "20", "20", "green", "true", "5"]
    expanded = expand_legacy_shape_params("draw_rectangle", raw)
    assert expanded == ["5", "5", "20", "20", "green", "100", "true", "5"]


def test_expand_circle_inserts_intensity():
    raw = ["15", "15", "5", "yellow", "false", "3"]
    expanded = expand_legacy_shape_params("draw_circle", raw)
    assert expanded == ["15", "15", "5", "yellow", "100", "false", "3"]


def test_expand_skips_when_intensity_present():
    raw = ["10", "10", "20", "15", "green", "50", "true"]
    assert expand_legacy_shape_params("draw_rectangle", raw) == raw


def test_format_filled_after_expand():
    reg = VariableRegistry()
    args = expand_legacy_shape_params(
        "draw_rectangle", ["5", "5", "20", "20", "green", "true", "5"]
    )
    formatted = [
        format_parameter(arg, "draw_rectangle", pos, reg)
        for pos, arg in enumerate(args)
    ]
    assert formatted[5] == "100"
    assert formatted[6] == "true"
    assert float(formatted[7]) == 5.0
