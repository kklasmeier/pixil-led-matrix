"""Safe, file-based control requests for a running Pixil process."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

from pixil_utils.runtime_status import _write_json, read_status


CONTROL_PATH = Path("/dev/shm/pixil_control.json")
_pending_jump_target: Optional[str] = None


def clear_control_request() -> None:
    try:
        CONTROL_PATH.unlink()
    except FileNotFoundError:
        pass


def poll_control_request() -> Optional[dict[str, Any]]:
    """Consume one request addressed to this Pixil parent process."""
    try:
        with CONTROL_PATH.open(encoding="utf-8") as source:
            request = json.load(source)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    if not isinstance(request, dict) or request.get("pid") != os.getpid():
        return None
    clear_control_request()
    return request


def consume_transition_request() -> bool:
    """Record a pending jump and tell the timer to end the current script."""
    global _pending_jump_target
    request = poll_control_request()
    if request is None:
        return False
    action = request.get("action")
    if action == "jump" and isinstance(request.get("target"), str):
        _pending_jump_target = request["target"]
        print(
            f"External request: jumping to {Path(_pending_jump_target).name}...",
            flush=True,
        )
        return True
    if action == "next":
        print("External request: advancing to the next script...", flush=True)
        return True
    return False


def consume_jump_target() -> Optional[str]:
    global _pending_jump_target
    target = _pending_jump_target
    _pending_jump_target = None
    return target


def _live_pixil_status() -> dict[str, Any]:
    status = read_status()
    if not status:
        raise RuntimeError("Pixil is not running or runtime status is unavailable")
    pid = status.get("pid")
    try:
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ")
    except (OSError, TypeError):
        raise RuntimeError("Pixil is not running") from None
    if b"Pixil.py" not in command:
        raise RuntimeError("Pixil runtime status is stale")
    return status


def _resolve_target(target: str) -> str:
    from pixil_utils.file_manager import PixilFileManager

    return str(PixilFileManager().get_script_path(target).resolve())


def submit_request(action: str, target: Optional[str] = None, wait: float = 10.0) -> int:
    """Submit a transition request and report whether Pixil acknowledged it."""
    status = _live_pixil_status()
    arguments = status.get("arguments") or []
    if not any("*" in str(argument) for argument in arguments):
        raise RuntimeError("next/jump controls require a running wildcard playlist")
    pid = status["pid"]
    old_started = status.get("script_started_at")
    old_script = status.get("script_name") or "current script"

    if action == "jump":
        if not target:
            raise ValueError("jump requires a script name, for example: ./run jump main/Rain.pix")
        target = _resolve_target(target)
        description = f"jump from {old_script} to {Path(target).name}"
    elif action == "next":
        target = None
        description = f"advance from {old_script} to the next script"
    else:
        raise ValueError(f"unsupported action: {action}")

    _write_json(
        CONTROL_PATH,
        {
            "pid": pid,
            "action": action,
            "target": target,
            "requested_at": time.time(),
        },
    )
    print(f"Request accepted: {description}.")
    print("Waiting for Pixil to complete the script transition...")

    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        current = read_status()
        if not current or current.get("pid") != pid:
            print("Pixil stopped before acknowledging the request.")
            return 1
        changed = current.get("script_started_at") != old_started
        target_matches = (
            action != "jump"
            or Path(current.get("script_path", "")).resolve() == Path(target).resolve()
        )
        if changed and target_matches:
            print(f"Transition complete: now running {current.get('script_name', 'unknown')}.")
            return 0
        time.sleep(0.2)

    if CONTROL_PATH.exists():
        print("Request is pending; the current script has not reached a control checkpoint yet.")
    else:
        print("Request acknowledged; Pixil is still completing the display transition.")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: runtime_control.py next | jump SCRIPT", file=sys.stderr)
        return 2
    action = argv[0]
    target = argv[1] if len(argv) > 1 else None
    try:
        return submit_request(action, target)
    except (RuntimeError, ValueError, FileNotFoundError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
