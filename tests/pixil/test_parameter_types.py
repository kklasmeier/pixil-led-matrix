"""Command parameter parsing (pixil_utils.parameter_types)."""

import pytest

from pixil_utils.parameter_types import (
    convert_to_type,
    get_parameter_type,
    parse_bool_literal,
    split_command_parameters,
    validate_command_params,
)


def test_split_simple_commas():
    assert split_command_parameters("1, 2, red") == ["1", "2", "red"]


def test_split_nested_function_calls():
    raw = '32, round(10 - random(1, 5, 1), 2), "Hello, World!"'
    assert split_command_parameters(raw) == [
        "32",
        "round(10 - random(1, 5, 1), 2)",
        '"Hello, World!"',
    ]


def test_split_quoted_commas():
    assert split_command_parameters('"a, b", 10') == ['"a, b"', "10"]


def test_convert_to_type_int_float_bool():
    assert convert_to_type("3.7", "int") == 4
    assert convert_to_type("3.7", "float") == 3.7
    assert convert_to_type("true", "bool") is True
    assert convert_to_type("false", "bool") is False


def test_get_parameter_type_plot():
    assert get_parameter_type("plot", 0) == "int"
    assert get_parameter_type("plot", 2) == "color"


def test_validate_command_params_plot_minimal():
    params = validate_command_params("plot", "10, 20, red")
    assert params == ["10", "20", "red"]


def test_validate_command_params_too_few():
    with pytest.raises(ValueError, match="at least"):
        validate_command_params("plot", "10, 20")


def test_validate_command_params_unknown_command():
    with pytest.raises(KeyError, match="Unknown command"):
        validate_command_params("not_a_command", "1")


def test_mflush_accepts_no_params():
    assert validate_command_params("mflush", "") == []


def test_parse_bool_literal_true_false():
    assert parse_bool_literal("true") is True
    assert parse_bool_literal("false") is False
    assert parse_bool_literal(" TRUE ") is True
    assert parse_bool_literal(True) is True
    assert parse_bool_literal(False) is False


def test_parse_bool_literal_rejects_garbage():
    with pytest.raises(ValueError, match="true/false"):
        parse_bool_literal("maybe")
    with pytest.raises(ValueError, match="true/false"):
        parse_bool_literal("")


def test_parse_bool_literal_not_python_bool_string():
    """Document regression: bool('false') is True in Python."""
    assert bool("false") is True
    assert parse_bool_literal("false") is False


def test_get_parameter_type_begin_frame():
    assert get_parameter_type("begin_frame", 0) == "bool"


def test_validate_begin_frame_preserve_argument():
    assert validate_command_params("begin_frame", "false") == ["false"]
    assert validate_command_params("begin_frame", "true") == ["true"]


def test_validate_begin_frame_no_args():
    assert validate_command_params("begin_frame", "") == []
