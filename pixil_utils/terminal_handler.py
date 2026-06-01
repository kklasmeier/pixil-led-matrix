"""
Terminal input handling utilities for Pixil script runner.
Background thread reads stdin so skip detection does not block script execution.
"""

import select
import sys
import termios
import threading
from .debug import debug_print, DEBUG_VERBOSE, DEBUG_CONCISE

# Set by reader thread on spacebar; consumed from is_time_expired() on the main thread.
_skip_event = threading.Event()

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
    _skip_event.clear()


def consume_skip_request():
    """
    Return True once if the user requested skip (spacebar) since the last consume.
    Main thread only; clears the pending flag.
    """
    if _skip_event.is_set():
        _skip_event.clear()
        return True
    return False


class TerminalHandler:
    """Manages terminal settings and a background stdin reader for spacebar skip."""

    _POLL_INTERVAL = 0.25

    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = None
        self._stop_event = threading.Event()
        self._reader_thread = None
        debug_print("Terminal handler initialized", DEBUG_VERBOSE)

    def start(self):
        """Enable raw stdin and start the background reader thread."""
        try:
            self.old_settings = termios.tcgetattr(self.fd)
            new_settings = termios.tcgetattr(self.fd)
            new_settings[3] = new_settings[3] & ~(
                termios.ICANON |
                termios.ECHO
            )
            termios.tcsetattr(self.fd, termios.TCSADRAIN, new_settings)
            self._stop_event.clear()
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                name="pixil-stdin-reader",
                daemon=True,
            )
            self._reader_thread.start()
            debug_print("Terminal handler started (background stdin reader)", DEBUG_VERBOSE)
        except Exception as e:
            debug_print(f"Error starting terminal handler: {str(e)}", DEBUG_CONCISE)
            self.stop()
            raise

    def stop(self):
        """Stop reader thread and restore terminal settings."""
        self._stop_event.set()
        reader = self._reader_thread
        if reader is not None and reader.is_alive():
            reader.join(timeout=self._POLL_INTERVAL + 0.5)
        self._reader_thread = None

        if self.old_settings:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
                debug_print("Terminal settings restored", DEBUG_VERBOSE)
            except Exception as e:
                debug_print(f"Error restoring terminal settings: {str(e)}", DEBUG_CONCISE)
            finally:
                self.old_settings = None

        _skip_event.clear()

    def _reader_loop(self):
        """Poll stdin in a side thread; set skip flag on spacebar."""
        while not self._stop_event.is_set():
            try:
                readable, _, _ = select.select(
                    [sys.stdin], [], [], self._POLL_INTERVAL,
                )
                if self._stop_event.is_set():
                    break
                if not readable:
                    continue
                char = sys.stdin.read(1)
                if char == ' ':
                    _skip_event.set()
                    debug_print("Spacebar skip requested", DEBUG_VERBOSE)
            except (OSError, ValueError) as e:
                if not self._stop_event.is_set():
                    debug_print(f"Stdin reader stopped: {e}", DEBUG_VERBOSE)
                break


__all__ = [
    'initialize_terminal',
    'start_terminal',
    'stop_terminal',
    'consume_skip_request',
]
