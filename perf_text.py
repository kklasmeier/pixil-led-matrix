#!/usr/bin/env python3
"""
Performance benchmark for rgb_matrix_lib rendering paths.

Tests each rendering mode with and without backgrounds to measure
frame times. Run twice — once with the new api.py, once with the old —
and compare results.

Run on the Raspberry Pi:
    sudo python3 test_perf_benchmark.py

Benchmarks:
    1. Immediate mode — no background (draw commands, no framing)
    2. Immediate mode — with background
    3. begin_frame(false) — no background
    4. begin_frame(false) — with background
    5. begin_frame(true) — no background
    6. begin_frame(true) — with background
    7. Sprite movement — no background
    8. Sprite movement — with background
"""

import sys
import time
import math

sys.path.insert(0, '/home/pi/led_matrix')

from rgb_matrix_lib.api import RGB_Api
from rgb_matrix_lib.utils import TRANSPARENT_COLOR


FRAMES = 200
TARGET_FPS = 30


def wait(msg=None):
    input(f"  >> {msg or 'Press ENTER to continue...'}")


def report(name, frame_times):
    """Print performance stats for a benchmark."""
    avg = sum(frame_times) / len(frame_times)
    mn = min(frame_times)
    mx = max(frame_times)
    target_dt = 1.0 / TARGET_FPS
    slow = sum(1 for t in frame_times if t > target_dt)
    total = sum(frame_times)
    fps = len(frame_times) / total if total > 0 else 0

    print(f"  {name}")
    print(f"    Frames:     {len(frame_times)}")
    print(f"    Avg:        {avg*1000:6.1f} ms")
    print(f"    Min:        {mn*1000:6.1f} ms")
    print(f"    Max:        {mx*1000:6.1f} ms")
    print(f"    Max FPS:    {fps:5.1f}")
    print(f"    Slow (>{target_dt*1000:.0f}ms): {slow}/{len(frame_times)}")
    print()
    return avg


def setup_background(api):
    """Create and activate a solid blue background."""
    api.sprite_manager.begin_sprite_definition('bench_bg', 64, 64)
    sprite = api.sprite_manager.get_drawing_target()
    sprite.draw_rectangle(0, 0, 64, 64, 'blue', 60, True)
    api.sprite_manager.end_sprite_definition()
    api.set_background('bench_bg')


def setup_sprite(api):
    """Create a small sprite for movement tests."""
    api.sprite_manager.begin_sprite_definition('bench_spr', 8, 8)
    sprite = api.sprite_manager.get_drawing_target()
    sprite.draw_rectangle(0, 0, 8, 8, 'yellow', 100, True)
    api.sprite_manager.end_sprite_definition()


# ------------------------------------------------------------------
# Benchmarks
# ------------------------------------------------------------------

def bench_immediate_no_bg(api):
    """Immediate mode drawing, no background."""
    times = []
    for i in range(FRAMES):
        t0 = time.time()
        x = i % 50
        y = (i * 3) % 50
        api.draw_rectangle(x, y, 14, 14, 'red', 80, True)
        api.draw_circle(x + 7, y + 7, 5, 'white', 100, False)
        times.append(time.time() - t0)
    return times


def bench_immediate_with_bg(api):
    """Immediate mode drawing, with background."""
    setup_background(api)
    times = []
    for i in range(FRAMES):
        t0 = time.time()
        x = i % 50
        y = (i * 3) % 50
        api.draw_rectangle(x, y, 14, 14, 'red', 80, True)
        api.draw_circle(x + 7, y + 7, 5, 'white', 100, False)
        times.append(time.time() - t0)
    return times


def bench_frame_false_no_bg(api):
    """begin_frame(false), no background."""
    times = []
    for i in range(FRAMES):
        t0 = time.time()
        api.begin_frame(False)
        x = i % 50
        y = (i * 3) % 50
        api.draw_rectangle(x, y, 14, 14, 'red', 80, True)
        api.draw_circle(x + 7, y + 7, 5, 'white', 100, False)
        api.draw_line(0, i % 64, 63, 63 - (i % 64), 'green', 60)
        api.end_frame()
        times.append(time.time() - t0)
    return times


def bench_frame_false_with_bg(api):
    """begin_frame(false), with background."""
    setup_background(api)
    times = []
    for i in range(FRAMES):
        t0 = time.time()
        api.begin_frame(False)
        x = i % 50
        y = (i * 3) % 50
        api.draw_rectangle(x, y, 14, 14, 'red', 80, True)
        api.draw_circle(x + 7, y + 7, 5, 'white', 100, False)
        api.draw_line(0, i % 64, 63, 63 - (i % 64), 'green', 60)
        api.end_frame()
        times.append(time.time() - t0)
    return times


