"""
Expression parser for Pixil script interpreter.
Coordinates between math evaluation and parameter type handling.
"""
import re   
from typing import Dict, Any, Union
from .variable_registry import VariableRegistry
from .debug import (DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE, DEBUG_LEVEL, set_debug_level, debug_print)
from .math_functions import has_math_expression, evaluate_math_expression
from .parameter_types import PARAMETER_TYPES, PARAM_INFO_LOOKUP, get_parameter_type, convert_to_type

def validate_color_value(value: Union[str, int, float]) -> int:
    """Validate a numeric value is within 0-100, rounding floats."""
    try:
        if isinstance(value, float):
            value = round(value)
        num = int(value)
        if not 0 <= num <= 100:
            raise ValueError(f"Value {num} must be between 0 and 99")
        return num
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert {value} to valid integer")

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
        
    # Replace backslashes first to avoid double-escaping
    result = s.replace('\\', '\\\\')
    # Then escape quotes
    result = result.replace('"', '\\"')
    return result

def format_parameter(value: Any, command: str, position: int, variables: Union[Dict[str, Any], VariableRegistry]) -> str:
    """Format parameter value for command string construction."""
    try:
        target_type, is_optional = PARAM_INFO_LOOKUP[command][position]
        param_name = PARAMETER_TYPES[command][position]['name']
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Formatting parameter: {value} (type: {target_type}, name: {param_name})", DEBUG_VERBOSE)

        # Special handling for text content in draw_text command
        # This is the key change that addresses the variable resolution issue
        if command == 'draw_text' and position == 2 and target_type == 'str':
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Special handling for draw_text text content: {value}", DEBUG_VERBOSE)
            
            # If it's already a quoted string, return as is
            if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                return value
                
            # For non-string values (like numbers), convert to string and quote
            if not isinstance(value, str):
                return f'"{str(value)}"'
                
            # For variables, evaluate them first
            if isinstance(value, str) and value.startswith('v_'):
                if value in variables:
                    var_value = variables[value]
                    return f'"{str(var_value)}"'
                
            # For expressions, evaluate then quote
            if isinstance(value, str) and has_math_expression(value):
                try:
                    result = evaluate_math_expression(value, variables)
                    return f'"{str(result)}"'
                except Exception as e:
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Error evaluating expression for text: {e}", DEBUG_VERBOSE)
            
            # For any other string, simply quote it
            return f'"{value}"'

        # Rest of the function remains the same as in the older version
        # Handle direct quoted strings
        if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Converted to str: {value}", DEBUG_VERBOSE)
            if target_type != 'str':
                # Strip quotes for non-string types
                stripped = value[1:-1]
                converted = convert_to_type(stripped, target_type)
                return str(converted) if target_type != 'bool' else str(converted).lower()
            return value
            
        # Handle math expressions or variables
        if isinstance(value, str) and (has_math_expression(value) or value.startswith('v_')):
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Processing expression/variable: {value}", DEBUG_VERBOSE)
            try:
                result = evaluate_math_expression(value, variables)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Evaluated result: {result}", DEBUG_VERBOSE)
                if target_type == 'color':
                    if isinstance(result, (int, float)):
                        return str(validate_color_value(result))
                    return str(result)
                if target_type == 'int' and param_name == 'intensity':
                    return str(validate_color_value(result))
                converted = convert_to_type(result, target_type)
                return str(converted) if target_type != 'bool' else str(converted).lower()
            except ValueError as e:
                if is_optional:
                    return ''
                raise
                
        # Direct values
        if target_type == 'color':
            if isinstance(value, (int, float)):
                return str(validate_color_value(value))
            return str(value)
        if target_type == 'int' and param_name == 'intensity':
            return str(validate_color_value(value))
        converted = convert_to_type(value, target_type)
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Converted to {target_type}: {converted}", DEBUG_VERBOSE)
        return str(converted) if target_type != 'bool' else str(converted).lower()
    except Exception as e:
        raise ValueError(f"Error formatting parameter '{value}' for {command} position {position}: {str(e)}")
                
__all__ = ['format_parameter']