"""
Debug utilities for Pixil script interpreter.
Provides debug level constants and print functionality.
"""

# Debug levels
DEBUG_OFF = 0
DEBUG_CONCISE = 1
DEBUG_SUMMARY = 2
DEBUG_VERBOSE = 3

# Default debug level
DEBUG_LEVEL = DEBUG_VERBOSE

# Global variable for current command
current_command = None  # Tracks the currently executing Pixil command

def set_debug_level(level):
    """Set the debug output level."""
    global DEBUG_LEVEL
    DEBUG_LEVEL = level

def debug_print(message, level=DEBUG_CONCISE, end='\n'):
    """
    Print debug messages based on current debug level.
    Includes the current Pixil command if level >= DEBUG_CONCISE and "error" is in the message.
    
    Args:
        message: The message to print
        level: Debug level of this message
        end: String appended after the message (default newline)
    """
    if DEBUG_LEVEL >= level:
        if (DEBUG_LEVEL >= DEBUG_CONCISE and 
            "error" in message.lower() and 
            current_command is not None):
            full_message = f"{message}\nCommand: {current_command}"
        else:
            full_message = message
        print(full_message, end=end)

# Export symbols
__all__ = [
    'DEBUG_OFF',
    'DEBUG_CONCISE',
    'DEBUG_SUMMARY',
    'DEBUG_VERBOSE',
    'DEBUG_LEVEL',
    'set_debug_level',
    'debug_print',
    'current_command'  # Export so Pixil.py can access it
]