def bench_frame_true_no_bg(api):
    """begin_frame(true), no background."""
    # Seed with an initial frame
    api.begin_frame(False)
    api.draw_rectangle(0, 0, 64, 64, 'dark_gray', 30, True)
    api.end_frame()

    times = []
    for i in range(FRAMES):
        t0 = time.time()
        api.begin_frame(True)
        x = (i * 2) % 60
        y = int(32 + 20 * math.sin(i * 0.1))
        api.draw_circle(x, y, 3, 'cyan', 90, True)
        api.end_frame()
        times.append(time.time() - t0)
    return times


def bench_frame_true_with_bg(api):
    """begin_frame(true), with background."""
    setup_background(api)
    # Seed with an initial frame
    api.begin_frame(False)
    api.draw_rectangle(10, 10, 44, 44, 'dark_gray', 30, True)
    api.end_frame()

    times = []
    for i in range(FRAMES):
        t0 = time.time()
        api.begin_frame(True)
        x = (i * 2) % 60
        y = int(32 + 20 * math.sin(i * 0.1))
        api.draw_circle(x, y, 3, 'cyan', 90, True)
        api.end_frame()
        times.append(time.time() - t0)
    return times


def bench_sprite_no_bg(api):
    """Sprite movement, no background."""
    setup_sprite(api)
    api.show_sprite('bench_spr', 0, 28, 0, 0)
    times = []
    for i in range(FRAMES):
        t0 = time.time()
        x = i % 56
        y = int(28 + 15 * math.sin(i * 0.08))
        api.move_sprite('bench_spr', x, y, 0)
        times.append(time.time() - t0)
    return times


def bench_sprite_with_bg(api):
    """Sprite movement, with background."""
    setup_background(api)
    setup_sprite(api)
    api.show_sprite('bench_spr', 0, 28, 0, 0)
    times = []
    for i in range(FRAMES):
        t0 = time.time()
        x = i % 56
        y = int(28 + 15 * math.sin(i * 0.08))
        api.move_sprite('bench_spr', x, y, 0)
        times.append(time.time() - t0)
    return times


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  RGB Matrix Lib — Rendering Performance Benchmark")
    print("=" * 60)
    print(f"  Frames per test: {FRAMES}")
    print(f"  Target FPS: {TARGET_FPS}")
    print()

    api = RGB_Api()
    results = {}

    benchmarks = [
        ("Immediate - no bg",       bench_immediate_no_bg),
        ("Immediate - with bg",     bench_immediate_with_bg),
        ("frame(false) - no bg",    bench_frame_false_no_bg),
        ("frame(false) - with bg",  bench_frame_false_with_bg),
        ("frame(true) - no bg",     bench_frame_true_no_bg),
        ("frame(true) - with bg",   bench_frame_true_with_bg),
        ("Sprite move - no bg",     bench_sprite_no_bg),
        ("Sprite move - with bg",   bench_sprite_with_bg),
    ]

    for i, (name, bench_fn) in enumerate(benchmarks, 1):
        # Clean slate between benchmarks
        api.dispose_all_sprites()
        api.clear()
        time.sleep(0.2)

        print(f"  Running benchmark {i}/{len(benchmarks)}: {name}...")
        frame_times = bench_fn(api)
        avg = report(name, frame_times)
        results[name] = avg

        api.dispose_all_sprites()
        api.clear()

    # Summary comparison table
    print("=" * 60)
    print("  SUMMARY — Average frame time (ms)")
    print("=" * 60)
    print(f"  {'Benchmark':<28} {'Avg ms':>8}")
    print(f"  {'-'*28} {'-'*8}")
    for name, avg in results.items():
        print(f"  {name:<28} {avg*1000:8.1f}")

    # Paired comparisons
    print()
    print("  Impact of background on each mode:")
    print(f"  {'Mode':<22} {'No BG':>8} {'With BG':>8} {'Delta':>8} {'Ratio':>7}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8} {'-'*7}")
    pairs = [
        ("Immediate",   "Immediate - no bg",    "Immediate - with bg"),
        ("frame(false)", "frame(false) - no bg", "frame(false) - with bg"),
        ("frame(true)",  "frame(true) - no bg",  "frame(true) - with bg"),
        ("Sprite move",  "Sprite move - no bg",  "Sprite move - with bg"),
    ]
    for mode, no_bg_key, with_bg_key in pairs:
        no_bg = results[no_bg_key] * 1000
        with_bg = results[with_bg_key] * 1000
        delta = with_bg - no_bg
        ratio = with_bg / no_bg if no_bg > 0 else float('inf')
        print(f"  {mode:<22} {no_bg:7.1f}  {with_bg:7.1f}  {delta:+7.1f}  {ratio:6.2f}x")

    print()
    print("=" * 60)
    print("  Benchmark complete!")
    print("=" * 60)

    api.cleanup()


if __name__ == '__main__':
    main()