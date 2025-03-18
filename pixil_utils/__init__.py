"""
Utility functions for Pixil script interpreter.
Provides debug, math functionality, and file management while maintaining Pixil's core state management.
"""

from .debug import DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE, DEBUG_LEVEL, debug_print, set_debug_level
from .math_functions import MATH_FUNCTIONS, random_float, has_math_expression, substitute_variables, evaluate_math_expression
from .file_manager import PixilFileManager
from .parameter_types import PARAMETER_TYPES, get_parameter_type, convert_to_type, validate_command_params
from .expression_parser import format_parameter
from .script_manager import ScriptManager
from .timer_manager import (initialize_timer, is_time_expired, clear_timer, 
                          get_remaining_time, force_timer_expired)
from .cli import validate_time_format, validate_debug_level, parse_args
from .array_manager import PixilArray
from .terminal_handler import (initialize_terminal, start_terminal, 
                             stop_terminal, check_spacebar)

__version__ = '0.1.0'

__all__ = [
    'DEBUG_OFF',
    'DEBUG_CONCISE',
    'DEBUG_SUMMARY', 
    'DEBUG_VERBOSE',
    'DEBUG_LEVEL',
    'debug_print',
    'set_debug_level',
    'MATH_FUNCTIONS',
    'random_float',
    'has_math_expression',
    'substitute_variables',
    'evaluate_math_expression',
    'PixilFileManager',
    'ScriptManager',
    # Parameter type handling
    'PARAMETER_TYPES',
    'get_parameter_type',
    'convert_to_type',
    'validate_command_params',
    # Expression parsing
    'format_parameter',
    # Timer management
    'initialize_timer',
    'is_time_expired',
    'clear_timer',
    'get_remaining_time',
    'force_timer_expired',
    # cli
    'validate_time_format', 
    'validate_debug_level',
    'parse_args',  
    # array handling
    'PixilArray',
    # terminal handling
    'initialize_terminal',
    'start_terminal', 
    'stop_terminal',
    'check_spacebar',
]