#!/usr/bin/env python3
"""
RGB Matrix Burnout Performance Benchmark
=========================================

This script benchmarks the performance impact of different burnout modes
by directly interfacing with rgb_matrix_lib.

Tests:
1. No burnout - baseline performance
2. Instant burnout - measures registration overhead
3. Fade burnout - measures registration + continuous fade processing

Metrics collected:
- Time to draw N pixels
- Time for burnout manager to process expirations
- CPU usage during rest periods (when fades are processing)

Usage:
    sudo python3 burnout_benchmark.py

Note: Must run as root for RGB matrix hardware access.
"""

import time
import statistics
import gc
import sys

# Add path if needed
sys.path.insert(0, '/home/pi/pixil')

from rgb_matrix_lib.api import RGB_Api


class BenchmarkResults:
    """Store and report benchmark results."""
    
    def __init__(self, name: str):
        self.name = name
        self.draw_times = []
        self.rest_times = []
        self.total_times = []
    
    def add_run(self, draw_time: float, rest_time: float, total_time: float):
        self.draw_times.append(draw_time)
        self.rest_times.append(rest_time)
        self.total_times.append(total_time)
    
    def report(self):
        print(f"\n{'='*60}")
        print(f"Results: {self.name}")
        print(f"{'='*60}")
        
        if not self.draw_times:
            print("  No data collected")
            return
        
        print(f"  Runs: {len(self.draw_times)}")
        print()
        
        # Draw times
        print(f"  Draw Time (plotting pixels):")
        print(f"    Mean:   {statistics.mean(self.draw_times)*1000:.2f} ms")
        print(f"    StdDev: {statistics.stdev(self.draw_times)*1000:.2f} ms" if len(self.draw_times) > 1 else "")
        print(f"    Min:    {min(self.draw_times)*1000:.2f} ms")
        print(f"    Max:    {max(self.draw_times)*1000:.2f} ms")
        print()
        
        # Rest times (includes burnout processing)
        print(f"  Rest Time (burnout processing):")
        print(f"    Mean:   {statistics.mean(self.rest_times)*1000:.2f} ms")
        print(f"    StdDev: {statistics.stdev(self.rest_times)*1000:.2f} ms" if len(self.rest_times) > 1 else "")
        print(f"    Min:    {min(self.rest_times)*1000:.2f} ms")
        print(f"    Max:    {max(self.rest_times)*1000:.2f} ms")
        print()
        
        # Total times
        print(f"  Total Time:")
        print(f"    Mean:   {statistics.mean(self.total_times)*1000:.2f} ms")
        print(f"    StdDev: {statistics.stdev(self.total_times)*1000:.2f} ms" if len(self.total_times) > 1 else "")
        print()
        
        # Pixels per second
        pixels_per_run = PIXELS_PER_TEST
        mean_draw_time = statistics.mean(self.draw_times)
        if mean_draw_time > 0:
            pixels_per_sec = pixels_per_run / mean_draw_time
            print(f"  Throughput: {pixels_per_sec:,.0f} pixels/second (draw phase)")


# Benchmark configuration
PIXELS_PER_TEST = 500      # Pixels to draw per test run
BURNOUT_DURATION_MS = 500  # Burnout time in milliseconds
REST_DURATION_SEC = 0.6    # Rest time (should be > burnout duration)
NUM_RUNS = 10              # Number of test runs per mode
WARMUP_RUNS = 2            # Warmup runs (discarded)


def generate_test_pixels(n: int):
    """Generate random pixel data for testing."""
    import random
    pixels = []
    for _ in range(n):
        x = random.randint(0, 63)
        y = random.randint(0, 63)
        # Use spectral color (0-99) for simplicity
        color = random.randint(0, 99)
        intensity = 100
        pixels.append((x, y, color, intensity))
    return pixels


def benchmark_no_burnout(api: RGB_Api, pixels: list, results: BenchmarkResults):
    """Benchmark drawing without any burnout."""
    api.clear()
    gc.collect()
    time.sleep(0.1)
    
    # Draw phase
    draw_start = time.perf_counter()
    for x, y, color, intensity in pixels:
        api.plot(x, y, color, intensity, None)  # No burnout
    draw_end = time.perf_counter()
    draw_time = draw_end - draw_start
    
    # Rest phase (nothing should happen)
    rest_start = time.perf_counter()
    api.rest(REST_DURATION_SEC)
    rest_end = time.perf_counter()
    rest_time = rest_end - rest_start
    
    total_time = draw_time + rest_time
    results.add_run(draw_time, rest_time, total_time)
    
    api.clear()


