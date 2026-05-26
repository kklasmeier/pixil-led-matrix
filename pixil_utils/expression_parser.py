"""
Expression parser for Pixil script interpreter.
Coordinates between math evaluation and parameter type handling.
"""
from typing import Any, Union, Dict

from .variable_registry import VariableRegistry
from .debug import DEBUG_VERBOSE, DEBUG_LEVEL, debug_print
from .math_functions import has_math_expression, evaluate_math_expression
from .parameter_types import PARAMETER_TYPES, PARAM_INFO_LOOKUP, convert_to_type
from .param_bounds import (
    clamp_intensity,
    clamp_spectral_color,
    clamp_burnout_duration,
    format_burnout_for_command,
    is_burnout_duration_param,
    is_numeric_literal,
)


def validate_color_value(value: Union[str, int, float]) -> int:
    """Clamp intensity to 0-100 (legacy name; prefer clamp_intensity)."""
    return clamp_intensity(value, warn=False)


def escape_string(s: str) -> str:
    """
    Escape special characters in a string for use in commands.

    Args:
        s: The string to escape

    Returns:
        Escaped string with proper backslash sequences
    """
    if not isinstance(s, str):
        return s

    result = s.replace('\\', '\\\\')
    result = result.replace('"', '\\"')
    return result


def format_numeric_for_display(value: Any) -> str:
    """
    Format a numeric value for text display.
    Converts whole-number floats to integers for cleaner display.
    """
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def _format_resolved_value(
    result: Any,
    command: str,
    param_name: str,
    target_type: str,
) -> str:
    if param_name == "intensity":
        return str(clamp_intensity(result, command=command, param_name=param_name))
    if target_type == "color" and isinstance(result, (int, float)):
        return str(clamp_spectral_color(result, command=command, param_name=param_name))
    if is_burnout_duration_param(command, param_name) and isinstance(result, (int, float)):
        clamped = clamp_burnout_duration(result, command=command, param_name=param_name)
        return format_burnout_for_command(clamped)
    if target_type == "color":
        return str(result)
    converted = convert_to_type(result, target_type)
    return str(converted) if target_type != "bool" else str(converted).lower()


def _format_direct_value(
    value: Any,
    command: str,
    param_name: str,
    target_type: str,
) -> str:
    if param_name == "intensity":
        return str(clamp_intensity(value, command=command, param_name=param_name))
    if target_type == "color" and isinstance(value, (int, float)):
        return str(clamp_spectral_color(value, command=command, param_name=param_name))
    if is_burnout_duration_param(command, param_name) and is_numeric_literal(value):
        clamped = clamp_burnout_duration(value, command=command, param_name=param_name)
        return format_burnout_for_command(clamped)
    if target_type == "color" and is_numeric_literal(value):
        return str(clamp_spectral_color(value, command=command, param_name=param_name))
    if target_type == "color":
        return str(value)
    converted = convert_to_type(value, target_type)
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Converted to {target_type}: {converted}", DEBUG_VERBOSE)
    return str(converted) if target_type != "bool" else str(converted).lower()


def format_parameter(
    value: Any,
    command: str,
    position: int,
    variables: Union[Dict[str, Any], VariableRegistry],
) -> str:
    """Format parameter value for command string construction."""
    try:
        target_type, _is_optional = PARAM_INFO_LOOKUP[command][position]
        param_name = PARAMETER_TYPES[command][position]["name"]
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(
                f"Formatting parameter: {value} (type: {target_type}, name: {param_name})",
                DEBUG_VERBOSE,
            )

        if command == "draw_text" and position == 2 and target_type == "str":
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Special handling for draw_text text content: {value}", DEBUG_VERBOSE)

            if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                return value

            if not isinstance(value, str):
                return f'"{format_numeric_for_display(value)}"'

            if isinstance(value, str) and value.startswith("v_"):
                if value in variables:
                    var_value = variables[value]
                    return f'"{format_numeric_for_display(var_value)}"'

            if isinstance(value, str) and has_math_expression(value):
                try:
                    result = evaluate_math_expression(value, variables)
                    return f'"{format_numeric_for_display(result)}"'
                except Exception as e:
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Error evaluating expression for text: {e}", DEBUG_VERBOSE)

            return f'"{value}"'

        if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Converted to str: {value}", DEBUG_VERBOSE)
            if target_type != "str":
                stripped = value[1:-1]
                converted = convert_to_type(stripped, target_type)
                if param_name == "intensity":
                    return str(
                        clamp_intensity(converted, command=command, param_name=param_name)
                    )
                if is_burnout_duration_param(command, param_name):
                    clamped = clamp_burnout_duration(
                        converted, command=command, param_name=param_name
                    )
                    return format_burnout_for_command(clamped)
                return str(converted) if target_type != "bool" else str(converted).lower()
            return value

        if isinstance(value, str) and (has_math_expression(value) or value.startswith("v_")):
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Processing expression/variable: {value}", DEBUG_VERBOSE)
            result = evaluate_math_expression(value, variables)
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Evaluated result: {result}", DEBUG_VERBOSE)
            return _format_resolved_value(result, command, param_name, target_type)

        return _format_direct_value(value, command, param_name, target_type)
    except Exception as e:
        raise ValueError(
            f"Error formatting parameter '{value}' for {command} position {position}: {str(e)}"
        )


__all__ = [
    "format_parameter",
    "validate_color_value",
    "escape_string",
    "format_numeric_for_display",
]
