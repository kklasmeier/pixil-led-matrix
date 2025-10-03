# File: benchmark_drawing.py

"""
Benchmark script to compare current pixel list approach vs PIL Image approach
for canvas swapping in the RGB Matrix API.

Tests three scenarios:
1. Non-frame mode (swap after each command)
2. Frame mode with preservation
3. Frame mode without preservation

Three workload densities:
- Sparse: ~200-500 pixels
- Medium: ~1500-2500 pixels  
- Dense: ~4000-6000 pixels
"""

import time
import sys
from rgb_matrix_lib.api import RGB_Api
from PIL import Image
import numpy as np

# Benchmark configuration
ITERATIONS = 100  # Number of frames to test per scenario
WARMUP_ITERATIONS = 10  # Warmup iterations to stabilize timing

class BenchmarkResults:
    """Store and display benchmark results."""
    def __init__(self, name):
        self.name = name
        self.times = []
    
    def add_time(self, elapsed):
        self.times.append(elapsed)
    
    def get_stats(self):
        if not self.times:
            return None
        avg = sum(self.times) / len(self.times)
        min_time = min(self.times)
        max_time = max(self.times)
        fps = 1.0 / avg if avg > 0 else 0
        return {
            'avg_ms': avg * 1000,
            'min_ms': min_time * 1000,
            'max_ms': max_time * 1000,
            'fps': fps
        }
    
    def print_stats(self):
        stats = self.get_stats()
        if stats:
            print(f"\n{self.name}:")
            print(f"  Avg: {stats['avg_ms']:.2f}ms ({stats['fps']:.1f} FPS)")
            print(f"  Min: {stats['min_ms']:.2f}ms")
            print(f"  Max: {stats['max_ms']:.2f}ms")


class WorkloadGenerator:
    """Generate different drawing workloads."""
    
    @staticmethod
    def sparse(api):
        """Sparse workload: ~200-500 pixels"""
        api.draw_circle(20, 20, 8, "red", 100, True)
        api.draw_circle(44, 44, 8, "blue", 100, True)
        api.draw_line(10, 10, 54, 54, "green", 100)
    
    @staticmethod
    def medium(api):
        """Medium workload: ~1500-2500 pixels"""
        api.draw_rectangle(5, 5, 54, 54, "blue", 100, False)
        api.draw_circle(32, 32, 20, "red", 100, True)
        api.draw_polygon(32, 32, 15, 6, "yellow", 100, 0, False)
        api.draw_line(0, 0, 63, 63, "green", 100)
        api.draw_line(0, 63, 63, 0, "green", 100)
    
    @staticmethod
    def dense(api):
        """Dense workload: ~4000-6000 pixels"""
        api.draw_rectangle(0, 0, 64, 64, "navy", 100, True)
        api.draw_circle(32, 32, 28, "red", 100, True)
        api.draw_circle(32, 32, 20, "yellow", 100, True)
        api.draw_circle(32, 32, 12, "white", 100, True)
        for i in range(0, 64, 8):
            api.draw_line(i, 0, 63-i, 63, "cyan", 80)
        api.draw_polygon(32, 32, 25, 8, "purple", 100, 0, False)


class BenchmarkAPI(RGB_Api):
    """Extended RGB_Api with PIL swap capability for benchmarking."""
    
    def __init__(self):
        super().__init__()
        self.use_pil_approach = False
    
    def _maybe_swap_buffer(self):
        """Override to support both approaches based on flag."""
        if not self.frame_mode:
            if self.use_pil_approach:
                self._maybe_swap_buffer_pil()
            else:
                self._maybe_swap_buffer_original()
    
    def _maybe_swap_buffer_original(self):
        """Current approach: pixel list + redraw."""
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        for x, y, r, g, b in self.current_command_pixels:
            self.canvas.SetPixel(x, y, r, g, b)
        self.current_command_pixels.clear()
    
    def _maybe_swap_buffer_pil(self):
        """PIL approach: numpy → PIL → SetImage."""
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        pil_image = Image.fromarray(self.drawing_buffer, mode='RGB')
        self.canvas.SetImage(pil_image)
        self.current_command_pixels.clear()
    
    def end_frame(self):
        """Override end_frame to support both approaches."""
        if self.frame_mode:
            if self.use_pil_approach:
                self._end_frame_pil()
            else:
                self._end_frame_original()
    
    def _end_frame_original(self):
        """Current end_frame implementation."""
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        for y in range(self.matrix.height):
            for x in range(self.matrix.width):
                r, g, b = self.drawing_buffer[y, x]
                self.canvas.SetPixel(x, y, int(r), int(g), int(b))
        if self.preserve_frame_changes:
            for x, y, r, g, b in self.current_command_pixels:
                self.canvas.SetPixel(x, y, r, g, b)
            self.current_command_pixels.clear()
        else:
            self.canvas.Fill(0, 0, 0)
        self.frame_mode = False
        self.preserve_frame_changes = False
    
    def _end_frame_pil(self):
        """PIL-based end_frame implementation."""
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        pil_image = Image.fromarray(self.drawing_buffer, mode='RGB')
        self.canvas.SetImage(pil_image)
        if self.preserve_frame_changes:
            # Preserve mode: keep current_command_pixels for next operation
            self.current_command_pixels.clear()
        else:
            # No preserve: clear canvas
            self.canvas.Fill(0, 0, 0)
        self.frame_mode = False
        self.preserve_frame_changes = False


