#!/usr/bin/env python3
"""
Background Sprite POC - Performance Test

Tests the viability of using a large sprite as a scrolling background layer.
The background pattern is larger than the 64x64 display and we render a 
viewport that moves in a circular pattern.

Performance targets:
- 30+ FPS for smooth animation
- <33ms per frame total
"""

from rgbmatrix import RGBMatrix, RGBMatrixOptions
import numpy as np
import time
import math
from PIL import Image

# Display constants
DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 64

# Background pattern size (larger than display for scrolling)
BG_WIDTH = 128
BG_HEIGHT = 128


class BackgroundSprite:
    """A large pattern that can be rendered as a tiling background."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        # RGB buffer for the pattern
        self.buffer = np.zeros((height, width, 3), dtype=np.uint8)
    
    def plot(self, x: int, y: int, r: int, g: int, b: int):
        """Draw a single pixel to the pattern."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = [r, g, b]
    
    def draw_circle(self, cx: int, cy: int, radius: int, r: int, g: int, b: int, filled: bool = False):
        """Draw a circle to the pattern."""
        for y in range(max(0, cy - radius), min(self.height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.width, cx + radius + 1)):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if filled:
                    if dist <= radius:
                        self.buffer[y, x] = [r, g, b]
                else:
                    if abs(dist - radius) < 1.0:
                        self.buffer[y, x] = [r, g, b]
    
    def get_viewport(self, offset_x: int, offset_y: int, 
                     view_width: int = DISPLAY_WIDTH, 
                     view_height: int = DISPLAY_HEIGHT) -> np.ndarray:
        """
        Extract a viewport from the pattern with tiling/wrapping.
        
        This is the critical performance path - needs to be fast!
        """
        # Normalize offsets to pattern bounds
        offset_x = offset_x % self.width
        offset_y = offset_y % self.height
        
        # Create output buffer
        viewport = np.zeros((view_height, view_width, 3), dtype=np.uint8)
        
        # Calculate how the viewport maps to the pattern (handling wrap)
        for vy in range(view_height):
            src_y = (offset_y + vy) % self.height
            for vx in range(view_width):
                src_x = (offset_x + vx) % self.width
                viewport[vy, vx] = self.buffer[src_y, src_x]
        
        return viewport
    
    def get_viewport_fast(self, offset_x: int, offset_y: int,
                          view_width: int = DISPLAY_WIDTH,
                          view_height: int = DISPLAY_HEIGHT) -> np.ndarray:
        """
        Optimized viewport extraction using numpy operations.
        Handles tiling by pre-computing indices.
        """
        # Normalize offsets
        offset_x = offset_x % self.width
        offset_y = offset_y % self.height
        
        # Create index arrays for tiled lookup
        y_indices = (np.arange(view_height) + offset_y) % self.height
        x_indices = (np.arange(view_width) + offset_x) % self.width
        
        # Use advanced indexing - numpy handles this efficiently
        # np.ix_ creates an open mesh from index arrays
        viewport = self.buffer[np.ix_(y_indices, x_indices)]
        
        return viewport


def configure_matrix() -> RGBMatrix:
    """Configure and return the LED matrix."""
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


def create_test_pattern(bg: BackgroundSprite):
    """Create a visually interesting test pattern."""
    print("Creating test pattern...")
    
    # Starfield background
    np.random.seed(42)  # Reproducible pattern
    for _ in range(300):
        x = np.random.randint(0, bg.width)
        y = np.random.randint(0, bg.height)
        brightness = np.random.randint(30, 100)
        gray = int(255 * brightness / 100)
        bg.plot(x, y, gray, gray, gray)
    
    # Some colored circles to make movement obvious
    bg.draw_circle(32, 32, 15, 255, 0, 0, filled=True)      # Red
    bg.draw_circle(96, 32, 15, 0, 255, 0, filled=True)      # Green
    bg.draw_circle(32, 96, 15, 0, 0, 255, filled=True)      # Blue
    bg.draw_circle(96, 96, 15, 255, 255, 0, filled=True)    # Yellow
    bg.draw_circle(64, 64, 10, 255, 0, 255, filled=True)    # Magenta center
    
    # Grid lines to see scrolling clearly
    for x in range(0, bg.width, 16):
        for y in range(bg.height):
            bg.plot(x, y, 40, 40, 40)
    for y in range(0, bg.height, 16):
        for x in range(bg.width):
            bg.plot(x, y, 40, 40, 40)
    
    print(f"Pattern created: {bg.width}x{bg.height}")