def benchmark_instant_burnout(api: RGB_Api, pixels: list, results: BenchmarkResults):
    """Benchmark drawing with instant burnout."""
    api.clear()
    gc.collect()
    time.sleep(0.1)
    
    # Draw phase
    draw_start = time.perf_counter()
    for x, y, color, intensity in pixels:
        api.plot(x, y, color, intensity, BURNOUT_DURATION_MS, "instant")
    draw_end = time.perf_counter()
    draw_time = draw_end - draw_start
    
    # Rest phase (burnout manager clears pixels at expiration)
    rest_start = time.perf_counter()
    api.rest(REST_DURATION_SEC)
    rest_end = time.perf_counter()
    rest_time = rest_end - rest_start
    
    total_time = draw_time + rest_time
    results.add_run(draw_time, rest_time, total_time)
    
    api.clear()


def benchmark_fade_burnout(api: RGB_Api, pixels: list, results: BenchmarkResults):
    """Benchmark drawing with fade burnout."""
    api.clear()
    gc.collect()
    time.sleep(0.1)
    
    # Draw phase
    draw_start = time.perf_counter()
    for x, y, color, intensity in pixels:
        api.plot(x, y, color, intensity, BURNOUT_DURATION_MS, "fade")
    draw_end = time.perf_counter()
    draw_time = draw_end - draw_start
    
    # Rest phase (burnout manager continuously updates fade intensity)
    rest_start = time.perf_counter()
    api.rest(REST_DURATION_SEC)
    rest_end = time.perf_counter()
    rest_time = rest_end - rest_start
    
    total_time = draw_time + rest_time
    results.add_run(draw_time, rest_time, total_time)
    
    api.clear()


def benchmark_batch_no_burnout(api: RGB_Api, pixels: list, results: BenchmarkResults):
    """Benchmark batch drawing without any burnout."""
    api.clear()
    gc.collect()
    time.sleep(0.1)
    
    # Prepare batch data
    batch_data = [(x, y, color, intensity, None) for x, y, color, intensity in pixels]
    
    # Draw phase
    draw_start = time.perf_counter()
    api.plot_batch(batch_data)
    draw_end = time.perf_counter()
    draw_time = draw_end - draw_start
    
    # Rest phase
    rest_start = time.perf_counter()
    api.rest(REST_DURATION_SEC)
    rest_end = time.perf_counter()
    rest_time = rest_end - rest_start
    
    total_time = draw_time + rest_time
    results.add_run(draw_time, rest_time, total_time)
    
    api.clear()


def benchmark_batch_instant_burnout(api: RGB_Api, pixels: list, results: BenchmarkResults):
    """Benchmark batch drawing with instant burnout."""
    api.clear()
    gc.collect()
    time.sleep(0.1)
    
    # Prepare batch data
    batch_data = [(x, y, color, intensity, BURNOUT_DURATION_MS, "instant") 
                  for x, y, color, intensity in pixels]
    
    # Draw phase
    draw_start = time.perf_counter()
    api.plot_batch(batch_data)
    draw_end = time.perf_counter()
    draw_time = draw_end - draw_start
    
    # Rest phase
    rest_start = time.perf_counter()
    api.rest(REST_DURATION_SEC)
    rest_end = time.perf_counter()
    rest_time = rest_end - rest_start
    
    total_time = draw_time + rest_time
    results.add_run(draw_time, rest_time, total_time)
    
    api.clear()


def benchmark_batch_fade_burnout(api: RGB_Api, pixels: list, results: BenchmarkResults):
    """Benchmark batch drawing with fade burnout."""
    api.clear()
    gc.collect()
    time.sleep(0.1)
    
    # Prepare batch data
    batch_data = [(x, y, color, intensity, BURNOUT_DURATION_MS, "fade") 
                  for x, y, color, intensity in pixels]
    
    # Draw phase
    draw_start = time.perf_counter()
    api.plot_batch(batch_data)
    draw_end = time.perf_counter()
    draw_time = draw_end - draw_start
    
    # Rest phase
    rest_start = time.perf_counter()
    api.rest(REST_DURATION_SEC)
    rest_end = time.perf_counter()
    rest_time = rest_end - rest_start
    
    total_time = draw_time + rest_time
    results.add_run(draw_time, rest_time, total_time)
    
    api.clear()


