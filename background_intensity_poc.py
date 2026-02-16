#!/usr/bin/env python3
"""
Background Intensity POC - Performance Test

Tests the overhead of applying intensity buffer during viewport extraction.
Compares:
1. No intensity (just color buffer)
2. With intensity application (color * intensity / 100)
"""

from rgbmatrix import RGBMatrix, RGBMatrixOptions
import numpy as np
import time
import math
from PIL import Image

DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 64
BG_WIDTH = 128
BG_HEIGHT = 128


class BackgroundWithIntensity:
    """Background pattern with separate intensity buffer (like MatrixSprite)."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.buffer = np.zeros((height, width, 3), dtype=np.uint8)
        self.intensity_buffer = np.full((height, width), 100, dtype=np.uint8)
        self.offset_x = 0
        self.offset_y = 0
    
    def plot(self, x: int, y: int, r: int, g: int, b: int, intensity: int = 100):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = [r, g, b]
            self.intensity_buffer[y, x] = intensity
    
    def get_viewport_no_intensity(self) -> np.ndarray:
        """Extract viewport WITHOUT applying intensity."""
        y_indices = (np.arange(DISPLAY_HEIGHT) + self.offset_y) % self.height
        x_indices = (np.arange(DISPLAY_WIDTH) + self.offset_x) % self.width
        return self.buffer[np.ix_(y_indices, x_indices)].copy()
    
    def get_viewport_with_intensity(self) -> np.ndarray:
        """Extract viewport WITH intensity application."""
        y_indices = (np.arange(DISPLAY_HEIGHT) + self.offset_y) % self.height
        x_indices = (np.arange(DISPLAY_WIDTH) + self.offset_x) % self.width
        
        color_view = self.buffer[np.ix_(y_indices, x_indices)]
        intensity_view = self.intensity_buffer[np.ix_(y_indices, x_indices)]
        
        # Apply intensity: RGB * (intensity / 100)
        scaled = color_view * (intensity_view[:, :, np.newaxis] / 100.0)
        return scaled.astype(np.uint8)
    
    def get_viewport_with_intensity_v2(self) -> np.ndarray:
        """Alternative: integer math to avoid float conversion."""
        y_indices = (np.arange(DISPLAY_HEIGHT) + self.offset_y) % self.height
        x_indices = (np.arange(DISPLAY_WIDTH) + self.offset_x) % self.width
        
        color_view = self.buffer[np.ix_(y_indices, x_indices)].astype(np.uint16)
        intensity_view = self.intensity_buffer[np.ix_(y_indices, x_indices)].astype(np.uint16)
        
        # Integer math: (RGB * intensity) // 100
        scaled = (color_view * intensity_view[:, :, np.newaxis]) // 100
        return scaled.astype(np.uint8)


def configure_matrix() -> RGBMatrix:
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 3
    options.scan_mode = 1
    options.pwm_bits = 11
    options.brightness = 100
    options.limit_refresh_rate_hz = 0
    return RGBMatrix(options=options)


def create_test_pattern(bg: BackgroundWithIntensity):
    """Create pattern with varying intensities."""
    print("Creating test pattern with varying intensities...")
    
    np.random.seed(42)
    
    # Stars with random intensities
    for _ in range(300):
        x = np.random.randint(0, bg.width)
        y = np.random.randint(0, bg.height)
        intensity = np.random.randint(30, 100)
        bg.plot(x, y, 255, 255, 255, intensity)
    
    # Colored circles with different intensities
    for cy in range(32, bg.height, 64):
        for cx in range(32, bg.width, 64):
            intensity = np.random.randint(50, 100)
            for dy in range(-15, 16):
                for dx in range(-15, 16):
                    if dx*dx + dy*dy <= 225:  # radius 15
                        bg.plot(cx + dx, cy + dy, 255, 0, 0, intensity)
    
    # Grid at 50% intensity
    for x in range(0, bg.width, 16):
        for y in range(bg.height):
            bg.plot(x, y, 100, 100, 100, 50)
    for y in range(0, bg.height, 16):
        for x in range(bg.width):
            bg.plot(x, y, 100, 100, 100, 50)
    
    print(f"Pattern created: {bg.width}x{bg.height}")


def calculate_scroll_offset(elapsed: float, width: int, height: int) -> tuple:
    center_x = width // 2
    center_y = height // 2
    radius = 20
    rotation_speed = 1.0
    angle = elapsed * rotation_speed * 2 * math.pi
    offset_x = int(center_x + radius * math.cos(angle))
    offset_y = int(center_y + radius * math.sin(angle))
    return offset_x, offset_y


def run_test(matrix: RGBMatrix, bg: BackgroundWithIntensity, 
             viewport_method: str, duration: float = 8.0):
    """Run a single test with specified viewport method."""
    
    print(f"\n--- Testing: {viewport_method} ---")
    
    canvas = matrix.CreateFrameCanvas()
    
    frame_times = []
    viewport_times = []
    
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        elapsed = time.time() - start_time
        
        # Update offset
        bg.offset_x, bg.offset_y = calculate_scroll_offset(elapsed, bg.width, bg.height)
        
        # Extract viewport using specified method
        vp_start = time.time()
        if viewport_method == "no_intensity":
            viewport = bg.get_viewport_no_intensity()
        elif viewport_method == "with_intensity_float":
            viewport = bg.get_viewport_with_intensity()
        elif viewport_method == "with_intensity_int":
            viewport = bg.get_viewport_with_intensity_v2()
        viewport_times.append(time.time() - vp_start)
        
        # Render
        pil_image = Image.fromarray(viewport, mode='RGB')
        canvas.SetImage(pil_image)
        canvas = matrix.SwapOnVSync(canvas)
        
        frame_times.append(time.time() - frame_start)
        frame_count += 1
    
    fps = frame_count / duration
    avg_frame = np.mean(frame_times) * 1000
    avg_viewport = np.mean(viewport_times) * 1000
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    print(f"  Avg viewport extraction: {avg_viewport:.3f}ms")
    
    return fps, avg_frame, avg_viewport


def main():
    print("=" * 60)
    print("Background Intensity POC - Performance Test")
    print("=" * 60)
    
    matrix = configure_matrix()
    bg = BackgroundWithIntensity(BG_WIDTH, BG_HEIGHT)
    create_test_pattern(bg)
    
    test_duration = 8.0
    results = {}
    
    try:
        # Test 1: No intensity
        fps1, frame1, vp1 = run_test(matrix, bg, "no_intensity", test_duration)
        results['no_intensity'] = (fps1, frame1, vp1)
        time.sleep(1)
        
        # Test 2: With intensity (float math)
        fps2, frame2, vp2 = run_test(matrix, bg, "with_intensity_float", test_duration)
        results['with_intensity_float'] = (fps2, frame2, vp2)
        time.sleep(1)
        
        # Test 3: With intensity (integer math)
        fps3, frame3, vp3 = run_test(matrix, bg, "with_intensity_int", test_duration)
        results['with_intensity_int'] = (fps3, frame3, vp3)
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  {'Method':<30} {'FPS':>8} {'Frame ms':>10} {'Viewport ms':>12}")
        print(f"  {'-'*30} {'-'*8} {'-'*10} {'-'*12}")
        print(f"  {'No intensity (baseline)':<30} {fps1:>8.1f} {frame1:>10.2f} {vp1:>12.3f}")
        print(f"  {'With intensity (float)':<30} {fps2:>8.1f} {frame2:>10.2f} {vp2:>12.3f}")
        print(f"  {'With intensity (integer)':<30} {fps3:>8.1f} {frame3:>10.2f} {vp3:>12.3f}")
        print()
        
        # Calculate overhead
        overhead_float = ((vp2 - vp1) / vp1) * 100 if vp1 > 0 else 0
        overhead_int = ((vp3 - vp1) / vp1) * 100 if vp1 > 0 else 0
        
        print(f"  Intensity overhead (float): {overhead_float:+.1f}%")
        print(f"  Intensity overhead (int):   {overhead_int:+.1f}%")
        print()
        
        if min(fps1, fps2, fps3) >= 30:
            print("  ✓ ALL METHODS VIABLE - 30+ FPS achieved")
        else:
            print("  ⚠ Some methods below 30 FPS")
        
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        canvas = matrix.CreateFrameCanvas()
        canvas.Fill(0, 0, 0)
        matrix.SwapOnVSync(canvas)
        print("\nTest complete")


if __name__ == "__main__":
    main()