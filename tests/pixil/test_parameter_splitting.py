"""Command parameter parsing (pixil_utils.parameter_types)."""

from pixil_utils.parameter_types import split_command_parameters


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
