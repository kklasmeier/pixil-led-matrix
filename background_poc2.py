#!/usr/bin/env python3
"""
Background Sprite POC v2 - Accurate Architecture Test

This POC accurately mirrors the api.py architecture:
- Double-buffered canvas with SwapOnVSync
- drawing_buffer (persistent layer)
- current_command_pixels for back buffer rebuild
- Sprite compositing with transparency
- Frame mode vs immediate mode

Tests adding a background layer underneath everything.

Layer stack (bottom to top):
1. Background pattern (NEW) - large scrollable pattern
2. Drawing buffer (existing) - persistent drawings, black = transparent over background
3. Sprites (existing) - composited last with transparency
"""

from rgbmatrix import RGBMatrix, RGBMatrixOptions
import numpy as np
import time
import math
from PIL import Image
from typing import List, Tuple, Optional

# Display constants
DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 64

# Background pattern size
BG_WIDTH = 128
BG_HEIGHT = 128

# Simulated sprite for testing
class TestSprite:
    """Simple sprite for testing compositing."""
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.buffer = np.zeros((height, width, 3), dtype=np.uint8)
        self.x = 0
        self.y = 0
        self.visible = True
    
    def draw_circle(self, cx: int, cy: int, radius: int, r: int, g: int, b: int):
        for y in range(self.height):
            for x in range(self.width):
                if math.sqrt((x - cx) ** 2 + (y - cy) ** 2) <= radius:
                    self.buffer[y, x] = [r, g, b]