def run_benchmarks():
    """Run all benchmarks and report results."""
    print("="*60)
    print("RGB Matrix Burnout Performance Benchmark")
    print("="*60)
    print()
    print(f"Configuration:")
    print(f"  Pixels per test:    {PIXELS_PER_TEST}")
    print(f"  Burnout duration:   {BURNOUT_DURATION_MS} ms")
    print(f"  Rest duration:      {REST_DURATION_SEC} sec")
    print(f"  Test runs:          {NUM_RUNS}")
    print(f"  Warmup runs:        {WARMUP_RUNS}")
    print()
    
    # Initialize API
    print("Initializing RGB Matrix API...")
    api = RGB_Api()
    api.clear()
    time.sleep(0.5)
    
    # Generate test data
    print("Generating test pixel data...")
    pixels = generate_test_pixels(PIXELS_PER_TEST)
    
    # Results containers
    results_no_burnout = BenchmarkResults("Individual Plots - No Burnout")
    results_instant = BenchmarkResults("Individual Plots - Instant Burnout")
    results_fade = BenchmarkResults("Individual Plots - Fade Burnout")
    results_batch_no_burnout = BenchmarkResults("Batch Plots - No Burnout")
    results_batch_instant = BenchmarkResults("Batch Plots - Instant Burnout")
    results_batch_fade = BenchmarkResults("Batch Plots - Fade Burnout")
    
    total_runs = NUM_RUNS + WARMUP_RUNS
    
    # ===== Individual Plot Benchmarks =====
    print()
    print("-" * 40)
    print("Running Individual Plot Benchmarks...")
    print("-" * 40)
    
    # No burnout
    print(f"\n[1/6] No Burnout (individual plots):")
    for i in range(total_runs):
        is_warmup = i < WARMUP_RUNS
        prefix = "  Warmup" if is_warmup else "  Run"
        print(f"{prefix} {i+1}/{total_runs}...", end=" ", flush=True)
        
        if is_warmup:
            # Discard warmup results
            temp_results = BenchmarkResults("warmup")
            benchmark_no_burnout(api, pixels, temp_results)
        else:
            benchmark_no_burnout(api, pixels, results_no_burnout)
        print("done")
    
    # Instant burnout
    print(f"\n[2/6] Instant Burnout (individual plots):")
    for i in range(total_runs):
        is_warmup = i < WARMUP_RUNS
        prefix = "  Warmup" if is_warmup else "  Run"
        print(f"{prefix} {i+1}/{total_runs}...", end=" ", flush=True)
        
        if is_warmup:
            temp_results = BenchmarkResults("warmup")
            benchmark_instant_burnout(api, pixels, temp_results)
        else:
            benchmark_instant_burnout(api, pixels, results_instant)
        print("done")
    
    # Fade burnout
    print(f"\n[3/6] Fade Burnout (individual plots):")
    for i in range(total_runs):
        is_warmup = i < WARMUP_RUNS
        prefix = "  Warmup" if is_warmup else "  Run"
        print(f"{prefix} {i+1}/{total_runs}...", end=" ", flush=True)
        
        if is_warmup:
            temp_results = BenchmarkResults("warmup")
            benchmark_fade_burnout(api, pixels, temp_results)
        else:
            benchmark_fade_burnout(api, pixels, results_fade)
        print("done")
    
    # ===== Batch Plot Benchmarks =====
    print()
    print("-" * 40)
    print("Running Batch Plot Benchmarks...")
    print("-" * 40)
    
    # Batch no burnout
    print(f"\n[4/6] No Burnout (batch plots):")
    for i in range(total_runs):
        is_warmup = i < WARMUP_RUNS
        prefix = "  Warmup" if is_warmup else "  Run"
        print(f"{prefix} {i+1}/{total_runs}...", end=" ", flush=True)
        
        if is_warmup:
            temp_results = BenchmarkResults("warmup")
            benchmark_batch_no_burnout(api, pixels, temp_results)
        else:
            benchmark_batch_no_burnout(api, pixels, results_batch_no_burnout)
        print("done")
    
    # Batch instant burnout
    print(f"\n[5/6] Instant Burnout (batch plots):")
    for i in range(total_runs):
        is_warmup = i < WARMUP_RUNS
        prefix = "  Warmup" if is_warmup else "  Run"
        print(f"{prefix} {i+1}/{total_runs}...", end=" ", flush=True)
        
        if is_warmup:
            temp_results = BenchmarkResults("warmup")
            benchmark_batch_instant_burnout(api, pixels, temp_results)
        else:
            benchmark_batch_instant_burnout(api, pixels, results_batch_instant)
        print("done")
    
    # Batch fade burnout
    print(f"\n[6/6] Fade Burnout (batch plots):")
    for i in range(total_runs):
        is_warmup = i < WARMUP_RUNS
        prefix = "  Warmup" if is_warmup else "  Run"
        print(f"{prefix} {i+1}/{total_runs}...", end=" ", flush=True)
        
        if is_warmup:
            temp_results = BenchmarkResults("warmup")
            benchmark_batch_fade_burnout(api, pixels, temp_results)
        else:
            benchmark_batch_fade_burnout(api, pixels, results_batch_fade)
        print("done")
    
    # ===== Report Results =====
    print("\n")
    print("#" * 60)
    print("# BENCHMARK RESULTS")
    print("#" * 60)
    
    results_no_burnout.report()
    results_instant.report()
    results_fade.report()
    results_batch_no_burnout.report()
    results_batch_instant.report()
    results_batch_fade.report()
    
    # ===== Summary Comparison =====
    print("\n")
    print("=" * 60)
    print("SUMMARY COMPARISON")
    print("=" * 60)
    print()
    
    # Individual plots comparison
    print("Individual Plots - Draw Time Comparison:")
    baseline = statistics.mean(results_no_burnout.draw_times) * 1000
    instant_draw = statistics.mean(results_instant.draw_times) * 1000
    fade_draw = statistics.mean(results_fade.draw_times) * 1000
    print(f"  No Burnout:      {baseline:.2f} ms (baseline)")
    print(f"  Instant Burnout: {instant_draw:.2f} ms ({(instant_draw/baseline - 1)*100:+.1f}%)")
    print(f"  Fade Burnout:    {fade_draw:.2f} ms ({(fade_draw/baseline - 1)*100:+.1f}%)")
    print()
    
    print("Individual Plots - Rest Time Comparison:")
    baseline_rest = statistics.mean(results_no_burnout.rest_times) * 1000
    instant_rest = statistics.mean(results_instant.rest_times) * 1000
    fade_rest = statistics.mean(results_fade.rest_times) * 1000
    print(f"  No Burnout:      {baseline_rest:.2f} ms (baseline)")
    print(f"  Instant Burnout: {instant_rest:.2f} ms ({(instant_rest/baseline_rest - 1)*100:+.1f}%)")
    print(f"  Fade Burnout:    {fade_rest:.2f} ms ({(fade_rest/baseline_rest - 1)*100:+.1f}%)")
    print()
    
    # Batch plots comparison
    print("Batch Plots - Draw Time Comparison:")
    baseline_batch = statistics.mean(results_batch_no_burnout.draw_times) * 1000
    instant_batch_draw = statistics.mean(results_batch_instant.draw_times) * 1000
    fade_batch_draw = statistics.mean(results_batch_fade.draw_times) * 1000
    print(f"  No Burnout:      {baseline_batch:.2f} ms (baseline)")
    print(f"  Instant Burnout: {instant_batch_draw:.2f} ms ({(instant_batch_draw/baseline_batch - 1)*100:+.1f}%)")
    print(f"  Fade Burnout:    {fade_batch_draw:.2f} ms ({(fade_batch_draw/baseline_batch - 1)*100:+.1f}%)")
    print()
    
    print("Batch Plots - Rest Time Comparison:")
    baseline_batch_rest = statistics.mean(results_batch_no_burnout.rest_times) * 1000
    instant_batch_rest = statistics.mean(results_batch_instant.rest_times) * 1000
    fade_batch_rest = statistics.mean(results_batch_fade.rest_times) * 1000
    print(f"  No Burnout:      {baseline_batch_rest:.2f} ms (baseline)")
    print(f"  Instant Burnout: {instant_batch_rest:.2f} ms ({(instant_batch_rest/baseline_batch_rest - 1)*100:+.1f}%)")
    print(f"  Fade Burnout:    {fade_batch_rest:.2f} ms ({(fade_batch_rest/baseline_batch_rest - 1)*100:+.1f}%)")
    print()
    
    # Cleanup
    print("Cleaning up...")
    api.clear()
    api.burnout_manager.stop()
    print("Benchmark complete.")


if __name__ == "__main__":
    try:
        run_benchmarks()
    except KeyboardInterrupt:
        print("\nBenchmark interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)