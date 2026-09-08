"""Persistent, non-invasive status for a running Pixil interpreter."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional


STATUS_PATH = Path(__file__).resolve().parents[1] / "database" / "data" / "runtime_status.json"
QUEUE_STATUS_PATH = Path("/dev/shm/pixil_queue_status.json")


def _write_json(path: Path, status: dict[str, Any]) -> None:
    """Atomically replace the state file so readers never see partial JSON."""
    path.parent.mkdir(exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{path.stem}.", suffix=".json", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(status, output, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _write_status(status: dict[str, Any]) -> None:
    _write_json(STATUS_PATH, status)


def initialize_status(arguments: list[str]) -> None:
    """Record a new Pixil process before it starts its first script."""
    now = time.time()
    _write_status(
        {
            "pid": os.getpid(),
            "process_started_at": now,
            "arguments": arguments,
            "script_name": None,
            "script_path": None,
            "script_started_at": None,
            "script_expected_end_at": None,
            "recent_scripts": [],
        }
    )


def set_current_script(script_path: str, duration_seconds: Optional[float]) -> float:
    """Publish the script currently being interpreted and its timer window."""
    now = time.time()
    expected_end = None if duration_seconds is None else now + duration_seconds
    status = read_status() or {}
    previous_name = status.get("script_name")
    previous_started = status.get("script_started_at")
    recent = list(status.get("recent_scripts") or [])
    if previous_name and isinstance(previous_started, (int, float)):
        recent.append({"name": previous_name, "started_at": previous_started})
        recent = recent[-3:]
    status.update(
        {
            "pid": os.getpid(),
            "script_name": Path(script_path).name,
            "script_path": str(script_path),
            "script_started_at": now,
            "script_expected_end_at": expected_end,
            "recent_scripts": recent,
        }
    )
    status.setdefault("process_started_at", now)
    status.setdefault("arguments", [])
    _write_status(status)
    return now


def clear_status() -> None:
    """Remove the live state only when it belongs to this process."""
    status = read_status()
    if status is not None and status.get("pid") not in (None, os.getpid()):
        return
    try:
        STATUS_PATH.unlink()
    except FileNotFoundError:
        pass
    _clear_owned_queue_status()


def read_status() -> Optional[dict[str, Any]]:
    """Return complete status data, or None for missing/corrupt state."""
    try:
        with STATUS_PATH.open(encoding="utf-8") as source:
            data = json.load(source)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _clear_owned_queue_status() -> None:
    try:
        with QUEUE_STATUS_PATH.open(encoding="utf-8") as source:
            status = json.load(source)
        if status.get("pid") not in (None, os.getpid()):
            return
    except (FileNotFoundError, OSError, json.JSONDecodeError, AttributeError):
        pass
    try:
        QUEUE_STATUS_PATH.unlink()
    except FileNotFoundError:
        pass


class QueueStatusReporter:
    """Sample queue depth without attaching to the interpreter."""

    def __init__(self, queue_instance: Any, interval: float = 1.0):
        self.queue_instance = queue_instance
        self.interval = interval
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._depth_total = 0
        self._sample_count = 0
        self._script_started_at: Optional[float] = None
        self._thread = threading.Thread(
            target=self._run, name="pixil-queue-status", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def reset_for_script(self, script_started_at: float) -> None:
        with self._lock:
            self._depth_total = 0
            self._sample_count = 0
            self._script_started_at = script_started_at

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=max(1.0, self.interval + 0.5))
        _clear_owned_queue_status()

    def _sample(self) -> None:
        depth = self.queue_instance.command_queue.qsize()
        capacity = self.queue_instance._queue_size
        with self._lock:
            self._depth_total += depth
            self._sample_count += 1
            samples = self._sample_count
            average = self._depth_total / samples
            script_started_at = self._script_started_at
        _write_json(
            QUEUE_STATUS_PATH,
            {
                "pid": os.getpid(),
                "sampled_at": time.time(),
                "script_started_at": script_started_at,
                "queue_depth": depth,
                "queue_capacity": capacity,
                "script_average_queue_depth": average,
                "sample_count": samples,
            },
        )

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._sample()
            except (NotImplementedError, OSError, AttributeError):
                pass
            self._stop_event.wait(self.interval)
