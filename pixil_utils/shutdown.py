"""
Ctrl+C shutdown coordination for Pixil.

Signal handler only sets a flag; the main thread performs cleanup and exit.
"""

import os
import sys

_ctrl_c_requested = False


class PixilShutdownRequested(Exception):
    """Ctrl+C requested; abort current script."""


def request_shutdown() -> None:
    global _ctrl_c_requested
    _ctrl_c_requested = True


def shutdown_requested() -> bool:
    return _ctrl_c_requested


def reset_shutdown() -> None:
    global _ctrl_c_requested
    _ctrl_c_requested = False


def exit_pixil(queue_instance=None, queue_monitor=None) -> None:
    """Stop the show: clear matrix, stop consumer, exit immediately (no metrics)."""
    if queue_monitor is not None:
        try:
            queue_monitor.stop()
        except Exception:
            pass

    try:
        from pixil_utils.terminal_handler import stop_terminal
        stop_terminal()
    except Exception:
        pass

    if queue_instance is not None:
        try:
            sys.stdout.write("Clearing display...\n")
            sys.stdout.flush()
            queue_instance.shutdown_display(timeout=4.0)
        except Exception:
            try:
                queue_instance.stop_consumer_force()
            except Exception:
                pass

    os._exit(0)


__all__ = [
    'PixilShutdownRequested',
    'request_shutdown',
    'shutdown_requested',
    'reset_shutdown',
    'exit_pixil',
]
