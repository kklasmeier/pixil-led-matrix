"""Invalid parameter and conversion errors (pixil_utils.parameter_types)."""

import pytest

from pixil_utils.parameter_types import (
    convert_to_type,
    validate_command_params,
)


def test_plot_too_few_params():
    with pytest.raises(ValueError, match="at least"):
        validate_command_params("plot", "10, 20")


def test_plot_too_many_params():
    extra = "10, 20, red, 50, 1.0, instant, extra"
    with pytest.raises(ValueError, match="at most"):
        validate_command_params("plot", extra)


def test_draw_circle_missing_required_filled():
    with pytest.raises(ValueError, match="at least"):
        validate_command_params("draw_circle", "10, 20, 5, red")


def test_convert_to_type_invalid_int():
    with pytest.raises(ValueError, match="Cannot convert"):
        convert_to_type("not_a_number", "int")


def test_convert_to_type_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported target type"):
        convert_to_type("1", "nope")  # type: ignore[arg-type]


def test_validate_optional_rest_accepts_single_param():
    params = validate_command_params("rest", "0.5")
    assert params == ["0.5"]


def test_validate_draw_text_requires_six():
    raw = '10, 20, "Hi", tiny64_font, 8, white'
    params = validate_command_params("draw_text", raw)
    assert len(params) == 6


def test_mplot_accepts_minimal_three():
    params = validate_command_params("mplot", "0, 0, red")
    assert len(params) == 3
