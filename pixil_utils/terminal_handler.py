"""
Terminal input handling utilities for Pixil script runner.
Handles raw terminal input for keyboard control.
"""

import sys
import tty
import termios
import select
from .debug import debug_print, DEBUG_VERBOSE, DEBUG_CONCISE

# Global terminal handler state
_handler = None

def initialize_terminal():
    """Initialize global terminal handler for keyboard input."""
    global _handler
    if _handler is None:
        _handler = TerminalHandler()
    return _handler

def start_terminal():
    """Start terminal handling if initialized."""
    global _handler
    if _handler:
        _handler.start()

def stop_terminal():
    """Stop terminal handling if active."""
    global _handler
    if _handler:
        _handler.stop()
        _handler = None

def check_spacebar():
    """
    Check for spacebar press using global handler.
    Returns False if handler not initialized.
    """
    global _handler
    if _handler:
        return _handler.check_spacebar()
    return False

class TerminalHandler:
    """Manages terminal settings and keyboard input detection."""
    
    def __init__(self):
        """Initialize terminal handler."""
        self.fd = sys.stdin.fileno()
        self.old_settings = None
        debug_print("Terminal handler initialized", DEBUG_VERBOSE)
        
    def start(self):
        """
        Start minimal terminal modifications for keyboard detection.
        Preserves signal handling while allowing direct character reads.
        """
        try:
            # Save original settings
            self.old_settings = termios.tcgetattr(self.fd)
            
            # Get current settings
            new_settings = termios.tcgetattr(self.fd)
            
            # Only modify what we need for spacebar detection
            new_settings[3] = new_settings[3] & ~(
                termios.ICANON |  # Turn off buffered input
                termios.ECHO      # Turn off echo
            )
            
            # Apply new settings
            termios.tcsetattr(self.fd, termios.TCSADRAIN, new_settings)
            debug_print("Terminal handler started with minimal modifications", DEBUG_VERBOSE)
            
        except Exception as e:
            debug_print(f"Error starting terminal handler: {str(e)}", DEBUG_CONCISE)
            self.stop()
            raise

    def stop(self):
        """Restore original terminal settings."""
        if self.old_settings:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
                debug_print("Terminal settings restored", DEBUG_VERBOSE)
            except Exception as e:
                debug_print(f"Error restoring terminal settings: {str(e)}", DEBUG_CONCISE)
            finally:
                self.old_settings = None

    def check_spacebar(self):
        """
        Non-blocking check for spacebar press.
        
        Returns:
            bool: True if spacebar was pressed, False otherwise
        """
        try:
            # Check for input without blocking
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                # Read one character if input is available
                char = sys.stdin.read(1)
                # Check if it's spacebar
                return char == ' '
        except Exception as e:
            debug_print(f"Error checking spacebar: {str(e)}", DEBUG_VERBOSE)
        return False

# Export symbols
__all__ = ['initialize_terminal', 'start_terminal', 'stop_terminal', 'check_spacebar']