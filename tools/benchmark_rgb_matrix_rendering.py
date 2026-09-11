#!/usr/bin/env python3
"""Measure RGB matrix rendering hot paths before and after renderer changes.

Default mode uses an in-memory canvas, so it measures Python-side command,
rasterization, and compositing cost without lighting the panel.  It also reports
the number of presents requested, which explains the cost of immediate mode.

Run a baseline before changing the renderer:
    python tools/benchmark_rgb_matrix_rendering.py --output /tmp/rgb-before.json

Run the same command afterwards and compare:
    python tools/benchmark_rgb_matrix_rendering.py \
        --output /tmp/rgb-after.json --compare /tmp/rgb-before.json

Use --hardware only on the Pi with the LED matrix connected.  That mode measures
real SwapOnVSync time and briefly displays the test patterns.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import types
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The default benchmark does not instantiate RGBMatrix.  Permit it to run on
# development machines where the hardware-only binding is unavailable.
try:
    import rgbmatrix  # noqa: F401
except ImportError:
    rgbmatrix_stub = types.ModuleType("rgbmatrix")
    rgbmatrix_stub.RGBMatrix = object
    rgbmatrix_stub.RGBMatrixOptions = object
    sys.modules["rgbmatrix"] = rgbmatrix_stub

from rgb_matrix_lib.api import RGB_Api
from rgb_matrix_lib.background import BackgroundManager
from rgb_matrix_lib.sprite import MatrixSprite, SpriteInstance, SpriteManager
from rgb_matrix_lib.utils import TRANSPARENT_COLOR


class MemoryCanvas:
    """Minimal FrameCanvas replacement that records renderer work."""

    def __init__(self) -> None:
        self.set_pixel_calls = 0
        self.set_image_calls = 0
        self.fill_calls = 0

    def SetPixel(self, _x: int, _y: int, _r: int, _g: int, _b: int) -> None:
        self.set_pixel_calls += 1

    def SetImage(self, _image) -> None:
        self.set_image_calls += 1

    def Fill(self, _r: int, _g: int, _b: int) -> None:
        self.fill_calls += 1


class MemoryMatrix:
    width = 64
    height = 64

    def __init__(self) -> None:
        self.swap_calls = 0

    def SwapOnVSync(self, canvas: MemoryCanvas) -> MemoryCanvas:
        self.swap_calls += 1
        return canvas


class NoBackground:
    def has_background(self) -> bool:
        return False


class NoSprites:
    z_order: list[tuple[str, int]] = []


def make_memory_api() -> RGB_Api:
    """Build only the state required by the measured render paths."""
    api = RGB_Api.__new__(RGB_Api)
    api.matrix = MemoryMatrix()
    api.canvas = MemoryCanvas()
    api.drawing_buffer = np.full((64, 64, 3), TRANSPARENT_COLOR, dtype=np.uint8)
    api.current_command_pixels = []
    api.frame_mode = False
    api.preserve_frame_changes = False
    api.background_manager = NoBackground()
    api.sprite_manager = NoSprites()
    api._frame_interval = 0.0
    api._last_present_time = 0.0
    return api


def sample(operation: Callable[[], None], iterations: int) -> list[float]:
    """Return operation durations in milliseconds after one warm-up run."""
    operation()
    durations = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        operation()
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    return durations


def stats(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))
    return {
        "median_ms": round(statistics.median(samples), 4),
        "mean_ms": round(statistics.fmean(samples), 4),
        "p95_ms": round(ordered[p95_index], 4),
    }


def benchmark_memory(iterations: int) -> dict:
    api = make_memory_api()

    def immediate_plots() -> None:
        api.frame_mode = False
        api.current_command_pixels.clear()
        for x in range(16):
            for y in range(16):
                api.plot(x, y, "red")

    def framed_plots() -> None:
        api.frame_mode = False
        api.current_command_pixels.clear()
        api.begin_frame()
        for x in range(16):
            for y in range(16):
                api.plot(x, y, "red")
        api.end_frame()

    rect_api = make_memory_api()

    def filled_rectangle() -> None:
        rect_api.frame_mode = True
        rect_api.draw_rectangle(0, 0, 64, 64, "blue", fill=True)

    shape_api = make_memory_api()
    shape_api.frame_mode = True

    def filled_circle() -> None:
        shape_api.draw_circle(32, 32, 31, "red", fill=True)

    def filled_polygon() -> None:
        shape_api.draw_polygon(32, 32, 31, 12, "green", rotation=7, fill=True)

    def filled_ellipse() -> None:
        shape_api.draw_ellipse(32, 32, 30, 20, "yellow", fill=True, rotation=27)

    sprite_api = make_memory_api()
    sprite_template = MatrixSprite(64, 64, "benchmark_sprite")
    sprite_template.buffer[:, :] = (37, 113, 251)
    sprite_template.intensity_buffer[:, :] = 73
    sprite_template.buffer[::4, ::4] = TRANSPARENT_COLOR
    sprite = SpriteInstance(sprite_template, 0, 0)

    def sprite_blit() -> None:
        sprite_api.copy_sprite_to_buffer(sprite, sprite_api.canvas)

    background_sprites = SpriteManager()
    background_template = MatrixSprite(16, 16, "benchmark_background")
    background_template.buffer[:, :] = (17, 83, 191)
    background_template.buffer[::3, ::3] = TRANSPARENT_COLOR
    background_template.intensity_buffer[:, :] = 81
    background_sprites.templates["benchmark_background"] = background_template
    background = BackgroundManager(background_sprites)
    background.set_background("benchmark_background")

    def static_background() -> None:
        background.get_viewport(64, 64)

    def moving_background() -> None:
        background.nudge(1, 1, cel_index=0)
        background.get_viewport(64, 64)

    immediate_before = api.matrix.swap_calls
    immediate = sample(immediate_plots, iterations)
    immediate_swaps = api.matrix.swap_calls - immediate_before
    frame_before = api.matrix.swap_calls
    framed = sample(framed_plots, iterations)
    framed_swaps = api.matrix.swap_calls - frame_before

    return {
        "mode": "memory",
        "iterations": iterations,
        "workloads": {
            "immediate_256_plots": {
                **stats(immediate),
                "presents_per_iteration": immediate_swaps / (iterations + 1),
            },
            "framed_256_plots": {
                **stats(framed),
                "presents_per_iteration": framed_swaps / (iterations + 1),
            },
            "filled_64x64_rectangle": stats(sample(filled_rectangle, iterations)),
            "filled_radius31_circle": stats(sample(filled_circle, iterations)),
            "filled_radius31_polygon_12_sides": stats(sample(filled_polygon, iterations)),
            "filled_30x20_rotated_ellipse": stats(sample(filled_ellipse, iterations)),
            "opaque_64x64_sprite_blit": stats(sample(sprite_blit, iterations)),
            "static_background_viewport": stats(sample(static_background, iterations)),
            "moving_background_viewport": stats(sample(moving_background, iterations)),
        },
    }


def benchmark_hardware(iterations: int) -> dict:
    """Measure present costs using the real RGB matrix; opt-in only."""
    if getattr(sys.modules["rgbmatrix"].RGBMatrix, "__name__", "") == "object":
        raise RuntimeError("The --hardware benchmark requires the rgbmatrix Python binding.")
    api = RGB_Api()
    api.reset_fps()

    def immediate_plots() -> None:
        api.clear()
        for x in range(16):
            for y in range(16):
                api.plot(x, y, "red")

    def framed_plots() -> None:
        api.clear()
        api.begin_frame()
        for x in range(16):
            for y in range(16):
                api.plot(x, y, "red")
        api.end_frame()

    try:
        return {
            "mode": "hardware",
            "iterations": iterations,
            "workloads": {
                "immediate_256_plots": stats(sample(immediate_plots, iterations)),
                "framed_256_plots": stats(sample(framed_plots, iterations)),
            },
        }
    finally:
        api.cleanup()


def compare(current: dict, baseline_path: Path) -> dict:
    baseline = json.loads(baseline_path.read_text())
    result = {}
    for name, values in current["workloads"].items():
        before = baseline.get("workloads", {}).get(name, {}).get("median_ms")
        after = values["median_ms"]
        if before and after:
            result[name] = {
                "before_median_ms": before,
                "after_median_ms": after,
                "speedup": round(before / after, 3),
            }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=100, help="samples per workload")
    parser.add_argument("--hardware", action="store_true", help="use the physical LED matrix")
    parser.add_argument("--output", type=Path, help="write complete JSON results")
    parser.add_argument("--compare", type=Path, help="baseline JSON to compare against")
    args = parser.parse_args()
    if args.iterations < 2:
        parser.error("--iterations must be at least 2")

    result = benchmark_hardware(args.iterations) if args.hardware else benchmark_memory(args.iterations)
    if args.compare:
        result["comparison"] = compare(result, args.compare)

    formatted = json.dumps(result, indent=2)
    print(formatted)
    if args.output:
        args.output.write_text(formatted + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