def calculate_scroll_offset(elapsed: float, pattern_width: int, pattern_height: int) -> tuple:
    """
    Calculate consistent circular scroll offset.
    Used by all tests for apples-to-apples comparison.
    
    Returns (offset_x, offset_y) for the viewport position.
    """
    # Circular motion parameters - consistent across all tests
    center_x = pattern_width // 2
    center_y = pattern_height // 2
    radius = 20  # Pixels of circular motion
    rotation_speed = 1.0  # Rotations per second
    
    angle = elapsed * rotation_speed * 2 * math.pi
    offset_x = int(center_x + radius * math.cos(angle))
    offset_y = int(center_y + radius * math.sin(angle))
    
    return offset_x, offset_y


def run_performance_test(matrix: RGBMatrix, bg: BackgroundSprite, 
                         use_fast_viewport: bool, duration: float = 10.0):
    """
    Run the circular scrolling test and measure performance.
    
    Args:
        matrix: The LED matrix
        bg: Background sprite pattern
        use_fast_viewport: If True, use numpy-optimized viewport extraction
        duration: How long to run the test in seconds
    """
    method_name = "FAST (numpy)" if use_fast_viewport else "SLOW (loop)"
    print(f"\n--- Testing {method_name} viewport method ---")
    
    canvas = matrix.CreateFrameCanvas()
    
    frame_times = []
    viewport_times = []
    render_times = []
    
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        
        # Calculate viewport offset (consistent circular motion)
        elapsed = time.time() - start_time
        offset_x, offset_y = calculate_scroll_offset(elapsed, bg.width, bg.height)
        
        # Extract viewport (this is what we're testing)
        vp_start = time.time()
        if use_fast_viewport:
            viewport = bg.get_viewport_fast(offset_x, offset_y)
        else:
            viewport = bg.get_viewport(offset_x, offset_y)
        vp_time = time.time() - vp_start
        viewport_times.append(vp_time)
        
        # Render to canvas
        render_start = time.time()
        pil_image = Image.fromarray(viewport, mode='RGB')
        canvas.SetImage(pil_image)
        canvas = matrix.SwapOnVSync(canvas)
        render_time = time.time() - render_start
        render_times.append(render_time)
        
        frame_time = time.time() - frame_start
        frame_times.append(frame_time)
        frame_count += 1
    
    # Report results
    avg_frame = np.mean(frame_times) * 1000
    avg_viewport = np.mean(viewport_times) * 1000
    avg_render = np.mean(render_times) * 1000
    fps = frame_count / duration
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    print(f"  Avg viewport extraction: {avg_viewport:.3f}ms")
    print(f"  Avg render time: {avg_render:.2f}ms")
    print(f"  Min/Max frame: {min(frame_times)*1000:.2f}ms / {max(frame_times)*1000:.2f}ms")
    
    return fps, avg_frame, avg_viewport


def run_tiling_test(matrix: RGBMatrix, duration: float = 10.0):
    """
    Test with a small pattern that tiles to fill the display.
    This tests the efficiency of tiled rendering with a small source.
    """
    print("\n--- Testing SMALL pattern (32x32) with tiling ---")
    
    # Small pattern that will tile
    small_bg = BackgroundSprite(32, 32)
    
    # Create a simple tiling pattern
    small_bg.draw_circle(16, 16, 10, 255, 100, 0, filled=True)
    for x in range(0, 32, 8):
        for y in range(32):
            small_bg.plot(x, y, 50, 50, 50)
    for y in range(0, 32, 8):
        for x in range(32):
            small_bg.plot(x, y, 50, 50, 50)
    
    canvas = matrix.CreateFrameCanvas()
    
    frame_times = []
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        
        # Use consistent circular scroll pattern
        elapsed = time.time() - start_time
        offset_x, offset_y = calculate_scroll_offset(elapsed, small_bg.width, small_bg.height)
        
        viewport = small_bg.get_viewport_fast(offset_x, offset_y)
        
        pil_image = Image.fromarray(viewport, mode='RGB')
        canvas.SetImage(pil_image)
        canvas = matrix.SwapOnVSync(canvas)
        
        frame_times.append(time.time() - frame_start)
        frame_count += 1
    
    fps = frame_count / duration
    avg_frame = np.mean(frame_times) * 1000
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    
    return fps