def benchmark_non_frame_mode(api, workload_func, workload_name, use_pil):
    """Benchmark non-frame mode."""
    approach = "PIL" if use_pil else "Current"
    results = BenchmarkResults(f"{workload_name} - Non-Frame - {approach}")
    
    api.use_pil_approach = use_pil
    api.clear()
    
    # Warmup
    for _ in range(WARMUP_ITERATIONS):
        workload_func(api)
        api.clear()
    
    # Actual benchmark
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        workload_func(api)
        elapsed = time.perf_counter() - start
        results.add_time(elapsed)
        api.clear()
    
    return results


def benchmark_frame_mode(api, workload_func, workload_name, use_pil, preserve):
    """Benchmark frame mode."""
    approach = "PIL" if use_pil else "Current"
    mode = "Preserve" if preserve else "No-Preserve"
    results = BenchmarkResults(f"{workload_name} - Frame-{mode} - {approach}")
    
    api.use_pil_approach = use_pil
    api.clear()
    
    # Warmup
    for _ in range(WARMUP_ITERATIONS):
        api.begin_frame(preserve)
        workload_func(api)
        api.end_frame()
    
    # Actual benchmark
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        api.begin_frame(preserve)
        workload_func(api)
        api.end_frame()
        elapsed = time.perf_counter() - start
        results.add_time(elapsed)
    
    return results


def run_all_benchmarks():
    """Run complete benchmark suite."""
    print("=" * 70)
    print("RGB Matrix Drawing Performance Benchmark")
    print("=" * 70)
    print(f"Iterations per test: {ITERATIONS}")
    print(f"Warmup iterations: {WARMUP_ITERATIONS}")
    print()
    
    try:
        api = BenchmarkAPI()
        print("API initialized successfully\n")
        
        workloads = [
            (WorkloadGenerator.sparse, "Sparse (~200-500 px)"),
            (WorkloadGenerator.medium, "Medium (~1500-2500 px)"),
            (WorkloadGenerator.dense, "Dense (~4000-6000 px)")
        ]
        
        all_results = []
        
        for workload_func, workload_name in workloads:
            print(f"\n{'=' * 70}")
            print(f"Testing: {workload_name}")
            print('=' * 70)
            
            # Non-frame mode
            print("\n--- Non-Frame Mode ---")
            result_current = benchmark_non_frame_mode(api, workload_func, workload_name, False)
            result_current.print_stats()
            all_results.append(result_current)
            
            result_pil = benchmark_non_frame_mode(api, workload_func, workload_name, True)
            result_pil.print_stats()
            all_results.append(result_pil)
            
            # Calculate speedup/slowdown
            stats_current = result_current.get_stats()
            stats_pil = result_pil.get_stats()
            if stats_current and stats_pil:
                ratio = stats_pil['avg_ms'] / stats_current['avg_ms']
                if ratio < 1.0:
                    print(f"  → PIL is {(1.0 - ratio) * 100:.1f}% faster")
                else:
                    print(f"  → PIL is {(ratio - 1.0) * 100:.1f}% slower")
            
            # Frame mode with preservation
            print("\n--- Frame Mode (Preserve) ---")
            result_current = benchmark_frame_mode(api, workload_func, workload_name, False, True)
            result_current.print_stats()
            all_results.append(result_current)
            
            result_pil = benchmark_frame_mode(api, workload_func, workload_name, True, True)
            result_pil.print_stats()
            all_results.append(result_pil)
            
            stats_current = result_current.get_stats()
            stats_pil = result_pil.get_stats()
            if stats_current and stats_pil:
                ratio = stats_pil['avg_ms'] / stats_current['avg_ms']
                if ratio < 1.0:
                    print(f"  → PIL is {(1.0 - ratio) * 100:.1f}% faster")
                else:
                    print(f"  → PIL is {(ratio - 1.0) * 100:.1f}% slower")
            
            # Frame mode without preservation
            print("\n--- Frame Mode (No-Preserve) ---")
            result_current = benchmark_frame_mode(api, workload_func, workload_name, False, False)
            result_current.print_stats()
            all_results.append(result_current)
            
            result_pil = benchmark_frame_mode(api, workload_func, workload_name, True, False)
            result_pil.print_stats()
            all_results.append(result_pil)
            
            stats_current = result_current.get_stats()
            stats_pil = result_pil.get_stats()
            if stats_current and stats_pil:
                ratio = stats_pil['avg_ms'] / stats_current['avg_ms']
                if ratio < 1.0:
                    print(f"  → PIL is {(1.0 - ratio) * 100:.1f}% faster")
                else:
                    print(f"  → PIL is {(ratio - 1.0) * 100:.1f}% slower")
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        for result in all_results:
            result.print_stats()
        
        api.cleanup()
        
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        if 'api' in locals():
            api.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n\nBenchmark failed with error: {e}")
        if 'api' in locals():
            api.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    run_all_benchmarks()