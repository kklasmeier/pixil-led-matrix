#!/usr/bin/env python3
"""
Tier 2: Run curated .pix scripts through Pixil.py (requires sudo + LED stack on Pi).

With PIXIL_TEST_MODE=1 (set automatically), Pixil emits:
  PIXIL_TEST_SUMMARY script=... commands=N rest=R fail=F buffer=HASH exit=0
  PIXIL_TEST_BUFFER_HASH=HASH  (from consumer process)

Optional golden buffer hashes in tests/scripts/golden/<script>.hash
Update goldens: PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).parent / "manifest" / "core.txt"
GOLDEN_DIR = Path(__file__).parent / "golden"
# Under sudo the consumer is root; use /tmp so writes are not blocked on repo mounts.
TEST_STATE_DIR = Path(
    os.environ.get(
        "PIXIL_TEST_STATE_DIR",
        f"/tmp/pixil-test-state-{os.getuid()}",
    )
)
STATE_HASH = TEST_STATE_DIR / "last_buffer.hash"
PIXIL = REPO_ROOT / "Pixil.py"

SUBPROCESS_TIMEOUT = int(os.environ.get("PIXIL_SCRIPT_TIMEOUT", "120"))
PIXIL_TIME_LIMIT = os.environ.get("PIXIL_SCRIPT_TIME_LIMIT", "1:00")
UPDATE_GOLDEN = os.environ.get("PIXIL_TEST_UPDATE_GOLDEN", "").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Script self-check lines like "  FAIL: ..." (not PIXIL_TEST_SUMMARY failures=0)
SCRIPT_FAIL_PATTERN = re.compile(r"^\s+FAIL\b", re.IGNORECASE | re.MULTILINE)
SUMMARY_RE = re.compile(
    r"PIXIL_TEST_SUMMARY\s+"
    r"script=(\S+)\s+"
    r"commands=(\d+)\s+"
    r"rest=(\d+)\s+"
    r"failures=(\d+)\s+"
    r"buffer=(\S+)\s+"
    r"exit=(\d+)"
)
# "empty" must precede [a-f0-9]+ or "e" is captured from "empty"
BUFFER_HASH_RE = re.compile(r"PIXIL_TEST_BUFFER_HASH=(empty|[a-f0-9]{16})")
SNAPSHOT_ERROR_RE = re.compile(r"PIXIL_TEST_SNAPSHOT_ERROR=(.+)")


def _load_manifest() -> list[tuple[str, bool]]:
    """Return (script path, volatile). Volatile scripts skip buffer golden compare."""
    scripts: list[tuple[str, bool]] = []
    for line in MANIFEST.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        rel = parts[0]
        volatile = len(parts) > 1 and parts[1].lower() == "volatile"
        scripts.append((rel, volatile))
    return scripts


def _golden_path(script_rel: str) -> Path:
    name = Path(script_rel).name.replace(".pix", ".hash")
    return GOLDEN_DIR / name


def _can_run() -> tuple[bool, str]:
    if os.environ.get("PIXIL_SKIP_SCRIPT_TESTS", "").lower() in ("1", "true", "yes"):
        return False, "PIXIL_SKIP_SCRIPT_TESTS is set"
    if not PIXIL.is_file():
        return False, f"Pixil.py not found at {PIXIL}"
    try:
        subprocess.run(
            ["sudo", "-n", "true"],
            check=True,
            capture_output=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False, "passwordless sudo required (sudo -n)"
    return True, ""


def _parse_test_output(combined: str) -> dict:
    info = {"summary": None, "buffer_hash": None}
    for line in combined.splitlines():
        m = SUMMARY_RE.search(line)
        if m:
            info["summary"] = {
                "script": m.group(1),
                "commands": int(m.group(2)),
                "rest": int(m.group(3)),
                "failures": int(m.group(4)),
                "buffer": m.group(5),
                "exit": int(m.group(6)),
            }
        m = BUFFER_HASH_RE.search(line)
        if m:
            info["buffer_hash"] = m.group(1)
    return info


def _check_golden(
    script_rel: str, buffer_hash: str, *, volatile: bool = False
) -> tuple[bool, str]:
    path = _golden_path(script_rel)
    if volatile:
        if UPDATE_GOLDEN and path.is_file():
            path.unlink()
        return True, "volatile (clock/runtime — golden not used)"
    if UPDATE_GOLDEN:
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(buffer_hash + "\n", encoding="utf-8")
        return True, f"golden updated -> {path.name}"
    if not path.is_file():
        return True, "no golden file yet (skipped)"
    expected = path.read_text(encoding="utf-8").strip()
    if expected != buffer_hash:
        return False, f"buffer hash mismatch (expected {expected}, got {buffer_hash})"
    return True, f"golden ok ({buffer_hash})"


def run_one(script_rel: str, *, volatile: bool = False) -> tuple[bool, str]:
    script_path = REPO_ROOT / "scripts" / script_rel
    if not script_path.is_file():
        return False, f"missing file: {script_path}"

    pixil_arg = str(Path(script_rel).with_suffix(""))

    TEST_STATE_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_HASH.is_file():
        try:
            STATE_HASH.unlink()
        except OSError:
            pass

    cmd = [
        "sudo",
        "-n",
        "env",
        "PIXIL_TEST_MODE=1",
        f"PIXIL_TEST_REST_CAP={os.environ.get('PIXIL_TEST_REST_CAP', '0.01')}",
        f"PIXIL_TEST_STATE_DIR={TEST_STATE_DIR}",
        "python3",
        str(PIXIL),
        pixil_arg,
        "-t",
        PIXIL_TIME_LIMIT,
        "-d",
        "DEBUG_OFF",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {SUBPROCESS_TIMEOUT}s"

    combined = (proc.stdout or "") + (proc.stderr or "")
    snap_err = SNAPSHOT_ERROR_RE.search(combined)
    if snap_err:
        return False, f"snapshot error: {snap_err.group(1).strip()}"

    if proc.returncode != 0:
        tail = combined[-2000:] if len(combined) > 2000 else combined
        return False, f"exit {proc.returncode}\n{tail}"
    fail_match = SCRIPT_FAIL_PATTERN.search(combined)
    if fail_match:
        return False, f"FAIL in output: {fail_match.group(0).strip()}"
    if "Traceback (most recent call last)" in combined:
        return False, "Python traceback in output"

    parsed = _parse_test_output(combined)
    summary = parsed.get("summary")
    if not summary:
        return False, "missing PIXIL_TEST_SUMMARY (is PIXIL_TEST_MODE set?)"
    if summary["exit"] != 0:
        return False, f"summary exit={summary['exit']}"
    if summary["failures"] > 0:
        return False, f"summary failures={summary['failures']}"

    buffer_hash = parsed.get("buffer_hash") or summary.get("buffer")
    if buffer_hash == "none":
        buffer_hash = parsed.get("buffer_hash")
    if (not buffer_hash or buffer_hash == "none") and STATE_HASH.is_file():
        buffer_hash = STATE_HASH.read_text(encoding="utf-8").strip() or None
    if not buffer_hash or buffer_hash == "none":
        return False, (
            "missing buffer fingerprint (__test_snapshot__ did not run? "
            f"summary buffer={summary.get('buffer')})"
        )

    ok, golden_msg = _check_golden(script_rel, buffer_hash, volatile=volatile)
    if not ok:
        return False, golden_msg

    return True, (
        f"commands={summary['commands']} rest={summary['rest']} "
        f"buffer={buffer_hash} ({golden_msg})"
    )


def main() -> int:
    ok, reason = _can_run()
    if not ok:
        print(f"SKIP Tier 2 script tests: {reason}")
        print("Run Tier 1 only: ./run test")
        return 0

    scripts = _load_manifest()
    if not scripts:
        print("ERROR: empty manifest", file=sys.stderr)
        return 1

    mode = "UPDATE golden hashes" if UPDATE_GOLDEN else "compare goldens when present"
    print(
        f"Tier 2: {len(scripts)} scripts (PIXIL_TEST_MODE=1, -t {PIXIL_TIME_LIMIT}, {mode})"
    )
    failed = []
    for rel, volatile in scripts:
        passed, detail = run_one(rel, volatile=volatile)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {rel}" + ("" if passed else f" — {detail.splitlines()[0]}"))
        if passed and detail != "ok":
            print(f"         {detail}")
        if not passed:
            failed.append((rel, detail))

    if failed:
        print(f"\n{len(failed)} script(s) failed:", file=sys.stderr)
        for rel, detail in failed:
            print(f"\n--- {rel} ---\n{detail}", file=sys.stderr)
        return 1

    print(f"\nAll {len(scripts)} script(s) passed.")
    if not UPDATE_GOLDEN and not any(
        _golden_path(r).is_file() for r, vol in scripts if not vol
    ):
        print(
            "\nTip: capture buffer goldens with:\n"
            "  PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