def run_composite_test(matrix: RGBMatrix, bg: BackgroundSprite, duration: float = 10.0):
    """
    Test background + drawing buffer compositing.
    This simulates the full layer stack (minus sprites).
    """
    print("\n--- Testing COMPOSITE (background + drawing buffer) ---")
    
    # Simulate a drawing buffer with some content
    drawing_buffer = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)
    
    # Draw some "persistent" content
    for x in range(20, 44):
        for y in range(20, 44):
            drawing_buffer[y, x] = [0, 255, 255]  # Cyan square
    # Add a circle
    for y in range(DISPLAY_HEIGHT):
        for x in range(DISPLAY_WIDTH):
            if math.sqrt((x - 50) ** 2 + (y - 50) ** 2) < 8:
                drawing_buffer[y, x] = [255, 0, 255]  # Magenta circle
    
    canvas = matrix.CreateFrameCanvas()
    
    frame_times = []
    composite_times = []
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        
        # Use consistent circular scroll pattern
        elapsed = time.time() - start_time
        offset_x, offset_y = calculate_scroll_offset(elapsed, bg.width, bg.height)
        
        viewport = bg.get_viewport_fast(offset_x, offset_y)
        
        # Composite drawing buffer on top (black = transparent)
        comp_start = time.time()
        # Create mask where drawing_buffer is non-black
        mask = np.any(drawing_buffer != 0, axis=2)
        # Apply drawing buffer where mask is true
        viewport[mask] = drawing_buffer[mask]
        composite_times.append(time.time() - comp_start)
        
        # Render
        pil_image = Image.fromarray(viewport, mode='RGB')
        canvas.SetImage(pil_image)
        canvas = matrix.SwapOnVSync(canvas)
        
        frame_times.append(time.time() - frame_start)
        frame_count += 1
    
    fps = frame_count / duration
    avg_frame = np.mean(frame_times) * 1000
    avg_composite = np.mean(composite_times) * 1000
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    print(f"  Avg composite time: {avg_composite:.3f}ms")
    
    return fps


def main():
    print("=" * 60)
    print("Background Sprite POC - Performance Test")
    print("=" * 60)
    
    # Initialize matrix
    print("\nInitializing LED matrix...")
    matrix = configure_matrix()
    
    # Create background pattern
    bg = BackgroundSprite(BG_WIDTH, BG_HEIGHT)
    create_test_pattern(bg)
    
    test_duration = 8.0  # Seconds per test
    
    try:
        # Test 1: Slow viewport (baseline)
        fps_slow, _, vp_slow = run_performance_test(matrix, bg, use_fast_viewport=False, duration=test_duration)
        
        # Brief pause
        time.sleep(1)
        
        # Test 2: Fast viewport (numpy optimized)
        fps_fast, _, vp_fast = run_performance_test(matrix, bg, use_fast_viewport=True, duration=test_duration)
        
        time.sleep(1)
        
        # Test 3: Small tiling pattern
        fps_tile = run_tiling_test(matrix, duration=test_duration)
        
        time.sleep(1)
        
        # Test 4: Full composite test
        fps_composite = run_composite_test(matrix, bg, duration=test_duration)
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  Slow viewport:    {fps_slow:.1f} FPS (viewport: {vp_slow:.3f}ms)")
        print(f"  Fast viewport:    {fps_fast:.1f} FPS (viewport: {vp_fast:.3f}ms)")
        print(f"  Small tiled:      {fps_tile:.1f} FPS")
        print(f"  Full composite:   {fps_composite:.1f} FPS")
        print()
        print(f"  Speedup (fast vs slow): {vp_slow/vp_fast:.1f}x")
        print()
        if fps_composite >= 30:
            print("  ✓ VIABLE - Composite rendering achieves 30+ FPS")
        else:
            print("  ✗ NEEDS OPTIMIZATION - Below 30 FPS target")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        # Clear display
        canvas = matrix.CreateFrameCanvas()
        canvas.Fill(0, 0, 0)
        matrix.SwapOnVSync(canvas)
        print("\nTest complete - display cleared")


if __name__ == "__main__":
    main()