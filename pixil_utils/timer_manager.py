"""
Timer management utilities for Pixil script runner.
Handles script duration tracking and timer state.
"""

import datetime
import time
from .debug import debug_print, DEBUG_VERBOSE

_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# Global timer state
end_time = None
timer_expired = False 

def initialize_timer(duration_seconds):
    """
    Initialize timer with duration in seconds.
    If duration is None, timer will never expire.
    
    Args:
        duration_seconds: Number of seconds to run, or None for unlimited
    """
    global end_time, timer_expired
    
    timer_expired = False  # Reset flag
    if duration_seconds is not None:
        end_time = time.time() + duration_seconds
        debug_print(f"Timer initialized for {duration_seconds} seconds", DEBUG_VERBOSE)
    else:
        end_time = None
        debug_print("Timer initialized for unlimited duration", DEBUG_VERBOSE)

def is_time_expired():
    """
    Check if timer has expired.
    
    Returns:
        bool: True if timer is set and has expired, False otherwise
    """
    global end_time, timer_expired
    if timer_expired:
        return True

    from .terminal_handler import consume_skip_request

    if consume_skip_request():
        print("Spacebar pressed, skipping to next script...")
        force_timer_expired()
        return True

    if end_time is None:
        return False

    timer_expired = time.time() >= end_time
    return timer_expired

def force_timer_expired():
    """Force timer to expired state."""
    global timer_expired
    timer_expired = True

    debug_print("Timer forced to expired state", DEBUG_VERBOSE)

def clear_timer():
    """Reset timer state."""
    global end_time, timer_expired
    end_time = None
    timer_expired = False
    debug_print("Timer cleared", DEBUG_VERBOSE)

def announce_script_start(script_path, duration_seconds=None):
    """
    Initialize the per-script timer and print start / expected end times.

    Args:
        script_path: Path to the script being started
        duration_seconds: Run duration in seconds, or None for unlimited
    """
    initialize_timer(duration_seconds)

    start = datetime.datetime.now()
    print(f"Current script: {script_path}...")
    print(f"Started: {start.strftime(_DATETIME_FORMAT)}")
    if duration_seconds is not None:
        end = start + datetime.timedelta(seconds=duration_seconds)
        print(f"Expected end: {end.strftime(_DATETIME_FORMAT)}")

def get_remaining_time():
    """
    Get remaining time in seconds.
    
    Returns:
        float or None: Seconds remaining if timer set, None if unlimited
    """
    global end_time
    
    if end_time is None:
        return None
        
    remaining = end_time - time.time()
    return max(0, remaining)

# Export symbols
__all__ = [
    'initialize_timer',
    'is_time_expired',
    'clear_timer',
    'get_remaining_time',
    'announce_script_start',
]