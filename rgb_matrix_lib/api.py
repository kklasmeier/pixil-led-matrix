# File: rgb_matrix_lib/api.py

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import time
import math
from .drawing_objects import DrawingObject, ShapeType, ThreadedBurnoutManager, BurnoutMode
from .utils import get_color_rgb, polygon_vertices, arc_points, TRANSPARENT_COLOR, GRID_SIZE, get_grid_cells
from typing import Optional, List, Tuple, Union, Any
from .debug import debug, Level, Component, configure_debug
from .sprite import MatrixSprite, SpriteManager, SpriteInstance
from .background import BackgroundManager
import numpy as np
from .text_effects import TextEffect, EffectModifier
from .text_renderer import TextRenderer
from .commands import CommandExecutor  # Added CommandExecutor import

#configure_debug(level=Level.DEBUG)

# Performance tuning flag
USE_PIL_FOR_FRAME_MODE = True  # Set to True to use PIL Image approach

# Global instance for internal use
_api_instance: Optional['RGB_Api'] = None

def get_api_instance() -> 'RGB_Api':
    """Get or create the global RGB_Api instance."""
    global _api_instance
    if _api_instance is None:
        debug("Creating new global RGB_Api instance", Level.INFO, Component.SYSTEM)
        _api_instance = RGB_Api()
    return _api_instance

def execute_command(command: str) -> None:
    """Execute a single command on the LED matrix."""
    api = get_api_instance()
    api.execute_command(command)

execute_single_command = execute_command

def cleanup() -> None:
    """Clean up resources and reset the LED matrix."""
    global _api_instance
    if _api_instance is not None:
        try:
            print("API module-level cleanup starting...")
            _api_instance.cleanup()
            print("API module-level cleanup: instance cleanup completed")
        except Exception as e:
            print(f"ERROR in API module-level cleanup: {str(e)}")
        finally:
            _api_instance = None
            print("API module-level cleanup: instance set to None")

