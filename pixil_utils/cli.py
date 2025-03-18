"""
Command Line Interface utilities for Pixil script runner.
Handles argument parsing and validation.
"""

import argparse
import re
from pathlib import Path
from .debug import (DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE)

def validate_time_format(time_str):
    """
    Validate time is in mm:ss format.
    
    Args:
        time_str: Time string in mm:ss format (e.g., '2:30')
        
    Returns:
        int: Duration in seconds if valid
        
    Raises:
        argparse.ArgumentTypeError if format is invalid
    """
    if not time_str:
        return None
        
    if not re.match(r'^\d+:[0-5]\d$', time_str):
        raise argparse.ArgumentTypeError('Time must be in mm:ss format (e.g., 2:30)')
        
    minutes, seconds = map(int, time_str.split(':'))
    return (minutes * 60) + seconds

def validate_debug_level(level_str):
    """
    Validate and convert debug level string to integer value.
    
    Args:
        level_str: Debug level name (e.g., 'DEBUG_VERBOSE')
        
    Returns:
        int: Debug level value
        
    Raises:
        argparse.ArgumentTypeError if level is invalid
    """
    valid_levels = {
        'DEBUG_OFF': DEBUG_OFF,
        'DEBUG_CONCISE': DEBUG_CONCISE,
        'DEBUG_SUMMARY': DEBUG_SUMMARY,
        'DEBUG_VERBOSE': DEBUG_VERBOSE
    }
    
    if level_str.upper() not in valid_levels:
        raise argparse.ArgumentTypeError(
            f'Debug level must be one of: {", ".join(valid_levels.keys())}'
        )
    
    return valid_levels[level_str.upper()]

def parse_args():
    """
    Parse and validate command line arguments.
    
    Returns:
        Namespace object with validated arguments:
            - script_path: Path or pattern for script(s)
            - duration: Run duration in seconds (None for unlimited)
            - debug_level: Debug level value (None for default)
    """
    parser = argparse.ArgumentParser(
        description='Pixil LED Matrix Script Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a script from the base directory
  sudo python Pixil.py myscript
  
  # Run a script from a subdirectory
  sudo python Pixil.py main/spiral
  sudo python Pixil.py holiday/christmas_tree
  
  # Run all scripts in a directory
  sudo python Pixil.py main/*         # All scripts in effects directory
  sudo python Pixil.py holiday/winter/*  # All scripts in holiday/winter
  
  # Script run duration (2 minutes 30 seconds)
  sudo python Pixil.py main/spiral -t 2:30
  
  # Run with debug output
  sudo python Pixil.py main/spiral -d DEBUG_VERBOSE

  # Run with the queue monitor
  sudo python Pixil.py main/snake -q  

  # Combined options
  sudo python Pixil.py holiday/* -t 1:30 -d DEBUG_SUMMARY

Note: 
  - Scripts can be referenced with or without the .pix extension
  - Subdirectories are supported for both single scripts and wildcards
  - Debug levels: DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE
"""
    )
    
    parser.add_argument(
        'script_path',
        help='Script file or pattern (e.g., myscript, effects/*, holiday/winter/*)'
    )
    
    parser.add_argument(
        '-t', '--time',
        type=validate_time_format,
        help='Run duration in mm:ss format (e.g., 2:30)'
    )
    
    parser.add_argument(
        '-d', '--debug',
        type=validate_debug_level,
        help='Debug level (DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE)'
    )
    
    # Add new argument
    parser.add_argument(
        '-q', '--queue-monitor',
        action='store_true',
        help='Show real-time queue depth monitor'
    )

    args = parser.parse_args()
    
    # Convert args to more intuitive names
    return argparse.Namespace(
        script_path=args.script_path,
        duration=args.time,  # Already converted to seconds by validate_time_format
        debug_level=args.debug,
        queue_monitor=args.queue_monitor
    )

# Export symbols
__all__ = ['parse_args']