class BackgroundSprite:
    """A large pattern that can be rendered as a tiling background."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.buffer = np.zeros((height, width, 3), dtype=np.uint8)
        self.offset_x = 0
        self.offset_y = 0
    
    def plot(self, x: int, y: int, r: int, g: int, b: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = [r, g, b]
    
    def draw_circle(self, cx: int, cy: int, radius: int, r: int, g: int, b: int, filled: bool = False):
        for y in range(max(0, cy - radius), min(self.height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.width, cx + radius + 1)):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if filled:
                    if dist <= radius:
                        self.buffer[y, x] = [r, g, b]
                else:
                    if abs(dist - radius) < 1.0:
                        self.buffer[y, x] = [r, g, b]
    
    def get_viewport_fast(self, offset_x: int, offset_y: int,
                          view_width: int = DISPLAY_WIDTH,
                          view_height: int = DISPLAY_HEIGHT) -> np.ndarray:
        """Optimized viewport extraction using numpy operations."""
        offset_x = offset_x % self.width
        offset_y = offset_y % self.height
        
        y_indices = (np.arange(view_height) + offset_y) % self.height
        x_indices = (np.arange(view_width) + offset_x) % self.width
        
        # Returns a VIEW, not a copy - need to copy for modification
        return self.buffer[np.ix_(y_indices, x_indices)].copy()


class SimulatedApi:
    """
    Simulates the api.py architecture with background layer added.
    
    This mirrors the exact patterns from api.py:
    - drawing_buffer: persistent numpy array
    - canvas: hardware framebuffer
    - current_command_pixels: list for back buffer rebuild
    - frame_mode: batched vs immediate rendering
    """
    
    def __init__(self, matrix: RGBMatrix):
        self.matrix = matrix
        self.canvas = matrix.CreateFrameCanvas()
        
        # Existing api.py structures
        self.drawing_buffer = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)
        self.current_command_pixels: List[Tuple[int, int, int, int, int]] = []
        self.frame_mode = False
        self.preserve_frame_changes = False
        
        # NEW: Background layer
        self.background: Optional[BackgroundSprite] = None
        self.bg_offset_x = 0
        self.bg_offset_y = 0
        
        # Sprites list for testing
        self.sprites: List[TestSprite] = []
    
    def set_background(self, bg: BackgroundSprite):
        """Set the background pattern."""
        self.background = bg
    
    def nudge_background(self, dx: int, dy: int):
        """Shift the background viewport."""
        if self.background:
            self.bg_offset_x += dx
            self.bg_offset_y += dy
    
    def set_background_offset(self, x: int, y: int):
        """Set absolute background viewport position."""
        self.bg_offset_x = x
        self.bg_offset_y = y
    
    def add_sprite(self, sprite: TestSprite):
        """Add a sprite for compositing."""
        self.sprites.append(sprite)
    
    # ========== Mirrored from api.py ==========
    
    def _draw_to_buffers(self, x: int, y: int, r: int, g: int, b: int):
        """Exact copy of api.py pattern."""
        if 0 <= x < DISPLAY_WIDTH and 0 <= y < DISPLAY_HEIGHT:
            self.drawing_buffer[y, x] = [r, g, b]
            self.canvas.SetPixel(x, y, r, g, b)
            if not self.frame_mode or self.preserve_frame_changes:
                self.current_command_pixels.append((x, y, r, g, b))
    
    def _maybe_swap_buffer(self):
        """Exact copy of api.py pattern."""
        if not self.frame_mode:
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            for x, y, r, g, b in self.current_command_pixels:
                self.canvas.SetPixel(x, y, r, g, b)
            self.current_command_pixels.clear()
    
    def _copy_sprite_to_canvas(self, sprite: TestSprite):
        """Copy sprite to canvas with transparency (black = transparent)."""
        for sy in range(sprite.height):
            dy = sprite.y + sy
            if dy < 0 or dy >= DISPLAY_HEIGHT:
                continue
            for sx in range(sprite.width):
                dx = sprite.x + sx
                if dx < 0 or dx >= DISPLAY_WIDTH:
                    continue
                r, g, b = sprite.buffer[sy, sx]
                if (r, g, b) != (0, 0, 0):  # Not transparent
                    self.canvas.SetPixel(dx, dy, r, g, b)
    
    def begin_frame(self, preserve_changes: bool = False):
        """Exact copy of api.py pattern."""
        self.frame_mode = True
        self.preserve_frame_changes = preserve_changes
        if not preserve_changes:
            self.canvas.Fill(0, 0, 0)
    
    def end_frame(self):
        """
        Modified from api.py to include background layer.
        
        Compositing order:
        1. Background pattern (if set)
        2. Drawing buffer (black = transparent over background)
        3. Sprites (black = transparent)
        """
        if self.frame_mode:
            # Step 1: Composite all layers to canvas
            self._composite_all_layers_to_canvas()
            
            # Step 2: Swap to display
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            
            # Step 3: Prepare back buffer for next frame
            # This also needs the composited background + drawing_buffer
            self._prepare_back_buffer()
            
            self.current_command_pixels.clear()
            self.frame_mode = False
            self.preserve_frame_changes = False
    
    def _composite_all_layers_to_canvas(self):
        """
        Composite all layers to canvas in correct order.
        This is called before SwapOnVSync.
        """
        # Start with background (or black if no background)
        if self.background:
            viewport = self.background.get_viewport_fast(self.bg_offset_x, self.bg_offset_y)
            
            # Composite drawing_buffer on top (black = transparent)
            mask = np.any(self.drawing_buffer != 0, axis=2)
            viewport[mask] = self.drawing_buffer[mask]
            
            # Blit composited image to canvas
            pil_image = Image.fromarray(viewport, mode='RGB')
            self.canvas.SetImage(pil_image)
        else:
            # No background - use drawing_buffer directly (existing behavior)
            pil_image = Image.fromarray(self.drawing_buffer, mode='RGB')
            self.canvas.SetImage(pil_image)
        
        # Draw sprites on top
        for sprite in self.sprites:
            if sprite.visible:
                self._copy_sprite_to_canvas(sprite)
    
    def _prepare_back_buffer(self):
        """
        Prepare the back buffer after swap.
        Mirrors api.py logic but accounts for background.
        """
        if self.preserve_frame_changes:
            # Rebuild with current state
            if self.background:
                viewport = self.background.get_viewport_fast(self.bg_offset_x, self.bg_offset_y)
                mask = np.any(self.drawing_buffer != 0, axis=2)
                viewport[mask] = self.drawing_buffer[mask]
                pil_image = Image.fromarray(viewport, mode='RGB')
                self.canvas.SetImage(pil_image)
            else:
                pil_image = Image.fromarray(self.drawing_buffer, mode='RGB')
                self.canvas.SetImage(pil_image)
            
            for x, y, r, g, b in self.current_command_pixels:
                self.canvas.SetPixel(x, y, r, g, b)
        else:
            self.canvas.Fill(0, 0, 0)
    
    def refresh_display(self):
        """
        Immediate mode refresh - mirrors api.py refresh_display.
        Used when sprites move outside of frame mode.
        """
        # Composite background + drawing_buffer
        if self.background:
            viewport = self.background.get_viewport_fast(self.bg_offset_x, self.bg_offset_y)
            mask = np.any(self.drawing_buffer != 0, axis=2)
            viewport[mask] = self.drawing_buffer[mask]
            pil_image = Image.fromarray(viewport, mode='RGB')
            self.canvas.SetImage(pil_image)
        
        # Draw sprites
        for sprite in self.sprites:
            if sprite.visible:
                self._copy_sprite_to_canvas(sprite)
        
        self._maybe_swap_buffer()
    
    def clear(self):
        """Clear all buffers."""
        self.drawing_buffer.fill(0)
        self.canvas.Fill(0, 0, 0)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        self.canvas.Fill(0, 0, 0)
        self.current_command_pixels.clear()


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
    print("Creating background pattern...")
    
    # Starfield
    np.random.seed(42)
    for _ in range(300):
        x = np.random.randint(0, bg.width)
        y = np.random.randint(0, bg.height)
        brightness = np.random.randint(30, 100)
        gray = int(255 * brightness / 100)
        bg.plot(x, y, gray, gray, gray)
    
    # Colored circles
    bg.draw_circle(32, 32, 15, 255, 0, 0, filled=True)
    bg.draw_circle(96, 32, 15, 0, 255, 0, filled=True)
    bg.draw_circle(32, 96, 15, 0, 0, 255, filled=True)
    bg.draw_circle(96, 96, 15, 255, 255, 0, filled=True)
    bg.draw_circle(64, 64, 10, 255, 0, 255, filled=True)
    
    # Grid lines
    for x in range(0, bg.width, 16):
        for y in range(bg.height):
            bg.plot(x, y, 40, 40, 40)
    for y in range(0, bg.height, 16):
        for x in range(bg.width):
            bg.plot(x, y, 40, 40, 40)
    
    print(f"Pattern created: {bg.width}x{bg.height}")


def create_drawing_buffer_content(drawing_buffer: np.ndarray):
    """Add some persistent content to drawing buffer."""
    print("Creating drawing buffer content...")
    
    # Cyan rectangle
    for x in range(20, 44):
        for y in range(20, 44):
            drawing_buffer[y, x] = [0, 255, 255]
    
    # Magenta circle
    for y in range(DISPLAY_HEIGHT):
        for x in range(DISPLAY_WIDTH):
            if math.sqrt((x - 50) ** 2 + (y - 14) ** 2) < 8:
                drawing_buffer[y, x] = [255, 0, 255]


def calculate_scroll_offset(elapsed: float, pattern_width: int, pattern_height: int) -> tuple:
    """Consistent circular scroll offset for all tests."""
    center_x = pattern_width // 2
    center_y = pattern_height // 2
    radius = 20
    rotation_speed = 1.0  # Rotations per second
    
    angle = elapsed * rotation_speed * 2 * math.pi
    offset_x = int(center_x + radius * math.cos(angle))
    offset_y = int(center_y + radius * math.sin(angle))
    
    return offset_x, offset_y


def run_test_no_background(matrix: RGBMatrix, duration: float = 8.0):
    """
    Test 1: Current api.py behavior (no background layer).
    Uses frame mode with drawing_buffer + sprites.
    """
    print("\n--- Test 1: NO BACKGROUND (current api.py behavior) ---")
    
    api = SimulatedApi(matrix)
    
    # Set up drawing buffer content
    create_drawing_buffer_content(api.drawing_buffer)
    
    # Create and add a moving sprite
    sprite = TestSprite(12, 12)
    sprite.draw_circle(6, 6, 5, 255, 128, 0)  # Orange circle
    api.add_sprite(sprite)
    
    frame_times = []
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        elapsed = time.time() - start_time
        
        # Move sprite in circle
        sprite.x = int(32 + 20 * math.cos(elapsed * 2))
        sprite.y = int(32 + 20 * math.sin(elapsed * 2))
        
        # Frame mode rendering (like your scripts use)
        api.begin_frame(preserve_changes=True)
        api.end_frame()
        
        frame_times.append(time.time() - frame_start)
        frame_count += 1
    
    fps = frame_count / duration
    avg_frame = np.mean(frame_times) * 1000
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    
    api.clear()
    return fps, avg_frame


def run_test_with_static_background(matrix: RGBMatrix, duration: float = 8.0):
    """
    Test 2: Background layer (not scrolling) + drawing_buffer + sprites.
    Tests the compositing overhead when background is present but static.
    """
    print("\n--- Test 2: STATIC BACKGROUND + drawing buffer + sprite ---")
    
    api = SimulatedApi(matrix)
    
    # Create and set background
    bg = BackgroundSprite(BG_WIDTH, BG_HEIGHT)
    create_test_pattern(bg)
    api.set_background(bg)
    
    # Set up drawing buffer content
    create_drawing_buffer_content(api.drawing_buffer)
    
    # Create and add a moving sprite
    sprite = TestSprite(12, 12)
    sprite.draw_circle(6, 6, 5, 255, 128, 0)
    api.add_sprite(sprite)
    
    frame_times = []
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        elapsed = time.time() - start_time
        
        # Move sprite in circle
        sprite.x = int(32 + 20 * math.cos(elapsed * 2))
        sprite.y = int(32 + 20 * math.sin(elapsed * 2))
        
        api.begin_frame(preserve_changes=True)
        api.end_frame()
        
        frame_times.append(time.time() - frame_start)
        frame_count += 1
    
    fps = frame_count / duration
    avg_frame = np.mean(frame_times) * 1000
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    
    api.clear()
    return fps, avg_frame


def run_test_with_scrolling_background(matrix: RGBMatrix, duration: float = 8.0):
    """
    Test 3: Scrolling background + drawing_buffer + sprites.
    The full layer stack with background animation.
    """
    print("\n--- Test 3: SCROLLING BACKGROUND + drawing buffer + sprite ---")
    
    api = SimulatedApi(matrix)
    
    # Create and set background
    bg = BackgroundSprite(BG_WIDTH, BG_HEIGHT)
    create_test_pattern(bg)
    api.set_background(bg)
    
    # Set up drawing buffer content
    create_drawing_buffer_content(api.drawing_buffer)
    
    # Create and add a moving sprite
    sprite = TestSprite(12, 12)
    sprite.draw_circle(6, 6, 5, 255, 128, 0)
    api.add_sprite(sprite)
    
    frame_times = []
    bg_times = []
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        elapsed = time.time() - start_time
        
        # Scroll background
        bg_start = time.time()
        offset_x, offset_y = calculate_scroll_offset(elapsed, bg.width, bg.height)
        api.set_background_offset(offset_x, offset_y)
        bg_times.append(time.time() - bg_start)
        
        # Move sprite in circle (opposite direction for visual interest)
        sprite.x = int(32 + 20 * math.cos(-elapsed * 2))
        sprite.y = int(32 + 20 * math.sin(-elapsed * 2))
        
        api.begin_frame(preserve_changes=True)
        api.end_frame()
        
        frame_times.append(time.time() - frame_start)
        frame_count += 1
    
    fps = frame_count / duration
    avg_frame = np.mean(frame_times) * 1000
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    
    api.clear()
    return fps, avg_frame


def run_test_scrolling_multiple_sprites(matrix: RGBMatrix, duration: float = 8.0):
    """
    Test 4: Scrolling background + drawing_buffer + multiple sprites.
    Stress test with more sprites.
    """
    print("\n--- Test 4: SCROLLING BACKGROUND + drawing buffer + 5 sprites ---")
    
    api = SimulatedApi(matrix)
    
    # Create and set background
    bg = BackgroundSprite(BG_WIDTH, BG_HEIGHT)
    create_test_pattern(bg)
    api.set_background(bg)
    
    # Set up drawing buffer content
    create_drawing_buffer_content(api.drawing_buffer)
    
    # Create multiple sprites
    colors = [(255, 128, 0), (0, 255, 128), (128, 0, 255), (255, 255, 0), (0, 255, 255)]
    sprites = []
    for i, (r, g, b) in enumerate(colors):
        sprite = TestSprite(10, 10)
        sprite.draw_circle(5, 5, 4, r, g, b)
        api.add_sprite(sprite)
        sprites.append(sprite)
    
    frame_times = []
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        elapsed = time.time() - start_time
        
        # Scroll background
        offset_x, offset_y = calculate_scroll_offset(elapsed, bg.width, bg.height)
        api.set_background_offset(offset_x, offset_y)
        
        # Move sprites in different patterns
        for i, sprite in enumerate(sprites):
            angle = elapsed * (1.5 + i * 0.3) + (i * 2 * math.pi / len(sprites))
            radius = 15 + i * 5
            sprite.x = int(32 + radius * math.cos(angle)) - 5
            sprite.y = int(32 + radius * math.sin(angle)) - 5
        
        api.begin_frame(preserve_changes=True)
        api.end_frame()
        
        frame_times.append(time.time() - frame_start)
        frame_count += 1
    
    fps = frame_count / duration
    avg_frame = np.mean(frame_times) * 1000
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    
    api.clear()
    return fps, avg_frame


def run_test_immediate_mode(matrix: RGBMatrix, duration: float = 8.0):
    """
    Test 5: Immediate mode (no frame buffering) with scrolling background.
    Tests refresh_display path instead of begin_frame/end_frame.
    """
    print("\n--- Test 5: IMMEDIATE MODE with scrolling background ---")
    
    api = SimulatedApi(matrix)
    
    # Create and set background
    bg = BackgroundSprite(BG_WIDTH, BG_HEIGHT)
    create_test_pattern(bg)
    api.set_background(bg)
    
    # Set up drawing buffer content
    create_drawing_buffer_content(api.drawing_buffer)
    
    # Create sprite
    sprite = TestSprite(12, 12)
    sprite.draw_circle(6, 6, 5, 255, 128, 0)
    api.add_sprite(sprite)
    
    frame_times = []
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        frame_start = time.time()
        elapsed = time.time() - start_time
        
        # Scroll background
        offset_x, offset_y = calculate_scroll_offset(elapsed, bg.width, bg.height)
        api.set_background_offset(offset_x, offset_y)
        
        # Move sprite
        sprite.x = int(32 + 20 * math.cos(-elapsed * 2))
        sprite.y = int(32 + 20 * math.sin(-elapsed * 2))
        
        # Immediate mode refresh (no frame buffering)
        api.refresh_display()
        
        frame_times.append(time.time() - frame_start)
        frame_count += 1
    
    fps = frame_count / duration
    avg_frame = np.mean(frame_times) * 1000
    
    print(f"  Frames: {frame_count}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg frame time: {avg_frame:.2f}ms")
    
    api.clear()
    return fps, avg_frame


def main():
    print("=" * 70)
    print("Background Sprite POC v2 - Accurate Architecture Test")
    print("=" * 70)
    print("\nThis test mirrors the exact api.py patterns:")
    print("  - Double-buffered canvas with SwapOnVSync")
    print("  - drawing_buffer + current_command_pixels")
    print("  - Frame mode (begin_frame/end_frame)")
    print("  - Sprite compositing with transparency")
    print()
    
    matrix = configure_matrix()
    test_duration = 8.0
    
    results = {}
    
    try:
        # Test 1: Current behavior (baseline)
        fps1, time1 = run_test_no_background(matrix, test_duration)
        results['no_background'] = (fps1, time1)
        time.sleep(1)
        
        # Test 2: Static background
        fps2, time2 = run_test_with_static_background(matrix, test_duration)
        results['static_background'] = (fps2, time2)
        time.sleep(1)
        
        # Test 3: Scrolling background
        fps3, time3 = run_test_with_scrolling_background(matrix, test_duration)
        results['scrolling_background'] = (fps3, time3)
        time.sleep(1)
        
        # Test 4: Multiple sprites
        fps4, time4 = run_test_scrolling_multiple_sprites(matrix, test_duration)
        results['multiple_sprites'] = (fps4, time4)
        time.sleep(1)
        
        # Test 5: Immediate mode
        fps5, time5 = run_test_immediate_mode(matrix, test_duration)
        results['immediate_mode'] = (fps5, time5)
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  {'Test':<45} {'FPS':>8} {'Frame ms':>10}")
        print(f"  {'-'*45} {'-'*8} {'-'*10}")
        print(f"  {'1. No background (current behavior)':<45} {fps1:>8.1f} {time1:>10.2f}")
        print(f"  {'2. Static background + drawing + sprite':<45} {fps2:>8.1f} {time2:>10.2f}")
        print(f"  {'3. Scrolling background + drawing + sprite':<45} {fps3:>8.1f} {time3:>10.2f}")
        print(f"  {'4. Scrolling background + drawing + 5 sprites':<45} {fps4:>8.1f} {time4:>10.2f}")
        print(f"  {'5. Immediate mode with scrolling background':<45} {fps5:>8.1f} {time5:>10.2f}")
        print()
        
        # Calculate overhead
        if fps1 > 0:
            overhead_static = ((time2 - time1) / time1) * 100
            overhead_scroll = ((time3 - time1) / time1) * 100
            print(f"  Background overhead (static):    {overhead_static:+.1f}%")
            print(f"  Background overhead (scrolling): {overhead_scroll:+.1f}%")
        
        print()
        min_fps = min(fps1, fps2, fps3, fps4, fps5)
        if min_fps >= 30:
            print("  ✓ ALL TESTS PASS - 30+ FPS achieved across all scenarios")
        elif min_fps >= 24:
            print("  ⚠ MARGINAL - Some tests below 30 FPS but above 24 FPS")
        else:
            print("  ✗ NEEDS OPTIMIZATION - Performance below acceptable threshold")
        
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        canvas = matrix.CreateFrameCanvas()
        canvas.Fill(0, 0, 0)
        matrix.SwapOnVSync(canvas)
        print("\nTest complete - display cleared")


if __name__ == "__main__":
    main()