class RGB_Api:
    def __init__(self):
        debug(f"Initializing RGB_Api from {__file__}", Level.INFO, Component.SYSTEM)
        
        self.options = self._configure_matrix_options()
        self.matrix = RGBMatrix(options=self.options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.drawing_buffer = np.zeros((self.matrix.height, self.matrix.width, 3), dtype=np.uint8)
        self.current_command_pixels = []
        self.frame_mode = False
        self.preserve_frame_changes = False
        self.grid_dirty = np.zeros((self.matrix.height // GRID_SIZE, self.matrix.width // GRID_SIZE), dtype=bool)
        self.sprite_manager = SpriteManager()
        self.background_manager = BackgroundManager(self.sprite_manager)
        self.text_renderer = TextRenderer(self)
        self.burnout_manager = ThreadedBurnoutManager(self)
        self.burnout_manager.start()
                
        debug("RGB_Api initialization complete", Level.INFO, Component.SYSTEM)

    def dispose_all_sprites(self):
        """Remove all sprites from memory and clear them from display."""
        debug("Disposing all sprites", Level.INFO, Component.SPRITE)
        # Notify background manager before disposing templates
        # (dispose_all_sprites destroys templates, so background must be cleared)
        self.background_manager.hide_background()
        self.background_manager._active_sprite_name = None
        dirty_cells = self.sprite_manager.dispose_all_sprites()
        if dirty_cells:
            self._mark_cells_dirty(dirty_cells)
            if not self.frame_mode:
                self._restore_dirty_cells()
                self.refresh_display()
        debug("All sprites disposed", Level.DEBUG, Component.SPRITE)

    # Background Layer Methods
    def set_background(self, sprite_name: str, cel_index: int = 0):
        """Activate a sprite as the background layer."""
        success = self.background_manager.set_background(sprite_name, cel_index)
        if not success:
            debug(f"Background sprite '{sprite_name}' not found", Level.ERROR, Component.SYSTEM)
        if not self.frame_mode:
            self.refresh_display()

    def hide_background(self):
        """Remove the background layer (template persists for reactivation)."""
        self.background_manager.hide_background()
        if not self.frame_mode:
            self.refresh_display()

    def nudge_background(self, dx: int, dy: int, cel_index: Optional[int] = None):
        """Shift background viewport. Auto-advances cel unless cel_index specified."""
        self.background_manager.nudge(dx, dy, cel_index)
        if not self.frame_mode:
            self.refresh_display()

    def set_background_offset(self, x: int, y: int, cel_index: Optional[int] = None):
        """Set absolute background viewport position. Auto-advances cel unless cel_index specified."""
        self.background_manager.set_offset(x, y, cel_index)
        if not self.frame_mode:
            self.refresh_display()

    def _configure_matrix_options(self):
        """Configure and return matrix options."""
        debug("Configuring matrix options", Level.DEBUG, Component.MATRIX)
        options = RGBMatrixOptions()
        options = RGBMatrixOptions()
        options.rows = 64
        options.cols = 64
        options.hardware_mapping = 'adafruit-hat'
        options.gpio_slowdown = 3
        options.scan_mode = 1
        options.pwm_bits = 11
        options.brightness = 100
        options.limit_refresh_rate_hz = 0  # No throttling

        debug(f"Matrix configured: {options.rows}x{options.cols}", Level.DEBUG, Component.MATRIX)
        return options

    def _get_color(self, color: Union[str, int, Tuple[int, int, int]], intensity: int = 100) -> Tuple[int, int, int]:
        """Get RGB tuple for a color input with optional intensity."""
        # Clamp intensity to 0-99 (max per rgb_matrix_lib)
        intensity = max(0, min(100, intensity))
        
        if isinstance(color, tuple) and len(color) == 3:
            # Tuple is pre-scaled RGB; apply intensity only if not 100
            if intensity != 100:
                scale = intensity / 100.0
                r, g, b = color
                rgb = (int(r * scale), int(g * scale), int(b * scale))
                debug(f"Scaled RGB tuple {color} at {intensity}% to {rgb}", Level.TRACE, Component.DRAWING)
                return rgb
            debug(f"Using RGB tuple {color} at {intensity}%", Level.TRACE, Component.DRAWING)
            return color
        
        # Named colors or spectral numbers
        rgb = get_color_rgb(color, intensity)
        debug(f"Converted {color} at {intensity}% to RGB: {rgb}", Level.TRACE, Component.DRAWING)
        return rgb

    def begin_frame(self, preserve_changes: bool = False):
        """Start frame mode."""
        self.frame_mode = True
        self.preserve_frame_changes = preserve_changes
        if not preserve_changes:
            self.drawing_buffer.fill(0)  # Fresh drawing buffer each frame
            self.canvas.Fill(0, 0, 0)    # Clears the current canvas if not preserving

    def end_frame(self):
        if self.frame_mode:
            if self.background_manager.has_background():
                # --- BACKGROUND PATH ---
                # Layer 1+2: Composite background + drawing_buffer
                bg_viewport = self.background_manager.get_viewport(self.matrix.width, self.matrix.height)
                mask = np.any(self.drawing_buffer != 0, axis=2)
                bg_viewport[mask] = self.drawing_buffer[mask]
                pil_image = Image.fromarray(bg_viewport, mode='RGB')
                self.canvas.SetImage(pil_image)

                # Layer 3: Sprites on top
                for sprite_name, instance_id in self.sprite_manager.z_order:
                    instance = self.sprite_manager.get_instance(sprite_name, instance_id)
                    if instance and instance.visible:
                        self.copy_sprite_to_buffer(instance, self.canvas)

                # Swap
                self.canvas = self.matrix.SwapOnVSync(self.canvas)

                # Prepare back buffer with background composite
                bg_viewport = self.background_manager.get_viewport(self.matrix.width, self.matrix.height)
                mask = np.any(self.drawing_buffer != 0, axis=2)
                bg_viewport[mask] = self.drawing_buffer[mask]
                pil_image = Image.fromarray(bg_viewport, mode='RGB')
                self.canvas.SetImage(pil_image)

                if self.preserve_frame_changes:
                    for x, y, r, g, b in self.current_command_pixels:
                        self.canvas.SetPixel(x, y, r, g, b)
                # No Fill(0,0,0) needed — background provides the base

            else:
                # --- ORIGINAL NO-BACKGROUND PATH (unchanged) ---
                # Draw all visible sprites to the current canvas (before swap)
                for sprite_name, instance_id in self.sprite_manager.z_order:
                    instance = self.sprite_manager.get_instance(sprite_name, instance_id)
                    if instance and instance.visible:
                        self.copy_sprite_to_buffer(instance, self.canvas)

                # Swap
                self.canvas = self.matrix.SwapOnVSync(self.canvas)

                # Prepare back buffer for next frame
                if USE_PIL_FOR_FRAME_MODE:
                    pil_image = Image.fromarray(self.drawing_buffer, mode='RGB')
                    self.canvas.SetImage(pil_image)
                else:
                    for y in range(self.matrix.height):
                        for x in range(self.matrix.width):
                            r, g, b = self.drawing_buffer[y, x]
                            self.canvas.SetPixel(x, y, int(r), int(g), int(b))

                if self.preserve_frame_changes:
                    for x, y, r, g, b in self.current_command_pixels:
                        self.canvas.SetPixel(x, y, r, g, b)
                else:
                    self.canvas.Fill(0, 0, 0)  # Prepares back buffer

            self.current_command_pixels.clear()
            self.frame_mode = False
            self.preserve_frame_changes = False

#    def end_frame(self):
#        """End frame mode and display the accumulated drawing."""
#        if self.frame_mode:
#            self.canvas = self.matrix.SwapOnVSync(self.canvas)
#            
#            if USE_PIL_FOR_FRAME_MODE:
#                # PIL Image approach (faster in benchmarks, needs production testing)
#                pil_image = Image.fromarray(self.drawing_buffer, mode='RGB')
#                self.canvas.SetImage(pil_image)
#            else:
#                # Original approach (stable, proven)
#                for y in range(self.matrix.height):
#                    for x in range(self.matrix.width):
#                        r, g, b = self.drawing_buffer[y, x]
#                        self.canvas.SetPixel(x, y, int(r), int(g), int(b))
#            
#            if self.preserve_frame_changes:
#                for x, y, r, g, b in self.current_command_pixels:
#                    self.canvas.SetPixel(x, y, r, g, b)
#                self.current_command_pixels.clear()
#            else:
#                self.canvas.Fill(0, 0, 0)
#            
#            self.refresh_display()
#            self.frame_mode = False
#            self.preserve_frame_changes = False

    def _draw_to_buffers(self, x: int, y: int, r: int, g: int, b: int):
        if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
            self.drawing_buffer[y, x] = [r, g, b]
            self.canvas.SetPixel(x, y, r, g, b)
            if not self.frame_mode or self.preserve_frame_changes:
                self.current_command_pixels.append((x, y, r, g, b))

    def _maybe_swap_buffer(self):
        """Handle buffer swapping based on mode."""
        if not self.frame_mode:
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            for x, y, r, g, b in self.current_command_pixels:
                self.canvas.SetPixel(x, y, r, g, b)
            self.current_command_pixels.clear()

    # Basic Drawing Methods
    def plot(self, x: int, y: int, color: Union[str, int], intensity: int = 100, 
             burnout: Optional[int] = None, burnout_mode: str = "instant"):
        """Plot a single pixel.
        
        Args:
            x, y: Pixel coordinates
            color: Color name, spectral number (0-99), or RGB tuple
            intensity: Brightness 0-100 (default 100)
            burnout: Duration in milliseconds before removal. -1 means no burnout.
            burnout_mode: 'instant' (clear to black at expiration) or 'fade' (gradual fade)
        """
        rgb_color = self._get_color(color, intensity)
        debug(f"Plotting point at ({x}, {y}) with color {color} at {intensity}% -> RGB {rgb_color}", 
              Level.TRACE, Component.DRAWING)
        
        if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
            self._draw_to_buffers(x, y, rgb_color[0], rgb_color[1], rgb_color[2])
            self._maybe_swap_buffer()

            if burnout is not None and burnout >= 0:
                mode = BurnoutMode.FADE if burnout_mode.lower() == "fade" else BurnoutMode.INSTANT
                pixel_colors = [rgb_color] if mode == BurnoutMode.FADE else None
                self.burnout_manager.add_object(
                    ShapeType.POINT, (x, y), [(x, y)], burnout, mode, pixel_colors
                )
        else:
            debug(f"Plot point ({x}, {y}) outside matrix bounds", Level.TRACE, Component.DRAWING)

    def plot_batch(self, plots):
        """Execute multiple plots atomically with single buffer swap.
        
        Args:
            plots: List of tuples (x, y, color, intensity, burnout, burnout_mode)
                   burnout_mode is optional and defaults to 'instant'
        """
        pixels_plotted = 0
        burnout_objects = []  # Only used if we find burnouts
        has_burnouts = False
        
        for plot_data in plots:
            # Handle both old format (5 elements) and new format (6 elements)
            if len(plot_data) == 5:
                x, y, color, intensity, burnout = plot_data
                burnout_mode = "instant"
            else:
                x, y, color, intensity, burnout, burnout_mode = plot_data
            
            # Skip invalid coordinates immediately
            if not (0 <= x < self.matrix.width and 0 <= y < self.matrix.height):
                continue
                
            # Get RGB color
            rgb_color = self._get_color(color, intensity if intensity is not None else 100)
            
            # Write directly to buffers (bypass bounds check since we already validated)
            self.drawing_buffer[y, x] = [rgb_color[0], rgb_color[1], rgb_color[2]]
            self.canvas.SetPixel(x, y, rgb_color[0], rgb_color[1], rgb_color[2])
            if not self.frame_mode or self.preserve_frame_changes:
                self.current_command_pixels.append((x, y, rgb_color[0], rgb_color[1], rgb_color[2]))
            
            # Only collect burnout data if burnout is specified and >= 0
            if burnout is not None and burnout >= 0:
                if not has_burnouts:
                    has_burnouts = True
                burnout_objects.append(((x, y), burnout, burnout_mode, rgb_color))
            
            pixels_plotted += 1
        
        # Single buffer swap for all pixels
        self._maybe_swap_buffer()
        
        # Only process burnouts if any were found
        if has_burnouts:
            for (x, y), burnout_time, b_mode, rgb_color in burnout_objects:
                mode = BurnoutMode.FADE if b_mode.lower() == "fade" else BurnoutMode.INSTANT
                pixel_colors = [rgb_color] if mode == BurnoutMode.FADE else None
                self.burnout_manager.add_object(
                    ShapeType.POINT, (x, y), [(x, y)], burnout_time, mode, pixel_colors
                )
            debug(f"Batch plotted {pixels_plotted} pixels ({len(burnout_objects)} with burnouts) atomically", 
                Level.DEBUG, Component.COMMAND)
        else:
            debug(f"Batch plotted {pixels_plotted} pixels atomically (no burnouts)", 
                Level.DEBUG, Component.COMMAND)
        
    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: Union[str, int], 
                  intensity: int = 100, burnout: Optional[int] = None, burnout_mode: str = "instant"):
        """Draw a line between two points.
        
        Args:
            x0, y0: Start point coordinates
            x1, y1: End point coordinates
            color: Color name, spectral number (0-99), or RGB tuple
            intensity: Brightness 0-100 (default 100)
            burnout: Duration in milliseconds before removal. -1 means no burnout.
            burnout_mode: 'instant' (clear to black at expiration) or 'fade' (gradual fade)
        """
        rgb_color = self._get_color(color, intensity)
        points = []
        
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            if 0 <= x0 < self.matrix.width and 0 <= y0 < self.matrix.height:
                self._draw_to_buffers(x0, y0, rgb_color[0], rgb_color[1], rgb_color[2])
                points.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

        self._maybe_swap_buffer()

        if burnout is not None and burnout >= 0:
            mode = BurnoutMode.FADE if burnout_mode.lower() == "fade" else BurnoutMode.INSTANT
            pixel_colors = [rgb_color] * len(points) if mode == BurnoutMode.FADE else None
            self.burnout_manager.add_object(
                ShapeType.LINE, (x0, y0, x1, y1), points, burnout, mode, pixel_colors
            )

    def draw_rectangle(self, x: int, y: int, width: int, height: int, color: Union[str, int], 
                    intensity: int = 100, fill: bool = False, burnout: Optional[int] = None,
                    burnout_mode: str = "instant"):
        """Draw a rectangle.
        
        Args:
            x, y: Top-left corner coordinates
            width, height: Rectangle dimensions
            color: Color name, spectral number (0-99), or RGB tuple
            intensity: Brightness 0-100 (default 100)
            fill: If True, fill the rectangle (default False)
            burnout: Duration in milliseconds before removal. -1 means no burnout.
            burnout_mode: 'instant' (clear to black at expiration) or 'fade' (gradual fade)
        """
        rgb_color = self._get_color(color, intensity)

        points = []
        
        if fill:
            for i in range(max(0, x), min(x + width, self.matrix.width)):
                for j in range(max(0, y), min(y + height, self.matrix.height)):
                    self._draw_to_buffers(i, j, rgb_color[0], rgb_color[1], rgb_color[2])
                    points.append((i, j))
        else:
            for i in range(max(0, x), min(x + width, self.matrix.width)):
                if 0 <= y < self.matrix.height:
                    self._draw_to_buffers(i, y, rgb_color[0], rgb_color[1], rgb_color[2])
                    points.append((i, y))
                if 0 <= y + height - 1 < self.matrix.height:
                    self._draw_to_buffers(i, y + height - 1, rgb_color[0], rgb_color[1], rgb_color[2])
                    points.append((i, y + height - 1))
            for j in range(max(0, y), min(y + height, self.matrix.height)):
                if 0 <= x < self.matrix.width:
                    self._draw_to_buffers(x, j, rgb_color[0], rgb_color[1], rgb_color[2])
                    points.append((x, j))
                if 0 <= x + width - 1 < self.matrix.width:
                    self._draw_to_buffers(x + width - 1, j, rgb_color[0], rgb_color[1], rgb_color[2])
                    points.append((x + width - 1, j))

        self._maybe_swap_buffer()

        if burnout is not None and burnout >= 0:
            mode = BurnoutMode.FADE if burnout_mode.lower() == "fade" else BurnoutMode.INSTANT
            pixel_colors = [rgb_color] * len(points) if mode == BurnoutMode.FADE else None
            self.burnout_manager.add_object(
                ShapeType.RECTANGLE, (x, y, width, height), points, burnout, mode, pixel_colors
            )

    def draw_circle(self, x_center: int, y_center: int, radius: int, color: Union[str, int], 
                    intensity: int = 100, fill: bool = False, burnout: Optional[int] = None,
                    burnout_mode: str = "instant"):
        """Draw a circle.
        
        Args:
            x_center, y_center: Center coordinates
            radius: Circle radius
            color: Color name, spectral number (0-99), or RGB tuple
            intensity: Brightness 0-100 (default 100)
            fill: If True, fill the circle (default False)
            burnout: Duration in milliseconds before removal. -1 means no burnout.
            burnout_mode: 'instant' (clear to black at expiration) or 'fade' (gradual fade)
        """
        rgb_color = self._get_color(color, intensity)
        points = set()

        def plot_circle_points(x: int, y: int):
            for dx, dy in [(x, y), (-x, y), (x, -y), (-x, -y), (y, x), (-y, x), (y, -x), (-y, -x)]:
                px, py = x_center + dx, y_center + dy
                if 0 <= px < self.matrix.width and 0 <= py < self.matrix.height:
                    self._draw_to_buffers(px, py, rgb_color[0], rgb_color[1], rgb_color[2])
                    points.add((px, py))
                    
        def draw_line(x0: int, y0: int, x1: int):
            for x in range(max(0, x0), min(x1 + 1, self.matrix.width)):
                if 0 <= y0 < self.matrix.height:
                    self._draw_to_buffers(x, y0, rgb_color[0], rgb_color[1], rgb_color[2])
                    points.add((x, y0))

        x, y = 0, radius
        d = 3 - 2 * radius

        while y >= x:
            if fill:
                draw_line(x_center - x, y_center - y, x_center + x)
                draw_line(x_center - x, y_center + y, x_center + x)
                draw_line(x_center - y, y_center - x, x_center + y)
                draw_line(x_center - y, y_center + x, x_center + y)
            else:
                plot_circle_points(x, y)

            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6

        self._maybe_swap_buffer()

        if burnout is not None and burnout >= 0:
            mode = BurnoutMode.FADE if burnout_mode.lower() == "fade" else BurnoutMode.INSTANT
            points_list = list(points)
            pixel_colors = [rgb_color] * len(points_list) if mode == BurnoutMode.FADE else None
            self.burnout_manager.add_object(
                ShapeType.CIRCLE, (x_center, y_center, radius), points_list, burnout, mode, pixel_colors
            )

    def draw_polygon(self, x_center: int, y_center: int, radius: int, sides: int, color: Union[str, int], 
                     intensity: int = 100, rotation: float = 0, fill: bool = False, burnout: Optional[int] = None,
                     burnout_mode: str = "instant"):
        """Draw a regular polygon.
        
        Args:
            x_center, y_center: Center coordinates
            radius: Distance from center to vertices
            sides: Number of sides
            color: Color name, spectral number (0-99), or RGB tuple
            intensity: Brightness 0-100 (default 100)
            rotation: Rotation in degrees (default 0)
            fill: If True, fill the polygon (default False)
            burnout: Duration in milliseconds before removal. -1 means no burnout.
            burnout_mode: 'instant' (clear to black at expiration) or 'fade' (gradual fade)
        """
        rgb_color = self._get_color(color, intensity)
        debug(f"Drawing polygon: center({x_center}, {y_center}), radius={radius}, sides={sides}", 
              Level.DEBUG, Component.DRAWING)
        vertices = polygon_vertices(x_center, y_center, radius, sides, rotation)
        burnout_points = set() if burnout is not None and burnout >= 0 else None
        
        for i in range(len(vertices)):
            x0, y0 = vertices[i]
            x1, y1 = vertices[(i + 1) % len(vertices)]
            dx = abs(x1 - x0)
            dy = -abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx + dy
            cx, cy = x0, y0
            
            while True:
                if 0 <= cx < self.matrix.width and 0 <= cy < self.matrix.height:
                    self._draw_to_buffers(cx, cy, rgb_color[0], rgb_color[1], rgb_color[2])
                    if burnout_points is not None:
                        burnout_points.add((cx, cy))
                if cx == x1 and cy == y1:
                    break
                e2 = 2 * err
                if e2 >= dy:
                    err += dy
                    cx += sx
                if e2 <= dx:
                    err += dx
                    cy += sy
        
        if fill:
            min_x = max(0, min(p[0] for p in vertices))
            max_x = min(self.matrix.width - 1, max(p[0] for p in vertices))
            min_y = max(0, min(p[1] for p in vertices))
            max_y = min(self.matrix.height - 1, max(p[1] for p in vertices))
            for y in range(min_y, max_y + 1):
                intersections = []
                for i in range(len(vertices)):
                    x0, y0 = vertices[i]
                    x1, y1 = vertices[(i + 1) % len(vertices)]
                    if (y0 < y and y1 >= y) or (y1 < y and y0 >= y):
                        x = int(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
                        intersections.append(x)
                intersections.sort()
                for i in range(0, len(intersections), 2):
                    if i + 1 < len(intersections):
                        start = max(min_x, min(intersections[i], intersections[i + 1]))
                        end = min(max_x, max(intersections[i], intersections[i + 1]))
                        for x in range(int(start), int(end) + 1):
                            self._draw_to_buffers(x, y, rgb_color[0], rgb_color[1], rgb_color[2])
                            if burnout_points is not None:
                                burnout_points.add((x, y))

        self._maybe_swap_buffer()

        if burnout is not None and burnout >= 0:
            mode = BurnoutMode.FADE if burnout_mode.lower() == "fade" else BurnoutMode.INSTANT
            points_list = list(burnout_points) if burnout_points else []
            pixel_colors = [rgb_color] * len(points_list) if mode == BurnoutMode.FADE else None
            self.burnout_manager.add_object(
                ShapeType.POLYGON, (x_center, y_center, radius), 
                points_list, burnout, mode, pixel_colors
            )

    def draw_ellipse(self, x_center: int, y_center: int, x_radius: int, y_radius: int, color: Union[str, int], 
                    intensity: int = 100, fill: bool = False, rotation: float = 0, burnout: Optional[int] = None,
                    burnout_mode: str = "instant"):
        """Draw an ellipse with optional rotation.
        
        Args:
            x_center, y_center: Center coordinates
            x_radius, y_radius: Horizontal and vertical radii
            color: Color name, spectral number (0-99), or RGB tuple
            intensity: Brightness 0-100 (default 100)
            fill: If True, fill the ellipse (default False)
            rotation: Rotation in degrees (default 0)
            burnout: Duration in milliseconds before removal. -1 means no burnout.
            burnout_mode: 'instant' (clear to black at expiration) or 'fade' (gradual fade)
        """
        rgb_color = self._get_color(color, intensity)
        points = set()
        
        # Pre-compute sin/cos for rotation
        rotation_rad = math.radians(rotation)
        cos_rot = math.cos(rotation_rad)
        sin_rot = math.sin(rotation_rad)
        
        # Helper function to rotate a point around the origin
        def rotate_point(x: int, y: int) -> Tuple[int, int]:
            rx = round(x * cos_rot - y * sin_rot)
            ry = round(x * sin_rot + y * cos_rot)
            return rx, ry
        
        # Helper function to plot a pixel if it's within bounds
        def plot_pixel(x: int, y: int):
            if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
                self._draw_to_buffers(x, y, rgb_color[0], rgb_color[1], rgb_color[2])
                points.add((x, y))
        
        # Special cases: point, horizontal/vertical line
        if x_radius == 0 or y_radius == 0:
            if x_radius == 0 and y_radius == 0:
                # Single point
                plot_pixel(x_center, y_center)
            elif x_radius == 0:
                # Vertical line
                for y in range(-y_radius, y_radius + 1):
                    rx, ry = rotate_point(0, y)
                    plot_pixel(x_center + rx, y_center + ry)
            else:  # y_radius == 0
                # Horizontal line
                for x in range(-x_radius, x_radius + 1):
                    rx, ry = rotate_point(x, 0)
                    plot_pixel(x_center + rx, y_center + ry)
            
            self._maybe_swap_buffer()
            
            if burnout is not None and burnout >= 0:
                mode = BurnoutMode.FADE if burnout_mode.lower() == "fade" else BurnoutMode.INSTANT
                points_list = list(points)
                pixel_colors = [rgb_color] * len(points_list) if mode == BurnoutMode.FADE else None
                self.burnout_manager.add_object(
                    ShapeType.ELLIPSE, (x_center, y_center, x_radius, y_radius, rotation), 
                    points_list, burnout, mode, pixel_colors
                )
            return
        
        # For filled ellipses, use a pixel-by-pixel approach
        if fill:
            # Determine a safe bounding box that will contain the rotated ellipse
            max_radius = max(x_radius, y_radius)
            min_x = max(0, x_center - max_radius - 1)
            max_x = min(self.matrix.width - 1, x_center + max_radius + 1)
            min_y = max(0, y_center - max_radius - 1)
            max_y = min(self.matrix.height - 1, y_center + max_radius + 1)
            
            # Check each pixel in the bounding box
            x_radius_sq = x_radius * x_radius
            y_radius_sq = y_radius * y_radius
            
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    # Transform back to ellipse coordinate system
                    dx = x - x_center
                    dy = y - y_center
                    
                    # Apply inverse rotation to check if point is inside unrotated ellipse
                    rx = dx * cos_rot + dy * sin_rot
                    ry = -dx * sin_rot + dy * cos_rot
                    
                    # Check ellipse equation: (x/a)² + (y/b)² <= 1
                    if (rx * rx / x_radius_sq + ry * ry / y_radius_sq) <= 1.0:
                        plot_pixel(x, y)
        else:
            # For outlines, use the midpoint algorithm
            a_squared = x_radius * x_radius
            b_squared = y_radius * y_radius
            
            # First region of the first quadrant
            x = 0
            y = y_radius
            
            # Initial decision parameter for region 1
            d1 = b_squared - a_squared * y_radius + (a_squared // 4)
            dx = 2 * b_squared * x
            dy = 2 * a_squared * y
            
            # Plot initial points in all four quadrants
            rx, ry = rotate_point(x, y)
            plot_pixel(x_center + rx, y_center + ry)
            
            rx, ry = rotate_point(-x, y)
            plot_pixel(x_center + rx, y_center + ry)
            
            rx, ry = rotate_point(x, -y)
            plot_pixel(x_center + rx, y_center + ry)
            
            rx, ry = rotate_point(-x, -y)
            plot_pixel(x_center + rx, y_center + ry)
            
            # Region 1
            while dx < dy:
                x += 1
                dx += 2 * b_squared
                
                if d1 < 0:
                    d1 += dx + b_squared
                else:
                    y -= 1
                    dy -= 2 * a_squared
                    d1 += dx + b_squared - dy
                
                # Plot points in all four quadrants
                rx, ry = rotate_point(x, y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(-x, y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(x, -y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(-x, -y)
                plot_pixel(x_center + rx, y_center + ry)
            
            # Decision parameter for region 2
            d2 = (b_squared * (x + 0.5) * (x + 0.5) + 
                a_squared * (y - 1) * (y - 1) - 
                a_squared * b_squared)
            
            # Region 2
            while y >= 0:
                y -= 1
                dy -= 2 * a_squared
                
                if d2 > 0:
                    d2 += a_squared - dy
                else:
                    x += 1
                    dx += 2 * b_squared
                    d2 += a_squared - dy + dx
                
                # Plot points in all four quadrants
                rx, ry = rotate_point(x, y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(-x, y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(x, -y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(-x, -y)
                plot_pixel(x_center + rx, y_center + ry)
        
        self._maybe_swap_buffer()
        
        if burnout is not None and burnout >= 0:
            mode = BurnoutMode.FADE if burnout_mode.lower() == "fade" else BurnoutMode.INSTANT
            points_list = list(points)
            pixel_colors = [rgb_color] * len(points_list) if mode == BurnoutMode.FADE else None
            self.burnout_manager.add_object(
                ShapeType.ELLIPSE, (x_center, y_center, x_radius, y_radius, rotation), 
                points_list, burnout, mode, pixel_colors
            )

    def draw_arc(self, x1: int, y1: int, x2: int, y2: int, bulge: float, color: Union[str, int],
                 intensity: int = 100, fill: bool = False, burnout: Optional[int] = None,
                 burnout_mode: str = "instant"):
        """
        Draw an arc defined by two endpoints and a bulge value.
        
        The arc curves between the start point (x1, y1) and end point (x2, y2).
        The bulge parameter controls how much the arc curves away from the straight 
        line (chord) between the endpoints.
        
        Args:
            x1, y1: Start point of the arc
            x2, y2: End point of the arc
            bulge: Perpendicular distance from chord midpoint to arc peak
                   - Positive: curves to port (left when traveling start→end)
                   - Negative: curves to starboard (right when traveling start→end)
                   - Zero: draws a straight line
            color: Color name, spectral number (0-99), or RGB tuple
            intensity: Brightness 0-100 (default 100)
            fill: If True, fills the chord area between arc and straight line (default False)
            burnout: Duration in milliseconds before removal. -1 means no burnout.
            burnout_mode: 'instant' (clear to black at expiration) or 'fade' (gradual fade)
        """
        rgb_color = self._get_color(color, intensity)
        
        debug(f"Drawing arc: ({x1},{y1}) to ({x2},{y2}), bulge={bulge}, "
              f"color={color} at {intensity}%, fill={fill}, "
              f"burnout={burnout if burnout is not None else 'None (permanent)'}", 
              Level.DEBUG, Component.DRAWING)
        
        # Get all points for the arc (outline or filled)
        points = arc_points(x1, y1, x2, y2, bulge, filled=fill)
        
        # Draw all points to the buffer
        drawn_points = []
        for px, py in points:
            if 0 <= px < self.matrix.width and 0 <= py < self.matrix.height:
                self._draw_to_buffers(px, py, rgb_color[0], rgb_color[1], rgb_color[2])
                drawn_points.append((px, py))
        
        self._maybe_swap_buffer()
        
        # Register with burnout manager if duration specified
        if burnout is not None and burnout >= 0:
            mode = BurnoutMode.FADE if burnout_mode.lower() == "fade" else BurnoutMode.INSTANT
            pixel_colors = [rgb_color] * len(drawn_points) if mode == BurnoutMode.FADE else None
            self.burnout_manager.add_object(
                ShapeType.ARC, (x1, y1, x2, y2, bulge), drawn_points, burnout, mode, pixel_colors
            )
        
        debug(f"Arc drawn with {len(drawn_points)} pixels", Level.TRACE, Component.DRAWING)

    def draw_text(self, x: int, y: int, text: Any, font_name: str, font_size: int, 
                color: Union[str, int], intensity: int = 100, effect: Union[str, TextEffect] = "NORMAL",
                modifier: Optional[Union[str, EffectModifier]] = None) -> None:
        """Draw text on the LED matrix."""
        rgb_color = self._get_color(color, intensity)
        text = str(text)  # Convert to string
        text_effect = effect if isinstance(effect, TextEffect) else TextEffect[effect.upper()]
        effect_modifier = modifier if isinstance(modifier, EffectModifier) else \
                        (EffectModifier[modifier.upper()] if modifier else None)
        self.text_renderer.render_text(x, y, text, font_name, font_size, rgb_color, text_effect, effect_modifier)
        self._maybe_swap_buffer()

    def clear_text(self, x: int, y: int) -> None:
        """Clear text at specified coordinates."""
        self.text_renderer.clear_text(x, y)
        self._maybe_swap_buffer()

    # Utility Methods
    def clear(self):
        """Clear both buffers and hide background."""
        self.drawing_buffer.fill(0)
        self.canvas.Fill(0, 0, 0)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        if not self.frame_mode:
            self.canvas.Fill(0, 0, 0)
        self.background_manager.hide_background()
        self.burnout_manager.clear_all()
        self.current_command_pixels.clear()

    def rest(self, duration: float):
        """Rest for a duration while still checking burnouts."""
        debug(f"Resting for {duration} seconds", Level.DEBUG, Component.COMMAND)
        end_time = time.time() + duration
        last_refresh_time = time.time()
        refresh_interval = 0.05  # Refresh display every 50ms
        
        while time.time() < end_time:
            current_time = time.time()
            
            # Check if it's time for a display refresh
            if current_time - last_refresh_time >= refresh_interval:
                # Refresh if not in frame mode AND (burnouts have made changes OR active fades exist)
                if not self.frame_mode and (self.burnout_manager.check_and_reset_changes() or 
                                            self.burnout_manager.has_active_fades()):
                    debug("Refreshing display due to burnout/fade changes", Level.TRACE, Component.SYSTEM)
                    self._maybe_swap_buffer()
                    self.refresh_display()
                last_refresh_time = current_time
                
            # Sleep for a small amount of time
            time.sleep(min(0.01, end_time - current_time))

    # Sprite Management Methods
    def show_sprite(self, name: str, x: float, y: float, instance_id: int = 0, 
                    z_index: int = 0, cel_idx: Optional[int] = None):
        """
        Show a sprite instance at specified position. Creates the instance if it doesn't exist.
        
        Args:
            name: Sprite template name
            x, y: Position on screen
            instance_id: Instance identifier (default 0)
            z_index: Z-order for layering (default 0)
            cel_idx: Which animation cel to display. If None, preserves current cel for 
                     existing instances or uses 0 for new instances.
        """
        debug(f"Showing sprite '{name}' instance {instance_id} at ({x}, {y})" + 
              (f" cel {cel_idx}" if cel_idx is not None else ""), 
            Level.INFO, Component.SPRITE)
        
        # Get or create the instance
        instance = self.sprite_manager.get_instance(name, instance_id)
        is_new_instance = False
        
        if not instance:
            # Create new instance from template - use cel_idx or default to 0
            initial_cel = cel_idx if cel_idx is not None else 0
            instance = self.sprite_manager.create_instance(name, instance_id, x, y, z_index, initial_cel)
            if not instance:
                debug(f"Cannot show sprite '{name}' instance {instance_id}: template doesn't exist", 
                    Level.ERROR, Component.SPRITE)
                return
            is_new_instance = True
        
        # If already visible, mark old position dirty
        if instance.visible:
            old_cells = get_grid_cells(int(instance.x), int(instance.y), instance.width, instance.height)
            self._mark_cells_dirty(old_cells)
        
        # Update instance state
        instance.x = int(x)
        instance.y = int(y)
        instance.visible = True
        
        # Only change cel if explicitly specified, or if this is a new instance
        if cel_idx is not None:
            instance.set_cel(cel_idx)
        # If not specified and existing instance, preserve current cel (do nothing)
        
        new_cells = set(get_grid_cells(int(x), int(y), instance.width, instance.height))
        instance.occupied_cells = new_cells
        
        if not self.frame_mode:
            self._restore_dirty_cells()
            self.copy_sprite_to_buffer(instance, self.canvas)
            self._maybe_swap_buffer()
            self.refresh_display()
        #else:
        #    self._restore_dirty_cells()  # Restore old position's background
        #    self.copy_sprite_to_buffer(instance, self.canvas)  # Draw new position

    def hide_sprite(self, name: str, instance_id: int = 0):
        """
        Hide a specific sprite instance.
        Note: Maintains current cel state (does NOT reset to cel 0).
        """
        debug(f"Hiding sprite '{name}' instance {instance_id}", Level.INFO, Component.SPRITE)
        
        instance = self.sprite_manager.get_instance(name, instance_id)
        if instance and instance.visible:
            cells = get_grid_cells(int(instance.x), int(instance.y), instance.width, instance.height)
            self._mark_cells_dirty(cells)
            instance.visible = False
            instance.occupied_cells.clear()
            if not self.frame_mode:
                self._restore_dirty_cells()
                self.refresh_display()
                self._maybe_swap_buffer()

    def move_sprite(self, name: str, x: float, y: float, instance_id: int = 0, cel_idx: Optional[int] = None):
        """
        Move a specific sprite instance to a new position.
        
        Args:
            name: Sprite template name
            x, y: New position on screen
            instance_id: Instance identifier (default 0)
            cel_idx: If specified, set to this cel. If None, auto-advance to next cel.
        
        Auto-Advance Behavior:
            - Without cel_idx: Automatically advances to next cel (current_cel + 1)
            - With cel_idx: Jumps to specified cel
            - Wrapping: When reaching last cel, wraps to cel 0
        """
        debug(f"Moving sprite '{name}' instance {instance_id} to ({x}, {y})" + 
              (f" cel {cel_idx}" if cel_idx is not None else " (auto-advance)"), 
            Level.INFO, Component.SPRITE)
        
        instance = self.sprite_manager.get_instance(name, instance_id)
        if instance and instance.visible:
            # Mark old position dirty
            old_cells = get_grid_cells(int(instance.x), int(instance.y), instance.width, instance.height)
            self._mark_cells_dirty(old_cells)
            
            # Update position
            instance.x = int(x)
            instance.y = int(y)
            
            # Handle cel animation
            if cel_idx is not None:
                # Explicit cel specified - jump to it
                instance.set_cel(cel_idx)
            else:
                # Auto-advance to next cel (with wrap)
                instance.advance_cel()
            
            # Update occupied cells
            new_cells = set(get_grid_cells(int(x), int(y), instance.width, instance.height))
            instance.occupied_cells = new_cells
            
            if not self.frame_mode:
                self._restore_dirty_cells()
                self.copy_sprite_to_buffer(instance, self.canvas)
                self._maybe_swap_buffer()
                self.refresh_display()
            #else:
            #    self._restore_dirty_cells()  # Restore Background from drawing_buffer
            #    self.copy_sprite_to_buffer(instance, self.canvas)
                
    def dispose_sprite_instance(self, name: str, instance_id: int):
        """Remove a specific sprite instance."""
        debug(f"Disposing of sprite '{name}' instance {instance_id}", 
            Level.INFO, Component.SPRITE)
        
        dirty_cells = self.sprite_manager.dispose_sprite_instance(name, instance_id)
        if dirty_cells:
            self._mark_cells_dirty(dirty_cells)
            if not self.frame_mode:
                self._restore_dirty_cells()
                self.refresh_display()

    def refresh_display(self):
        """Refresh the display with all layers in correct order."""
        # If background is active, composite background + drawing_buffer first
        if self.background_manager.has_background():
            bg_viewport = self.background_manager.get_viewport(self.matrix.width, self.matrix.height)
            mask = np.any(self.drawing_buffer != 0, axis=2)
            bg_viewport[mask] = self.drawing_buffer[mask]
            pil_image = Image.fromarray(bg_viewport, mode='RGB')
            self.canvas.SetImage(pil_image)

        # Then draw all visible sprites on top in z-order
        for sprite_name, instance_id in self.sprite_manager.z_order:
            instance = self.sprite_manager.get_instance(sprite_name, instance_id)
            if instance and instance.visible:
                self.copy_sprite_to_buffer(instance, self.canvas)
        self._maybe_swap_buffer()

    def copy_sprite_to_buffer(self, sprite: Union[SpriteInstance, MatrixSprite], dest_buffer):
        """
        Copy sprite pixels to the destination buffer.
        Works with both SpriteInstance (uses current_cel) and MatrixSprite (uses active_cel).
        """
        if isinstance(sprite, SpriteInstance):
            x, y = int(sprite.x), int(sprite.y)
        else:
            # MatrixSprite doesn't have x/y attributes; draw at origin
            x, y = 0, 0
        start_x = max(0, x)
        start_y = max(0, y)
        end_x = min(self.matrix.width, x + sprite.width)
        end_y = min(self.matrix.height, y + sprite.height)
        sprite_start_x = max(0, -x)
        sprite_start_y = max(0, -y)
        pixels_copied = 0
        pixels_skipped = 0
        for sy in range(sprite_start_y, sprite.height):
            dy = y + sy
            if dy >= end_y:
                break
            if dy < start_y:
                continue
            for sx in range(sprite_start_x, sprite.width):
                dx = x + sx
                if dx >= end_x:
                    break
                if dx < start_x:
                    continue
                r, g, b = sprite.buffer[sy][sx]
                if (r, g, b) != TRANSPARENT_COLOR:
                    intensity = sprite.intensity_buffer[sy][sx]
                    scale = intensity / 100.0
                    scaled_rgb = (int(r * scale), int(g * scale), int(b * scale))
                    debug(f"Copying sprite pixel ({dx}, {dy}) with RGB {scaled_rgb} (intensity: {intensity}%)", 
                        Level.TRACE, Component.SPRITE)
                    dest_buffer.SetPixel(dx, dy, scaled_rgb[0], scaled_rgb[1], scaled_rgb[2])
                    pixels_copied += 1
                else:
                    pixels_skipped += 1
        debug(f"Sprite copy complete: {pixels_copied} pixels copied, {pixels_skipped} skipped", 
            Level.TRACE, Component.SPRITE)
    
    def clear_sprite_position(self, sprite: Union[SpriteInstance, MatrixSprite], dest_buffer):
        """Clear the sprite's current position with black."""
        if isinstance(sprite, SpriteInstance):
            x, y = round(sprite.x), round(sprite.y)
        else:
            # MatrixSprite doesn't have x/y attributes; clear at origin
            x, y = 0, 0
        start_x = max(0, x)
        start_y = max(0, y)
        end_x = min(self.matrix.width, x + sprite.width)
        end_y = min(self.matrix.height, y + sprite.height)
        for dy in range(start_y, end_y):
            for dx in range(start_x, end_x):
                dest_buffer.SetPixel(dx, dy, 0, 0, 0)

    def draw_to_sprite(self, name: str, command: str, *args):
        """Execute a drawing command on a sprite template being defined."""
        debug(f"Drawing to sprite {name}: {command} {args}", Level.DEBUG, Component.SPRITE)
        
        # Get the sprite template - either currently being defined or already stored
        sprite = self.sprite_manager.get_drawing_target()
        if sprite is None or sprite.name != name:
            sprite = self.sprite_manager.get_template(name)
        
        if not sprite:
            debug(f"Error: Sprite template '{name}' not found", Level.ERROR, Component.SPRITE)
            return

        try:
            if command == 'plot' and len(args) >= 3:
                x, y, color = args[:3]
                intensity = int(args[3]) if len(args) > 3 else 100
                sprite.plot(int(x), int(y), color, intensity)
            elif command == 'draw_line' and len(args) >= 5:
                x1, y1, x2, y2, color = args[:5]
                intensity = int(args[5]) if len(args) > 5 else 100
                sprite.draw_line(int(x1), int(y1), int(x2), int(y2), color, intensity)
            elif command == 'draw_rectangle' and len(args) >= 5:
                x, y, width, height, color = args[:5]
                intensity = int(args[5]) if len(args) > 5 else 100
                fill = bool(args[6]) if len(args) > 6 else False
                sprite.draw_rectangle(int(x), int(y), int(width), int(height), color, intensity, fill)
            elif command == 'draw_circle' and len(args) >= 4:
                x, y, radius, color = args[:4]
                intensity = int(args[4]) if len(args) > 4 else 100
                fill = bool(args[5]) if len(args) > 5 else False
                sprite.draw_circle(int(x), int(y), int(radius), color, intensity, fill)
            elif command == 'draw_polygon' and len(args) >= 5:
                x, y, radius, sides, color = args[:5]
                intensity = int(args[5]) if len(args) > 5 else 100
                rotation = float(args[6]) if len(args) > 6 else 0
                fill = bool(args[7]) if len(args) > 7 else False
                sprite.draw_polygon(int(x), int(y), int(radius), int(sides), color, intensity, rotation, fill)
            elif command == 'draw_ellipse' and len(args) >= 5:
                x, y, x_radius, y_radius, color = args[:5]
                intensity = int(args[5]) if len(args) > 5 else 100
                fill = bool(args[6]) if len(args) > 6 else False
                rotation = float(args[7]) if len(args) > 7 else 0
                sprite.draw_ellipse(int(x), int(y), int(x_radius), int(y_radius), 
                                color, intensity, fill, rotation)
            elif command == 'draw_arc' and len(args) >= 6:
                x1, y1, x2, y2, arc_height, color = args[:6]
                intensity = int(args[6]) if len(args) > 6 else 100
                fill = bool(args[7]) if len(args) > 7 else False
                sprite.draw_arc(int(x1), int(y1), int(x2), int(y2), float(arc_height), color, intensity, fill)
            elif command == 'clear':
                sprite.clear()
            else:
                debug(f"Unsupported sprite command: {command}", Level.ERROR, Component.SPRITE)
                raise ValueError(f"Unsupported sprite command: {command}")
            debug(f"Successfully executed {command} on sprite {name}", Level.DEBUG, Component.SPRITE)
        except Exception as e:
            debug(f"Error executing sprite command: {e}", Level.ERROR, Component.SPRITE)
            raise

    def execute_command(self, command: str) -> None:
        """Execute a single command."""
        debug(f"Executing command: {command}", Level.INFO, Component.COMMAND)
        if not command.strip():
            debug("Empty command received, ignoring", Level.WARNING, Component.COMMAND)
            return
        if not hasattr(self, 'command_executor'):
            debug("Creating new CommandExecutor instance", Level.DEBUG, Component.COMMAND)
            self.command_executor = CommandExecutor(self)
        try:
            self.command_executor.execute_command(command)
            debug("Command executed successfully", Level.DEBUG, Component.COMMAND)
        except Exception as e:
            debug(f"Command execution failed: {str(e)}", Level.ERROR, Component.COMMAND)
            raise

    # Grid Management (unchanged)
    def _mark_cells_dirty(self, cells: List[Tuple[int, int]]):
        for gx, gy in cells:
            if 0 <= gx < self.grid_dirty.shape[1] and 0 <= gy < self.grid_dirty.shape[0]:
                self.grid_dirty[gy, gx] = True

    def _restore_cell(self, grid_x: int, grid_y: int, bg_viewport: Optional[np.ndarray] = None):
        """Restore a cell from background (if active) + drawing_buffer."""
        start_x = grid_x * GRID_SIZE
        start_y = grid_y * GRID_SIZE
        end_x = min(start_x + GRID_SIZE, self.matrix.width)
        end_y = min(start_y + GRID_SIZE, self.matrix.height)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # Start with background or black
                if bg_viewport is not None:
                    r, g, b = int(bg_viewport[y, x, 0]), int(bg_viewport[y, x, 1]), int(bg_viewport[y, x, 2])
                else:
                    r, g, b = 0, 0, 0
                # Overlay drawing_buffer if non-black
                db_color = self.drawing_buffer[y, x]
                if db_color[0] != 0 or db_color[1] != 0 or db_color[2] != 0:
                    r, g, b = int(db_color[0]), int(db_color[1]), int(db_color[2])
                self.canvas.SetPixel(x, y, r, g, b)
                if not self.frame_mode:
                    self.current_command_pixels.append((x, y, r, g, b))

    def _restore_dirty_cells(self):
        # Compute background viewport once for all dirty cells
        bg_viewport = None
        if self.background_manager.has_background():
            bg_viewport = self.background_manager.get_viewport(self.matrix.width, self.matrix.height)

        dirty_yx = np.where(self.grid_dirty)
        for grid_y, grid_x in zip(dirty_yx[0], dirty_yx[1]):
            self._restore_cell(grid_x, grid_y, bg_viewport)
            self.grid_dirty[grid_y, grid_x] = False
            cell_sprites = self.sprite_manager.get_overlapping_sprites([(grid_x, grid_y)])
            for sprite in cell_sprites:
                self.copy_sprite_to_buffer(sprite, self.canvas)

    def cleanup(self):
        """Clean up resources."""
        print("\nStarting RGB_Api instance cleanup...")
        try:
            if self.frame_mode:
                print("RGB_Api cleanup: ending frame mode")
                self.end_frame()
            print("RGB_Api cleanup: clearing display")
            self.clear()
            print("RGB_Api cleanup: stopping burnout manager")
            self.burnout_manager.stop()
            print("RGB_Api cleanup: burnout manager stopped")
        except Exception as e:
            print(f"ERROR during RGB_Api cleanup: {str(e)}")
        finally:
            print("RGB_Api instance cleanup complete")