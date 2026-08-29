#!/usr/bin/env python3
"""Compare pure-Pixil particle physics with generic native primitives.

This is an explicit Raspberry Pi hardware benchmark, not part of ``./run test``.
It runs deterministic, non-rendering Pixil scripts and compares median runtime
and final-state checksum.
"""

from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PIXIL = ROOT / "Pixil.py"
SCRIPTS = {
    "reference": ROOT / "scripts/testing/perf_particle_reference.pix",
    "primitives": ROOT / "scripts/testing/perf_particle_primitives.pix",
}
RESULT_RE = re.compile(
    r"PARTICLE_PERF\s+variant=(\w+)\s+frames=(\d+)\s+"
    r"elapsed_ms=([0-9.]+)\s+checksum=([-+0-9.eE]+)"
)


def _ensure_ready() -> None:
    sudo = subprocess.run(
        ["sudo", "-n", "true"],
        capture_output=True,
        text=True,
        check=False,
    )
    if sudo.returncode != 0:
        raise RuntimeError("passwordless sudo is required on the matrix Pi")

    running = subprocess.run(
        ["pgrep", "-af", r"[P]ixil\.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    if running.returncode == 0 and running.stdout.strip():
        raise RuntimeError(
            "Pixil is already running; stop the show before this hardware benchmark"
        )


def _run_variant(variant: str, timeout: float) -> tuple[float, float, int]:
    command = [
        "sudo",
        "-n",
        "python3",
        str(PIXIL),
        str(SCRIPTS[variant]),
        "-d",
        "DEBUG_OFF",
    ]
    proc = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0:
        raise RuntimeError(
            f"{variant} exited {proc.returncode}\n{output[-4000:]}"
        )
    match = RESULT_RE.search(output)
    if not match:
        raise RuntimeError(
            f"{variant} did not emit PARTICLE_PERF\n{output[-4000:]}"
        )
    reported_variant, frames, elapsed_ms, checksum = match.groups()
    if reported_variant != variant:
        raise RuntimeError(
            f"expected variant={variant}, got variant={reported_variant}"
        )
    return float(elapsed_ms), float(checksum), int(frames)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark Pixil particle primitives against pure Pixil",
    )
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--min-speedup", type=float, default=1.5)
    parser.add_argument("--checksum-tolerance", type=float, default=0.01)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    try:
        _ensure_ready()
        samples: dict[str, list[float]] = {"reference": [], "primitives": []}
        checksums: dict[str, list[float]] = {"reference": [], "primitives": []}
        frame_counts: set[int] = set()

        # Alternate order to reduce temperature/order bias.
        for run_index in range(args.runs):
            order = (
                ("reference", "primitives")
                if run_index % 2 == 0
                else ("primitives", "reference")
            )
            for variant in order:
                elapsed, checksum, frames = _run_variant(
                    variant,
                    args.timeout,
                )
                samples[variant].append(elapsed)
                checksums[variant].append(checksum)
                frame_counts.add(frames)
                print(
                    f"run={run_index + 1} variant={variant} "
                    f"elapsed_ms={elapsed:.3f} checksum={checksum:.6f}",
                    flush=True,
                )

        reference_ms = statistics.median(samples["reference"])
        primitives_ms = statistics.median(samples["primitives"])
        speedup = reference_ms / primitives_ms
        reference_checksum = statistics.median(checksums["reference"])
        primitive_checksum = statistics.median(checksums["primitives"])
        checksum_delta = abs(reference_checksum - primitive_checksum)

        print()
        print(f"frames={','.join(str(n) for n in sorted(frame_counts))}")
        print(f"reference_median_ms={reference_ms:.3f}")
        print(f"primitives_median_ms={primitives_ms:.3f}")
        print(f"speedup={speedup:.2f}x")
        print(f"checksum_delta={checksum_delta:.9f}")

        if len(frame_counts) != 1:
            print("FAIL: variants reported different frame counts")
            return 1
        if checksum_delta > args.checksum_tolerance:
            print(
                "FAIL: final-state checksum differs by more than "
                f"{args.checksum_tolerance}"
            )
            return 1
        if speedup < args.min_speedup:
            print(
                f"FAIL: speedup {speedup:.2f}x is below "
                f"{args.min_speedup:.2f}x"
            )
            return 1
        print("PASS: particle primitives preserve state and improve performance")
        return 0
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
