"""Test-mode inspection helpers (rgb_matrix_lib)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .api import RGB_Api

def _state_dir() -> Path:
    override = os.environ.get("PIXIL_TEST_STATE_DIR", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "tests" / "scripts" / "state"


def buffer_fingerprint(api: "RGB_Api") -> str:
    """Stable SHA-256 prefix of the drawing buffer (opaque pixels only)."""
    buf = api.drawing_buffer
    # Hash non-transparent cells only so layer compositing order in buffer is stable.
    from .utils import TRANSPARENT_COLOR

    mask = (buf[:, :, 0] != TRANSPARENT_COLOR[0]) | (
        buf[:, :, 1] != TRANSPARENT_COLOR[1]
    ) | (buf[:, :, 2] != TRANSPARENT_COLOR[2])
    if not mask.any():
        return "empty"
    payload = buf[mask].tobytes()
    return hashlib.sha256(payload).hexdigest()[:16]


def try_write_buffer_hash_state(fp: str) -> bool:
    """Best-effort write for harness fallback; never raises (sudo/root vs repo perms)."""
    try:
        state_dir = _state_dir()
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "last_buffer.hash").write_text(fp + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def write_buffer_hash_state(api: "RGB_Api") -> str:
    """Return buffer fingerprint; persist to state file when writable."""
    fp = buffer_fingerprint(api)
    try_write_buffer_hash_state(fp)
    return fp


def read_buffer_hash_state() -> Optional[str]:
    path = _state_dir() / "last_buffer.hash"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def emit_test_snapshot(api: "RGB_Api") -> str:
    """Consumer-side: fingerprint buffer; optional file + stdout for harness."""
    fp = buffer_fingerprint(api)
    try_write_buffer_hash_state(fp)
    print(f"PIXIL_TEST_BUFFER_HASH={fp}", flush=True)
    return fp
