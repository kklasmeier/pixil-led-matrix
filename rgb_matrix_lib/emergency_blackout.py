"""Black out the LED matrix from a fresh process after the consumer was killed."""

from __future__ import annotations


def run_emergency_blackout() -> None:
    """Initialize matrix hardware in this process and force every pixel off."""
    try:
        from rgb_matrix_lib.api import get_api_instance

        api = get_api_instance()
        api.blackout_display()
        api.cleanup()
    except Exception as exc:
        print(f"[QUEUE] Emergency blackout failed: {exc}", flush=True)


def spawn_emergency_blackout(timeout: float = 4.0) -> None:
    """Run ``run_emergency_blackout`` in a short-lived child process."""
    import time
    from multiprocessing import Process

    proc = Process(target=run_emergency_blackout, name="emergency_blackout")
    proc.daemon = True
    proc.start()
    proc.join(timeout=timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(0.5)
        if proc.is_alive():
            proc.kill()
            proc.join(0.5)
    time.sleep(0.05)
