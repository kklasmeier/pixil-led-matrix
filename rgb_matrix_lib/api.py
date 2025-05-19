# File: rgb_matrix_lib/api.py

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import time
import math
from .drawing_objects import DrawingObject, ShapeType, ThreadedBurnoutManager
from .utils import get_color_rgb, polygon_vertices, TRANSPARENT_COLOR, GRID_SIZE, get_grid_cells  # Added get_grid_cells
from typing import Optional, List, Tuple, Union, Any
from .debug import debug, Level, Component
from .sprite import MatrixSprite, SpriteManager
import numpy as np
from .text_effects import TextEffect, EffectModifier
from .text_renderer import TextRenderer
from .commands import CommandExecutor  # Added CommandExecutor import

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
        self.text_renderer = TextRenderer(self)
        self.burnout_manager = ThreadedBurnoutManager(self)
        self.burnout_manager.start()
                
        debug("RGB_Api initialization complete", Level.INFO, Component.SYSTEM)

    def dispose_all_sprites(self):
        """Remove all sprites from memory and clear them from display."""
        debug("Disposing all sprites", Level.INFO, Component.SPRITE)
        dirty_cells = self.sprite_manager.dispose_all_sprites()
        if dirty_cells:
            self._mark_cells_dirty(dirty_cells)
            if not self.frame_mode:
                self._restore_dirty_cells()
                self.refresh_display()
        debug("All sprites disposed", Level.DEBUG, Component.SPRITE)

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
                rgb = tuple(int(c * scale) for c in color)
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
            self.canvas.Fill(0, 0, 0) # Clears the current canvas if not preserving

    def end_frame(self):
        if self.frame_mode:
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
            self.refresh_display()
            self.frame_mode = False
            self.preserve_frame_changes = False

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
    def plot(self, x: int, y: int, color: Union[str, int], intensity: int = 100, burnout: Optional[int] = None):
        """Plot a single pixel."""
        rgb_color = self._get_color(color, intensity)
        debug(f"Plotting point at ({x}, {y}) with color {color} at {intensity}% -> RGB {rgb_color}", 
              Level.TRACE, Component.DRAWING)
        
        if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
            self._draw_to_buffers(x, y, rgb_color[0], rgb_color[1], rgb_color[2])
            self._maybe_swap_buffer()

            if burnout is not None:
                self.burnout_manager.add_object(
                    ShapeType.POINT, (x, y), [(x, y)], burnout
                )
        else:
            debug(f"Plot point ({x}, {y}) outside matrix bounds", Level.TRACE, Component.DRAWING)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: Union[str, int], 
                  intensity: int = 100, burnout: Optional[int] = None):
        """Draw a line between two points."""
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

        if burnout is not None:
            self.burnout_manager.add_object(
                ShapeType.LINE, (x0, y0, x1, y1), points, burnout
            )

    def draw_rectangle(self, x: int, y: int, width: int, height: int, color: Union[str, int], 
                    intensity: int = 100, fill: bool = False, burnout: Optional[int] = None):
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

        if burnout is not None:
            self.burnout_manager.add_object(
                ShapeType.RECTANGLE, (x, y, width, height), points, burnout
            )

    def draw_circle(self, x_center: int, y_center: int, radius: int, color: Union[str, int], 
                    intensity: int = 100, fill: bool = False, burnout: Optional[int] = None):
        """Draw a circle."""
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

        if burnout is not None:
            self.burnout_manager.add_object(
                ShapeType.CIRCLE, (x_center, y_center, radius), list(points), burnout
            )

    def draw_polygon(self, x_center: int, y_center: int, radius: int, sides: int, color: Union[str, int], 
                     intensity: int = 100, rotation: float = 0, fill: bool = False, burnout: Optional[int] = None):
        """Draw a regular polygon."""
        rgb_color = self._get_color(color, intensity)
        debug(f"Drawing polygon: center({x_center}, {y_center}), radius={radius}, sides={sides}", 
              Level.DEBUG, Component.DRAWING)
        vertices = polygon_vertices(x_center, y_center, radius, sides, rotation)
        burnout_points = set() if burnout is not None else None
        
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

        if burnout is not None:
            self.burnout_manager.add_object(
                ShapeType.POLYGON, (x_center, y_center, radius), list(burnout_points), burnout
            )

    def draw_ellipse(self, x_center: int, y_center: int, x_radius: int, y_radius: int, color: Union[str, int], 
                    intensity: int = 100, fill: bool = False, rotation: float = 0, burnout: Optional[int] = None):
        """Draw an ellipse with optional rotation."""
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
            
            if burnout is not None:
                self.burnout_manager.add_object(
                    ShapeType.ELLIPSE, (x_center, y_center, x_radius, y_radius, rotation), 
                    list(points), burnout
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
        
        if burnout is not None:
            self.burnout_manager.add_object(
                ShapeType.ELLIPSE, (x_center, y_center, x_radius, y_radius, rotation), 
                list(points), burnout
            )

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
        """Clear both buffers."""
        self.drawing_buffer.fill(0)
        self.canvas.Fill(0, 0, 0)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        if not self.frame_mode:
            self.canvas.Fill(0, 0, 0)
        self.burnout_manager.clear_all()
        self.current_command_pixels.clear()

    def rest(self, duration: float):
        """Rest for a duration while still checking burnouts."""
        debug(f"Resting for {duration} seconds", Level.DEBUG, Component.COMMAND)
        end_time = time.time() + duration
        last_refresh_time = time.time()
        refresh_interval = 0.05  # Refresh display every 100ms
        
        while time.time() < end_time:
            current_time = time.time()
            
            # Check if it's time for a display refresh
            if current_time - last_refresh_time >= refresh_interval:
                # Only refresh if not in frame mode AND burnouts have made changes
                if not self.frame_mode and self.burnout_manager.check_and_reset_changes():
                    debug("Refreshing display due to burnout changes", Level.TRACE, Component.SYSTEM)
                    self._maybe_swap_buffer()
                    self.refresh_display()
                last_refresh_time = current_time
                
            # Sleep for a small amount of time
            time.sleep(min(0.01, end_time - current_time))

    # Sprite Management Methods
    def show_sprite(self, name: str, x: float, y: float, instance_id: int = 0):
        """Show a sprite instance at specified position. Creates the instance if it doesn't exist."""
        debug(f"Showing sprite '{name}' instance {instance_id} at ({x}, {y})", 
            Level.INFO, Component.SPRITE)
        
        sprite = self.sprite_manager.get_sprite(name, instance_id)
        
        # If this instance doesn't exist yet, create it
        if not sprite and instance_id > 0:
            # Get the template sprite (instance 0)
            template = self.sprite_manager.get_sprite(name, 0)
            if template:
                # Create new instance 
                sprite = self.sprite_manager.create_sprite_instance(name, instance_id)
            else:
                debug(f"Cannot show sprite '{name}' instance {instance_id}: template doesn't exist", 
                    Level.ERROR, Component.SPRITE)
                return
        
        if sprite:
            if sprite.visible:
                old_cells = get_grid_cells(int(sprite.x), int(sprite.y), sprite.width, sprite.height)
                self._mark_cells_dirty(old_cells)
            sprite.x = x
            sprite.y = y
            sprite.visible = True
            new_cells = set(get_grid_cells(int(x), int(y), sprite.width, sprite.height))
            sprite.occupied_cells = new_cells
            if not self.frame_mode:
                self._restore_dirty_cells()
                self.copy_sprite_to_buffer(sprite, self.canvas)
                self._maybe_swap_buffer()
                self.refresh_display()
            else:
                self._restore_dirty_cells()  # Restore old position's background
                self.copy_sprite_to_buffer(sprite, self.canvas)  # Draw new position

    def hide_sprite(self, name: str, instance_id: int = 0):
        """Hide a specific sprite instance."""
        debug(f"Hiding sprite '{name}' instance {instance_id}", Level.INFO, Component.SPRITE)
        
        sprite = self.sprite_manager.get_sprite(name, instance_id)
        if sprite and sprite.visible:
            cells = get_grid_cells(int(sprite.x), int(sprite.y), sprite.width, sprite.height)
            self._mark_cells_dirty(cells)
            sprite.visible = False
            sprite.occupied_cells.clear()
            if not self.frame_mode:
                self._restore_dirty_cells()
                self.refresh_display()
                self._maybe_swap_buffer()

    def move_sprite(self, name: str, x: float, y: float, instance_id: int = 0):
        """Move a specific sprite instance to a new position."""
        debug(f"Moving sprite '{name}' instance {instance_id} to ({x}, {y})", 
            Level.INFO, Component.SPRITE)
        
        sprite = self.sprite_manager.get_sprite(name, instance_id)
        if sprite and sprite.visible:
            old_cells = get_grid_cells(int(sprite.x), int(sprite.y), sprite.width, sprite.height)
            self._mark_cells_dirty(old_cells)
            # Remove explicit clear to black
            sprite.x = x
            sprite.y = y
            new_cells = set(get_grid_cells(int(x), int(y), sprite.width, sprite.height))
            sprite.occupied_cells = new_cells
            if not self.frame_mode:
                self._restore_dirty_cells()
                self.copy_sprite_to_buffer(sprite, self.canvas)
                self._maybe_swap_buffer()
                self.refresh_display()
            else:
                self._restore_dirty_cells()  # Restore Background from drawing_buffer
                self.copy_sprite_to_buffer(sprite, self.canvas)
                
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
        """Refresh the display with all visible sprites in z-order."""
        for sprite_name, instance_id in self.sprite_manager.z_order:
            sprite = self.sprite_manager.get_sprite(sprite_name, instance_id)
            if sprite and sprite.visible:
                self.copy_sprite_to_buffer(sprite, self.canvas)
        self._maybe_swap_buffer()

    def copy_sprite_to_buffer(self, sprite: MatrixSprite, dest_buffer):
        x, y = round(sprite.x), round(sprite.y)
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
    
    def clear_sprite_position(self, sprite: MatrixSprite, dest_buffer):
        """Clear the sprite's current position with black."""
        x, y = round(sprite.x), round(sprite.y)
        start_x = max(0, x)
        start_y = max(0, y)
        end_x = min(self.matrix.width, x + sprite.width)
        end_y = min(self.matrix.height, y + sprite.height)
        for dy in range(start_y, end_y):
            for dx in range(start_x, end_x):
                dest_buffer.SetPixel(dx, dy, 0, 0, 0)

    def draw_to_sprite(self, name: str, command: str, *args):
        """Execute a drawing command on a sprite."""
        debug(f"(ktest) Drawing to sprite {name}: {command} {args}", Level.DEBUG, Component.SPRITE)
        sprite = self.sprite_manager.get_sprite(name)
        if not sprite:
            debug(f"Error: Sprite '{name}' not found", Level.ERROR, Component.SPRITE)
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

    def _restore_cell(self, grid_x: int, grid_y: int):
        start_x = grid_x * GRID_SIZE
        start_y = grid_y * GRID_SIZE
        end_x = min(start_x + GRID_SIZE, self.matrix.width)
        end_y = min(start_y + GRID_SIZE, self.matrix.height)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                color = self.drawing_buffer[y, x]
                self.canvas.SetPixel(x, y, int(color[0]), int(color[1]), int(color[2]))
                if not self.frame_mode:
                    self.current_command_pixels.append((x, y, int(color[0]), int(color[1]), int(color[2])))

    def _restore_dirty_cells(self):
        dirty_yx = np.where(self.grid_dirty)
        for grid_y, grid_x in zip(dirty_yx[0], dirty_yx[1]):
            self._restore_cell(grid_x, grid_y)
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