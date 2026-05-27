#!/usr/bin/env python3
"""
One-off: add fps(60) to every scripts/main/*.pix that does not already define fps().

Usage (from repo root):
  python3 scripts/temp_add_fps_to_main.py
  python3 scripts/temp_add_fps_to_main.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_DIR = REPO_ROOT / "scripts" / "main"

FPS_COMMENT = "# Cap display refresh at 60 FPS (rgb_matrix_lib; fps(0) = unlimited)"
FPS_LINE = "fps(60)"

HAS_FPS = re.compile(r"^\s*fps\s*\(", re.MULTILINE)
HAS_THROTTLE = re.compile(r"^\s*throttle\s*\(", re.MULTILINE)


def find_insert_index(lines: list[str]) -> int:
    """Insert after first throttle(), else after leading # / blank header."""
    for i, line in enumerate(lines):
        if HAS_THROTTLE.match(line):
            return i + 1
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "" or stripped.startswith("#"):
            i += 1
            continue
        break
    return i


def insert_fps_block(lines: list[str], index: int) -> list[str]:
    block = [FPS_COMMENT, FPS_LINE]
    before = lines[:index]
    after = lines[index:]

    if before and before[-1].strip() != "":
        before.append("")
    if after and after[0].strip() != "":
        block.append("")

    return before + block + after


def process_file(path: Path, dry_run: bool) -> str:
    text = path.read_text(encoding="utf-8")
    if HAS_FPS.search(text):
        return "skip_has_fps"

    lines = text.splitlines(keepends=True)
    # Normalise to lines without keepends for editing
    raw = [ln.rstrip("\n\r") for ln in lines]
    if not raw:
        return "skip_empty"

    idx = find_insert_index(raw)
    new_raw = insert_fps_block(raw, idx)
    new_text = "\n".join(new_raw) + ("\n" if text.endswith("\n") else "")

    if new_text == text:
        return "skip_unchanged"

    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return "updated"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing files",
    )
    args = parser.parse_args()

    if not MAIN_DIR.is_dir():
        print(f"Missing directory: {MAIN_DIR}", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    for path in sorted(MAIN_DIR.glob("*.pix")):
        result = process_file(path, args.dry_run)
        counts[result] = counts.get(result, 0) + 1
        if result == "updated":
            prefix = "would update" if args.dry_run else "updated"
            print(f"  {prefix}: {path.name}")

    print()
    print(f"Directory: {MAIN_DIR}")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    total = sum(counts.values())
    print(f"  total: {total}")
    if args.dry_run:
        print("\n(dry run — no files written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
