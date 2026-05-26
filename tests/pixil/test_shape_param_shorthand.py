"""Legacy draw_* commands that omit intensity before filled/fill."""

import pytest

from pixil_utils.expression_parser import format_parameter
from pixil_utils.parameter_types import expand_legacy_shape_params
from pixil_utils.variable_registry import VariableRegistry

# (command, legacy args, expected after expand_legacy_shape_params)
LEGACY_EXPAND_CASES = [
    (
        "draw_rectangle",
        ["5", "5", "20", "20", "green", "true", "5"],
        ["5", "5", "20", "20", "green", "100", "true", "5"],
    ),
    (
        "draw_circle",
        ["15", "15", "5", "yellow", "false", "3"],
        ["15", "15", "5", "yellow", "100", "false", "3"],
    ),
    (
        "draw_polygon",
        ["32", "32", "20", "6", "red", "0", "false"],
        ["32", "32", "20", "6", "red", "100", "0", "false"],
    ),
    (
        "draw_ellipse",
        ["16", "16", "10", "8", "blue", "false", "0"],
        ["16", "16", "10", "8", "blue", "100", "false", "0"],
    ),
]

# (command, full documented args) — must not be altered by expand_legacy_shape_params
FULL_FORM_CASES = [
    ("draw_rectangle", ["10", "10", "20", "15", "green", "50", "true", "2"]),
    ("draw_circle", ["15", "15", "5", "yellow", "75", "false", "3"]),
    (
        "draw_polygon",
        ["32", "32", "20", "6", "1", "50", "0", "false"],
    ),
    ("draw_ellipse", ["16", "16", "10", "8", "blue", "80", "true", "45"]),
]


@pytest.mark.parametrize("command,legacy,expected", LEGACY_EXPAND_CASES)
def test_expand_legacy_inserts_default_intensity(command, legacy, expected):
    assert expand_legacy_shape_params(command, list(legacy)) == list(expected)


@pytest.mark.parametrize("command,full_args", FULL_FORM_CASES)
def test_expand_skips_when_intensity_present(command, full_args):
    assert expand_legacy_shape_params(command, list(full_args)) == list(full_args)


INTENSITY_IDX = {
    "draw_rectangle": 5,
    "draw_circle": 4,
    "draw_polygon": 5,
    "draw_ellipse": 5,
}
FILL_IDX = {
    "draw_rectangle": 6,
    "draw_circle": 5,
    "draw_polygon": 7,
    "draw_ellipse": 6,
}


@pytest.mark.parametrize("command,legacy,expected", LEGACY_EXPAND_CASES)
def test_format_parameter_after_legacy_expand(command, legacy, expected):
    """Pixil.py path: expand then format_parameter for each slot."""
    reg = VariableRegistry()
    args = expand_legacy_shape_params(command, list(legacy))
    assert args == list(expected)
    formatted = [format_parameter(arg, command, pos, reg) for pos, arg in enumerate(args)]
    assert formatted[INTENSITY_IDX[command]] == "100"
    assert formatted[FILL_IDX[command]] in ("true", "false")


@pytest.mark.parametrize("command,full_args", FULL_FORM_CASES)
def test_format_parameter_after_full_form_no_expand(command, full_args):
    """Regression: bool filled/fill must not land on float duration/burnout slots."""
    reg = VariableRegistry()
    args = expand_legacy_shape_params(command, list(full_args))
    assert args == list(full_args)
    for pos, arg in enumerate(args):
        format_parameter(arg, command, pos, reg)
    formatted = [format_parameter(arg, command, pos, reg) for pos, arg in enumerate(args)]
    assert formatted[FILL_IDX[command]] in ("true", "false")


def test_format_filled_after_expand_rectangle():
    """Explicit values for legacy rectangle + duration."""
    reg = VariableRegistry()
    args = expand_legacy_shape_params(
        "draw_rectangle", ["5", "5", "20", "20", "green", "true", "5"]
    )
    formatted = [
        format_parameter(arg, "draw_rectangle", pos, reg) for pos, arg in enumerate(args)
    ]
    assert formatted[5] == "100"
    assert formatted[6] == "true"
    assert float(formatted[7]) == 5.0
