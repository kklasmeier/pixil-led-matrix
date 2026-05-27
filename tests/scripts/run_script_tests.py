#!/usr/bin/env python3
"""
Tier 2: Run curated .pix scripts through Pixil.py (requires sudo + LED stack on Pi).

With PIXIL_TEST_MODE=1 (set automatically), Pixil emits:
  PIXIL_TEST_SUMMARY script=... commands=N rest=R fail=F buffer=HASH exit=0
  PIXIL_TEST_BUFFER_HASH=HASH  (from consumer process)

Optional golden buffer hashes in tests/scripts/golden/<script>.hash

Golden modes (non-volatile scripts only):
  Default (./run test-scripts): compare existing goldens; create *.hash if missing.
  Refresh all: PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts
  Compare only (no auto-create): PIXIL_TEST_UPDATE_MISSING_GOLDEN=0 ./run test-scripts
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = Path(__file__).parent / "manifest"
DEFAULT_MANIFEST = MANIFEST_DIR / "core.txt"
MAIN_SMOKE_MANIFEST = MANIFEST_DIR / "main_smoke.txt"
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

# Default smoke duration (was 1:00 — too slow for infinite-loop main shows).
DEFAULT_TIME_LIMIT = os.environ.get("PIXIL_SCRIPT_TIME_LIMIT", "0:10")
# Wall-clock cap per script (overridden per entry when possible).
DEFAULT_SUBPROCESS_TIMEOUT = int(os.environ.get("PIXIL_SCRIPT_TIMEOUT", "90"))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _parse_seconds_from_limit(limit: str) -> int:
    """Parse Pixil -t style limit to seconds (for subprocess timeout)."""
    limit = limit.strip()
    if limit.endswith("s") and limit[:-1].isdigit():
        return int(limit[:-1])
    if limit.isdigit():
        return int(limit)
    if ":" in limit:
        parts = [int(p) for p in limit.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 10


def _seconds_to_pixil_limit(seconds: int) -> str:
    """Format seconds as M:SS for Pixil -t."""
    seconds = max(1, seconds)
    if seconds < 60:
        return f"0:{seconds:02d}"
    return f"{seconds // 60}:{seconds % 60:02d}"


def _parse_manifest_time_token(token: str, default: str) -> str:
    """Parse optional per-line time: quick, 6s, 0:08."""
    t = token.strip()
    lower = t.lower()
    if lower == "quick":
        return "0:05"
    if t.endswith("s") and t[:-1].isdigit():
        return _seconds_to_pixil_limit(int(t[:-1]))
    if ":" in t or t.isdigit():
        return t if ":" in t else _seconds_to_pixil_limit(int(t))
    return default


def _load_manifest_file(path: Path, *, default_time: str = DEFAULT_TIME_LIMIT) -> list[tuple[str, bool, str]]:
    """
    Return list of (script path relative to scripts/, volatile, pixil -t limit).

    Line format:  path [volatile] [time]
      volatile — skip buffer golden compare
      quick    — 5 second smoke
      6s       — 6 second smoke
      0:08     — explicit M:SS limit
    """
    if not path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")

    scripts: list[tuple[str, bool, str]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        rel = parts[0]
        volatile = False
        time_limit = default_time
        for token in parts[1:]:
            if token.lower() == "volatile":
                volatile = True
            else:
                time_limit = _parse_manifest_time_token(token, default_time)
        scripts.append((rel, volatile, time_limit))
    return scripts


def _load_manifests(paths: list[Path]) -> list[tuple[str, bool, str]]:
    all_entries: list[tuple[str, bool, str]] = []
    for path in paths:
        all_entries.extend(_load_manifest_file(path))
    return all_entries


def _resolve_manifest_paths(cli_paths: list[str] | None) -> list[Path]:
    if cli_paths:
        return [(REPO_ROOT / p).resolve() if not Path(p).is_absolute() else Path(p) for p in cli_paths]
    env = os.environ.get("PIXIL_TEST_MANIFESTS", "").strip()
    if env:
        return [REPO_ROOT / p.strip() for p in env.split(":") if p.strip()]
    return [DEFAULT_MANIFEST]


def _parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tier 2 Pixil script smoke tests")
    parser.add_argument(
        "--manifest",
        action="append",
        metavar="PATH",
        help="Manifest file (repeatable). Default: tests/scripts/manifest/core.txt",
    )
    parser.add_argument(
        "--include-main-smoke",
        action="store_true",
        help="Also run tests/scripts/manifest/main_smoke.txt (same as second --manifest)",
    )
    parser.add_argument(
        "--update-golden",
        action="store_true",
        help="Overwrite every non-volatile golden (same as PIXIL_TEST_UPDATE_GOLDEN=1)",
    )
    parser.add_argument(
        "--no-update-missing",
        action="store_true",
        help="Do not create goldens for scripts that lack a .hash file",
    )
    return parser.parse_args(argv)


def _golden_mode(cli: argparse.Namespace) -> tuple[bool, bool]:
    """Return (update_all, update_missing)."""
    update_all = cli.update_golden or _env_bool("PIXIL_TEST_UPDATE_GOLDEN", False)
    if update_all:
        return True, False
    update_missing = not cli.no_update_missing and _env_bool(
        "PIXIL_TEST_UPDATE_MISSING_GOLDEN", True
    )
    return False, update_missing


# Set in main() after CLI parse
UPDATE_GOLDEN = False
UPDATE_MISSING_GOLDEN = True

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
BUFFER_HASH_RE = re.compile(r"PIXIL_TEST_BUFFER_HASH=(empty|[a-f0-9]{16})")
SNAPSHOT_ERROR_RE = re.compile(r"PIXIL_TEST_SNAPSHOT_ERROR=(.+)")


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
        return True, "volatile (no golden)"
    if UPDATE_GOLDEN:
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(buffer_hash + "\n", encoding="utf-8")
        return True, f"golden updated -> {path.name}"
    if not path.is_file():
        if UPDATE_MISSING_GOLDEN:
            GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(buffer_hash + "\n", encoding="utf-8")
            return True, f"golden created -> {path.name}"
        return True, "no golden file yet (skipped)"
    expected = path.read_text(encoding="utf-8").strip()
    if expected != buffer_hash:
        return False, f"buffer hash mismatch (expected {expected}, got {buffer_hash})"
    return True, f"golden ok ({buffer_hash})"


def run_one(
    script_rel: str,
    *,
    volatile: bool = False,
    time_limit: str = DEFAULT_TIME_LIMIT,
) -> tuple[bool, str, float]:
    """Run one script. Returns (passed, detail, elapsed_seconds)."""
    script_path = REPO_ROOT / "scripts" / script_rel
    if not script_path.is_file():
        return False, f"missing file: {script_path}", 0.0

    pixil_arg = str(Path(script_rel).with_suffix(""))
    limit_seconds = _parse_seconds_from_limit(time_limit)
    subprocess_timeout = min(
        DEFAULT_SUBPROCESS_TIMEOUT,
        max(limit_seconds + 25, 30),
    )

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
        time_limit,
        "-d",
        "DEBUG_OFF",
    ]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=subprocess_timeout,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        return False, f"timeout after {subprocess_timeout}s (limit {time_limit})", elapsed

    elapsed = time.perf_counter() - t0
    combined = (proc.stdout or "") + (proc.stderr or "")
    snap_err = SNAPSHOT_ERROR_RE.search(combined)
    if snap_err:
        return False, f"snapshot error: {snap_err.group(1).strip()}", elapsed

    if proc.returncode != 0:
        tail = combined[-2000:] if len(combined) > 2000 else combined
        return False, f"exit {proc.returncode}\n{tail}", elapsed
    fail_match = SCRIPT_FAIL_PATTERN.search(combined)
    if fail_match:
        return False, f"FAIL in output: {fail_match.group(0).strip()}", elapsed
    if "Traceback (most recent call last)" in combined:
        return False, "Python traceback in output", elapsed

    parsed = _parse_test_output(combined)
    summary = parsed.get("summary")
    if not summary:
        return False, "missing PIXIL_TEST_SUMMARY (is PIXIL_TEST_MODE set?)", elapsed
    if summary["exit"] != 0:
        return False, f"summary exit={summary['exit']}", elapsed
    if summary["failures"] > 0:
        return False, f"summary failures={summary['failures']}", elapsed

    buffer_hash = parsed.get("buffer_hash") or summary.get("buffer")
    if buffer_hash == "none":
        buffer_hash = parsed.get("buffer_hash")
    if (not buffer_hash or buffer_hash == "none") and STATE_HASH.is_file():
        buffer_hash = STATE_HASH.read_text(encoding="utf-8").strip() or None
    if not buffer_hash or buffer_hash == "none":
        return False, (
            "missing buffer fingerprint (__test_snapshot__ did not run? "
            f"summary buffer={summary.get('buffer')})"
        ), elapsed

    ok, golden_msg = _check_golden(script_rel, buffer_hash, volatile=volatile)
    if not ok:
        return False, golden_msg, elapsed

    return True, (
        f"commands={summary['commands']} rest={summary['rest']} "
        f"buffer={buffer_hash} ({golden_msg})"
    ), elapsed


def _golden_mode_label() -> str:
    if UPDATE_GOLDEN:
        return "UPDATE all golden hashes"
    if UPDATE_MISSING_GOLDEN:
        return "compare goldens; create missing"
    return "compare goldens only (missing skipped)"


def main() -> int:
    global UPDATE_GOLDEN, UPDATE_MISSING_GOLDEN

    cli = _parse_cli()
    UPDATE_GOLDEN, UPDATE_MISSING_GOLDEN = _golden_mode(cli)

    ok, reason = _can_run()
    if not ok:
        print(f"SKIP Tier 2 script tests: {reason}")
        print("Run Tier 1 only: ./run test")
        return 0

    manifest_paths = _resolve_manifest_paths(cli.manifest)
    if cli.include_main_smoke and MAIN_SMOKE_MANIFEST not in manifest_paths:
        manifest_paths.append(MAIN_SMOKE_MANIFEST)

    try:
        scripts = _load_manifests(manifest_paths)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not scripts:
        print("ERROR: empty manifest", file=sys.stderr)
        return 1

    manifest_names = ", ".join(p.relative_to(REPO_ROOT).as_posix() for p in manifest_paths)
    total_budget = sum(_parse_seconds_from_limit(t) for _, _, t in scripts)
    print(
        f"Tier 2: {len(scripts)} scripts from {manifest_names} "
        f"(~{total_budget}s Pixil time budget, {_golden_mode_label()})"
    )

    failed = []
    suite_t0 = time.perf_counter()
    for rel, volatile, time_limit in scripts:
        passed, detail, elapsed = run_one(rel, volatile=volatile, time_limit=time_limit)
        tag = f"-t {time_limit}"
        if volatile:
            tag += ", volatile"
        status = "PASS" if passed else "FAIL"
        print(
            f"  [{status}] {rel} ({tag}, {elapsed:.1f}s wall)"
            + ("" if passed else f" — {detail.splitlines()[0]}")
        )
        if passed and detail != "ok":
            print(f"         {detail}")
        if not passed:
            failed.append((rel, detail))

    suite_elapsed = time.perf_counter() - suite_t0
    if failed:
        print(f"\n{len(failed)} script(s) failed ({suite_elapsed:.1f}s total):", file=sys.stderr)
        for rel, detail in failed:
            print(f"  - {rel}: {detail.splitlines()[0]}", file=sys.stderr)
        return 1

    print(f"\nAll {len(scripts)} script(s) passed ({suite_elapsed:.1f}s total).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
