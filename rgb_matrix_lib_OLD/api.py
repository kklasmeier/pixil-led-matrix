# File: rgb_matrix_lib/api.py

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import time
from .drawing_objects import DrawingObject, ShapeType, ThreadedBurnoutManager
from .utils import get_color_palette, get_grid_cells, is_cell_empty, parse_color_spec, get_color_rgb, polygon_vertices, TRANSPARENT_COLOR, GRID_SIZE
from typing import Optional, List, Tuple, Union
from .debug import debug, Level, Component
from .sprite import MatrixSprite, SpriteManager
import numpy as np
from .text_effects import TextEffect, EffectModifier
from .text_renderer import TextRenderer  # Add this import

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

# Alias for backward compatibility
execute_single_command = execute_command

def cleanup() -> None:
    """Clean up resources and reset the LED matrix."""
    global _api_instance
    if _api_instance is not None:
        _api_instance.clear()
        _api_instance = None
        
class RGB_Api:
    def __init__(self):
        debug("Initializing RGB_Api", Level.INFO, Component.SYSTEM)
        
        # Configure matrix with optimal settings
        self.options = self._configure_matrix_options()
        self.matrix = RGBMatrix(options=self.options)
        self.offscreen_canvas = self.matrix.CreateFrameCanvas()

        # Initialize buffers and grid
        self.drawing_buffer = np.zeros((self.matrix.height, self.matrix.width, 3), dtype=np.uint8)
        grid_cells_y = self.matrix.height // GRID_SIZE
        grid_cells_x = self.matrix.width // GRID_SIZE
        self.grid_dirty = np.zeros((grid_cells_y, grid_cells_x), dtype=bool)

        # Initialize components
        self.color_palette = get_color_palette()
        self.drawing_objects = [] #KJK Does this go away?
        self.frame_mode = False
        self.sprite_manager = SpriteManager()
        self.text_renderer = TextRenderer(self) 

        self.burnout_manager = ThreadedBurnoutManager(self)
        self.burnout_manager.start()
                
        debug("RGB_Api initialization complete", Level.INFO, Component.SYSTEM)

    def dispose_all_sprites(self):
        """
        Remove all sprites from memory and clear them from display.
        """
        debug("Disposing all sprites", Level.INFO, Component.SPRITE)
        
        # Get dirty cells from sprite disposal
        dirty_cells = self.sprite_manager.dispose_all_sprites()
        
        if dirty_cells:  # Only process if there were visible sprites
            # Mark affected cells as dirty
            self._mark_cells_dirty(dirty_cells)
            
            if not self.frame_mode:
                # Restore the background for affected cells
                self._restore_dirty_cells()
                self.refresh_display()
                
        debug("All sprites disposed", Level.DEBUG, Component.SPRITE)

    def _configure_matrix_options(self):
        """Configure and return matrix options."""
        debug("Configuring matrix options", Level.DEBUG, Component.MATRIX)
        options = RGBMatrixOptions()
        options.rows = 64
        options.cols = 64
        options.hardware_mapping = 'adafruit-hat'
        options.gpio_slowdown = 3
        options.scan_mode = 1
        options.pwm_bits = 11
        debug(f"Matrix configured: {options.rows}x{options.cols}", Level.DEBUG, Component.MATRIX)
        return options

    # In api.py - RGB_Api class

    def _get_color(self, color: Union[str, tuple[int, int, int]]) -> tuple[int, int, int]:
        """
        Get RGB tuple for a color input.
        
        Args:
            color: Either RGB tuple from command parser or a color name string
                (color name string support kept for backward compatibility)
        
        Returns:
            tuple[int, int, int]: RGB color values
        """
        if isinstance(color, tuple) and len(color) == 3:
            debug(f"Using pre-calculated RGB color: {color}", Level.TRACE, Component.DRAWING)
            return color
            
        # Backward compatibility for direct color name usage
        color_str = str(color).lower()
        rgb = self.color_palette.get(color_str, self.color_palette["white"])
        debug(f"Color {color_str} resolved to RGB: {rgb}", Level.TRACE, Component.DRAWING)
        return rgb

    # Frame Management Methods
    def begin_frame(self):
        """Enter frame buffer mode - drawing commands won't display until end_frame"""
        debug("Beginning frame mode", Level.DEBUG, Component.MATRIX)
        self.frame_mode = True
    
    def end_frame(self):
        """Exit frame buffer mode and display all buffered changes"""
        if self.frame_mode:
            debug("Ending frame mode, swapping buffers", Level.DEBUG, Component.MATRIX)
            self.matrix.SwapOnVSync(self.offscreen_canvas)
            self.frame_mode = False
    
    def _maybe_swap_buffer(self):
        """Internal helper to handle buffer swapping based on mode"""
        if not self.frame_mode:
            debug("Swapping display buffer", Level.TRACE, Component.MATRIX)
            self.matrix.SwapOnVSync(self.offscreen_canvas)

    # Drawing Object Management
    def check_burnouts(self):
        """Check for and handle any pixels that need to burn out"""
        expired_objects = self.burnout_manager.process_burnouts()
        
        if expired_objects:
            debug(f"Processing {len(expired_objects)} burnout objects", 
                Level.TRACE, Component.DRAWING)
            
            for obj in expired_objects:
                region = obj.get_region()
                
                # Fast path for rectangles
                if region.shape_type == ShapeType.RECTANGLE:
                    x, y, width, height = region.bounds
                    # Clamp coordinates to matrix boundaries
                    start_x = max(0, x)
                    start_y = max(0, y)
                    end_x = min(x + width, self.matrix.width)
                    end_y = min(y + height, self.matrix.height)
                    
                    # Clear rectangle area only within bounds
                    for i in range(start_x, end_x):
                        for j in range(start_y, end_y):
                            self._draw_to_buffers(i, j, 0, 0, 0)
                else:
                    # For other shapes, clear individual points
                    # Points list already contains only in-bounds points
                    for point in obj.get_points():
                        self._draw_to_buffers(point[0], point[1], 0, 0, 0)
                
            self._maybe_swap_buffer()
            return True
        return False

    # Basic Drawing Methods
    def plot(self, x, y, color_name, burnout=None):
        """Plot a single pixel."""
        debug(f"Plotting point at ({x}, {y}) with color {color_name}", Level.DEBUG, Component.DRAWING)
        
        if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
            color = self._get_color(color_name)
            self._draw_to_buffers(x, y, color[0], color[1], color[2])
            
            if burnout is not None:
                self.burnout_manager.add_object(
                    ShapeType.POINT,
                    (x, y),
                    [(x, y)],
                    burnout
                )

            self._maybe_swap_buffer()
        else:
            debug(f"Plot point ({x}, {y}) outside matrix bounds", Level.TRACE, Component.DRAWING)

    def draw_line(self, x0, y0, x1, y1, color_name, burnout=None):
        """Draw a line between two points."""
        color = self._get_color(color_name)
        points = []
        
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            if 0 <= x0 < self.matrix.width and 0 <= y0 < self.matrix.height:
                self._draw_to_buffers(x0, y0, color[0], color[1], color[2])
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

        if burnout is not None:
            self.burnout_manager.add_object(
                ShapeType.LINE,
                (x0, y0, x1, y1),
                points,
                burnout
            )

        self._maybe_swap_buffer()

    def draw_rectangle(self, x, y, width, height, color_name, fill=False, burnout=None):
        """Draw a rectangle."""
        color = self._get_color(color_name)
        points = []
        
        if fill:
            for i in range(max(0, x), min(x + width, self.matrix.width)):
                for j in range(max(0, y), min(y + height, self.matrix.height)):
                    self._draw_to_buffers(i, j, color[0], color[1], color[2])
                    points.append((i, j))
        else:
            # Draw horizontal lines
            for i in range(max(0, x), min(x + width, self.matrix.width)):
                if 0 <= y < self.matrix.height:
                    self._draw_to_buffers(i, y, color[0], color[1], color[2])
                    points.append((i, y))
                if 0 <= y + height - 1 < self.matrix.height:
                    self._draw_to_buffers(i, y + height - 1, color[0], color[1], color[2])
                    points.append((i, y + height - 1))
            
            # Draw vertical lines
            for j in range(max(0, y), min(y + height, self.matrix.height)):
                if 0 <= x < self.matrix.width:
                    self._draw_to_buffers(x, j, color[0], color[1], color[2])
                    points.append((x, j))
                if 0 <= x + width - 1 < self.matrix.width:
                    self._draw_to_buffers(x + width - 1, j, color[0], color[1], color[2])
                    points.append((x + width - 1, j))

        if burnout is not None:
            # Add rectangle to burnout manager with region info
            self.burnout_manager.add_object(
                ShapeType.RECTANGLE,
                (x, y, width, height),
                points,
                burnout
            )

        self._maybe_swap_buffer()

    def draw_circle(self, x_center, y_center, radius, color_name, fill=False, burnout=None):
        """Draw a circle."""
        color = self._get_color(color_name)
        points = set()

        def plot_circle_points(x, y):
            for dx, dy in [(x, y), (-x, y), (x, -y), (-x, -y), (y, x), (-y, x), (y, -x), (-y, -x)]:
                px, py = x_center + dx, y_center + dy
                if 0 <= px < self.matrix.width and 0 <= py < self.matrix.height:
                    self._draw_to_buffers(px, py, color[0], color[1], color[2])
                    points.add((px, py))
                    
        def draw_line(x0, y0, x1, y1):
            for x in range(max(0, x0), min(x1 + 1, self.matrix.width)):
                if 0 <= y0 < self.matrix.height:
                    self._draw_to_buffers(x, y0, color[0], color[1], color[2])
                    points.add((x, y0))

        x, y = 0, radius
        d = 3 - 2 * radius

        while y >= x:
            if fill:
                draw_line(x_center - x, y_center - y, x_center + x, y_center - y)
                draw_line(x_center - x, y_center + y, x_center + x, y_center + y)
                draw_line(x_center - y, y_center - x, x_center + y, y_center - x)
                draw_line(x_center - y, y_center + x, x_center + y, y_center + x)
            else:
                plot_circle_points(x, y)

            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6

        if burnout is not None:
            self.burnout_manager.add_object(
                ShapeType.CIRCLE,
                (x_center, y_center, radius),
                list(points),
                burnout
            )

        self._maybe_swap_buffer()

    def draw_polygon(self, x_center: int, y_center: int, radius: int, sides: int, color_name: str, 
                    rotation: float = 0, fill: bool = False, burnout: Optional[int] = None):
        """Draw a regular polygon."""
        debug(f"Drawing polygon: center({x_center}, {y_center}), radius={radius}, sides={sides}",
            Level.DEBUG, Component.DRAWING)
            
        color = self._get_color(color_name)
        points = polygon_vertices(x_center, y_center, radius, sides, rotation)
        
        # Track all points for burnout
        all_points = set()
        
        # Draw outline
        for i in range(len(points)):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % len(points)]
            
            dx = abs(x1 - x0)
            dy = -abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx + dy
            
            while True:
                if 0 <= x0 < self.matrix.width and 0 <= y0 < self.matrix.height:
                    self._draw_to_buffers(x0, y0, color[0], color[1], color[2])
                    all_points.add((x0, y0))
                if x0 == x1 and y0 == y1:
                    break
                e2 = 2 * err
                if e2 >= dy:
                    err += dy
                    x0 += sx
                if e2 <= dx:
                    err += dx
                    y0 += sy
        
        # Fill if requested
        if fill:
            # Find polygon bounds
            min_x = max(0, min(p[0] for p in points))
            max_x = min(self.matrix.width - 1, max(p[0] for p in points))
            min_y = max(0, min(p[1] for p in points))
            max_y = min(self.matrix.height - 1, max(p[1] for p in points))
            
            # Scan line algorithm
            for y in range(min_y, max_y + 1):
                intersections = []
                
                # Find intersections with edges
                for i in range(len(points)):
                    x0, y0 = points[i]
                    x1, y1 = points[(i + 1) % len(points)]
                    
                    if (y0 < y and y1 >= y) or (y1 < y and y0 >= y):
                        x = int(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
                        intersections.append(x)
                
                # Sort intersections
                intersections.sort()
                
                # Fill between intersection pairs
                for i in range(0, len(intersections), 2):
                    if i + 1 < len(intersections):
                        start = max(min_x, min(intersections[i], intersections[i + 1]))
                        end = min(max_x, max(intersections[i], intersections[i + 1]))
                        
                        for x in range(int(start), int(end) + 1):
                            self._draw_to_buffers(x, y, color[0], color[1], color[2])
                            all_points.add((x, y))
        
        if burnout is not None:
            self.burnout_manager.add_object(
                ShapeType.POLYGON,
                (x_center, y_center, radius),
                list(points),
                burnout
            )
            
        self._maybe_swap_buffer()

    def draw_text(self, x: int, y: int, text: str, font_name: str, font_size: int, 
                 color: str, effect: TextEffect = TextEffect.NORMAL,
                 modifier: Optional[EffectModifier] = None) -> None:
        """
        Draw text on the LED matrix.
        
        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to display
            font_name: Name of font to use
            font_size: Font size in pixels
            color: Color name or specification
            effect: Text effect to apply (default: NORMAL)
            modifier: Effect modifier (optional)
        """
        self.text_renderer.render_text(x, y, text, font_name, font_size, color, effect, modifier)
        self._maybe_swap_buffer()

    def clear_text(self, x: int, y: int) -> None:
        """
        Clear text at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.text_renderer.clear_text(x, y)
        self._maybe_swap_buffer()

    # Utility Methods
    def clear(self):
        """Clear both buffers."""
        self.drawing_buffer.fill(0)  # Clear drawing buffer
        self.offscreen_canvas.Fill(0, 0, 0)
        self.burnout_manager.clear_all()  # Clear burnout queue
        self._maybe_swap_buffer()

    def rest(self, duration):
        """Rest for a duration while still checking burnouts."""
        debug(f"Resting for {duration} seconds..0", Level.DEBUG, Component.COMMAND)
        end_time = time.time() + duration
        while time.time() < end_time:
            """Rest for a duration."""
            debug(f"Resting for {duration} seconds", Level.DEBUG, Component.COMMAND)
            time.sleep(duration)
    # Sprite Management Methods
    def show_sprite(self, name: str, x: float, y: float):
        """Show a sprite at the specified position."""
        sprite = self.sprite_manager.get_sprite(name)
        if sprite:
            debug(f"Sprite {name} now occupies cells: {sprite.occupied_cells}", Level.DEBUG, Component.SPRITE)
            # Mark old position's cells dirty
            if sprite.visible:
                old_cells = get_grid_cells(int(sprite.x), int(sprite.y), sprite.width, sprite.height)
                self._mark_cells_dirty(old_cells)
                debug(f"Marking old cells dirty for sprite {name}: {old_cells}", Level.DEBUG, Component.SPRITE)
            
            # Update position and visibility
            sprite.x = x
            sprite.y = y
            sprite.visible = True
            
            # Update occupied cells
            new_cells = set(get_grid_cells(int(x), int(y), sprite.width, sprite.height))
            sprite.occupied_cells = new_cells
            debug(f"Sprite {name} now occupies cells: {new_cells}", Level.DEBUG, Component.SPRITE)

            # Copy sprite to display buffer and update
            self.copy_sprite_to_buffer(sprite, self.offscreen_canvas)
            if not self.frame_mode:
                self.matrix.SwapOnVSync(self.offscreen_canvas)

    def hide_sprite(self, name: str):
        """Hide a sprite."""
        sprite = self.sprite_manager.get_sprite(name)
        if sprite and sprite.visible:
            # Mark cells dirty where sprite was
            cells = get_grid_cells(int(sprite.x), int(sprite.y), 
                                sprite.width, sprite.height)
            self._mark_cells_dirty(cells)
            sprite.visible = False
            sprite.occupied_cells.clear()

            if not self.frame_mode:
                self._restore_dirty_cells()
                self.refresh_display()

    def move_sprite(self, name: str, x: float, y: float):
        """Move a sprite to a new position."""
        sprite = self.sprite_manager.get_sprite(name)
        if sprite and sprite.visible:
            # Debug old position details
            old_x, old_y = int(sprite.x), int(sprite.y)
            debug(f"Moving sprite {name} from ({old_x},{old_y}) to ({int(x)},{int(y)})", 
                Level.DEBUG, Component.SPRITE)
            debug(f"Old sprite boundaries: x({old_x} to {old_x+sprite.width}) y({old_y} to {old_y+sprite.height})", 
                Level.DEBUG, Component.SPRITE)

            # Get and log old cells
            old_cells = get_grid_cells(old_x, old_y, sprite.width, sprite.height)
            debug(f"Old grid cells coverage: {old_cells}", Level.DEBUG, Component.SPRITE)

            # Mark old cells dirty
            self._mark_cells_dirty(old_cells)

            # Update position
            sprite.x = x
            sprite.y = y
            
            # Debug new position details
            new_x, new_y = int(x), int(y)
            debug(f"New sprite boundaries: x({new_x} to {new_x+sprite.width}) y({new_y} to {new_y+sprite.height})", 
                Level.DEBUG, Component.SPRITE)

            # Update occupied cells
            new_cells = set(get_grid_cells(new_x, new_y, sprite.width, sprite.height))
            sprite.occupied_cells = new_cells
            debug(f"New grid cells coverage: {new_cells}", Level.DEBUG, Component.SPRITE)

            if not self.frame_mode:
                self.begin_frame()
                self._restore_dirty_cells()  # Restore background
                self.copy_sprite_to_buffer(sprite, self.offscreen_canvas)  # Draw sprite
                self.end_frame()  # Single frame update

    def refresh_display(self):
        """Refresh the display with all visible sprites in z-order."""
        # Get all visible sprites from the sprite manager in z-order
        for sprite_name in self.sprite_manager.z_order:
            sprite = self.sprite_manager.sprites[sprite_name]
            if sprite.visible:
                self.copy_sprite_to_buffer(sprite, self.offscreen_canvas)
        
        if not self.frame_mode:
            self.matrix.SwapOnVSync(self.offscreen_canvas)

    def copy_sprite_to_buffer(self, sprite: MatrixSprite, dest_buffer):
        """Copy sprite pixels to the destination buffer, skipping transparent pixels."""
        debug(f"Copying sprite '{sprite.name}' to buffer", Level.TRACE, Component.SPRITE)
        
        x, y = round(sprite.x), round(sprite.y)
        
        start_x = max(0, x)
        start_y = max(0, y)
        end_x = min(self.matrix.width, x + sprite.width)
        end_y = min(self.matrix.height, y + sprite.height)
        
        sprite_start_x = max(0, -x)
        sprite_start_y = max(0, -y)
        
        # Initialize counters
        pixels_copied = 0
        pixels_skipped = 0
        
        # Copy non-transparent pixels
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
                    
                r = sprite.buffer[sy][sx][0]
                g = sprite.buffer[sy][sx][1]
                b = sprite.buffer[sy][sx][2]
                
                if (r, g, b) != TRANSPARENT_COLOR:
                    dest_buffer.SetPixel(dx, dy, r, g, b)
                    pixels_copied += 1
                else:
                    pixels_skipped += 1
    
        debug(f"Sprite copy complete: {pixels_copied} pixels copied, {pixels_skipped} transparent pixels skipped",
            Level.TRACE, Component.SPRITE)

    def clear_sprite_position(self, sprite: MatrixSprite, dest_buffer):
        """Clear the sprite's current position on the buffer with transparent color."""
        x, y = round(sprite.x), round(sprite.y)
        
        start_x = max(0, x)
        start_y = max(0, y)
        end_x = min(self.matrix.width, x + sprite.width)
        end_y = min(self.matrix.height, y + sprite.height)
        
        # Use true black (0,0,0) for clearing, not transparent color
        for dy in range(start_y, end_y):
            for dx in range(start_x, end_x):
                dest_buffer.SetPixel(dx, dy, 0, 0, 0)

        debug(f"Cleared sprite position with black: ({start_x},{start_y}) to ({end_x},{end_y})", 
            Level.TRACE, Component.SPRITE)

    def draw_to_sprite(self, name: str, command: str, *args):
        """Execute a drawing command on a sprite."""
        debug(f"Drawing to sprite {name}: {command} {args}", Level.DEBUG, Component.SPRITE)
        
        sprite = self.sprite_manager.get_sprite(name)
        if not sprite:
            debug(f"Error: Sprite '{name}' not found", Level.ERROR, Component.SPRITE)
            return

        try:
            if command == 'draw_circle':
                # Extract parameters
                x, y, radius, color_spec = args[0:4]
                fill = args[4] if len(args) > 4 else False
                
                # Handle color conversion - can be string or int
                if isinstance(color_spec, (str, int)):
                    color_str = str(color_spec)
                    color_base, intensity = parse_color_spec(color_str)
                    color = get_color_rgb(color_base, intensity)
                else:
                    color = color_spec
                
                debug(f"Circle params: center({x},{y}) radius:{radius} color:{color} fill:{fill}",
                    Level.DEBUG, Component.SPRITE)
                sprite.draw_circle(int(x), int(y), int(radius), color, fill)
                
            elif command == 'draw_rectangle':
                # Extract parameters
                x, y, width, height, color_spec = args[0:5]
                fill = args[5] if len(args) > 5 else False
                
                # Handle color conversion - can be string or int
                if isinstance(color_spec, (str, int)):
                    color_str = str(color_spec)
                    color_base, intensity = parse_color_spec(color_str)
                    color = get_color_rgb(color_base, intensity)
                else:
                    color = color_spec
                
                debug(f"Rectangle params: pos({x},{y}) size({width}x{height}) color:{color} fill:{fill}",
                    Level.DEBUG, Component.SPRITE)
                sprite.draw_rectangle(int(x), int(y), int(width), int(height), color, fill)
                
            elif command == 'plot':
                # Extract parameters
                x, y, color_spec = args[0:3]
                
                # Handle color conversion - can be string or int
                if isinstance(color_spec, (str, int)):
                    color_str = str(color_spec)
                    color_base, intensity = parse_color_spec(color_str)
                    color = get_color_rgb(color_base, intensity)
                else:
                    color = color_spec
                    
                debug(f"Plot params: pos({x},{y}) color:{color}",
                    Level.DEBUG, Component.SPRITE)
                sprite.plot(int(x), int(y), color)
                
            elif command == 'draw_line':
                # Extract parameters
                x1, y1, x2, y2, color_spec = args[0:5]
                
                # Handle color conversion - can be string or int
                if isinstance(color_spec, (str, int)):
                    color_str = str(color_spec)
                    color_base, intensity = parse_color_spec(color_str)
                    color = get_color_rgb(color_base, intensity)
                else:
                    color = color_spec
                    
                debug(f"Line params: from({x1},{y1}) to({x2},{y2}) color:{color}",
                    Level.DEBUG, Component.SPRITE)
                sprite.draw_line(int(x1), int(y1), int(x2), int(y2), color)

            elif command == 'draw_polygon':
                # Extract parameters
                x, y, radius, sides, color_spec = args[0:5]
                rotation = float(args[5]) if len(args) > 5 else 0
                fill = args[6] if len(args) > 6 else False
                
                # Handle color conversion
                if isinstance(color_spec, (str, int)):
                    color_str = str(color_spec)
                    color_base, intensity = parse_color_spec(color_str)
                    color = get_color_rgb(color_base, intensity)
                else:
                    color = color_spec
                    
                debug(f"Polygon params: center({x},{y}) radius:{radius} sides:{sides} color:{color} rotation:{rotation} fill:{fill}",
                    Level.DEBUG, Component.SPRITE)
                sprite.draw_polygon(int(x), int(y), int(radius), int(sides), color, rotation, fill)
                
            elif command == 'clear':
                sprite.clear()
                
            debug(f"Successfully executed {command} on sprite {name}",
                Level.DEBUG, Component.SPRITE)
                
        except Exception as e:
            debug(f"Error executing sprite drawing command: {e}",
                Level.ERROR, Component.SPRITE)
            debug(f"Args received: {args}", Level.ERROR, Component.SPRITE)

    def execute_command(self, command: str) -> None:
        """Execute a single command."""
        debug(f"Executing command: {command}", Level.INFO, Component.COMMAND)
        if not command.strip():
            debug("Empty command received, ignoring", Level.WARNING, Component.COMMAND)
            return
            
        from .commands import CommandExecutor
        if not hasattr(self, 'command_executor'):
            debug("Creating new CommandExecutor instance", Level.DEBUG, Component.COMMAND)
            self.command_executor = CommandExecutor(self)
            
        try:
            self.command_executor.execute_command(command)
            debug("Command executed successfully", Level.DEBUG, Component.COMMAND)
        except Exception as e:
            debug(f"Command execution failed: {str(e)}", Level.ERROR, Component.COMMAND)
            raise

    #Buffer Management
    def _draw_to_buffers(self, x: int, y: int, r: int, g: int, b: int):
        """Write pixel to both drawing buffer and display buffer."""
        if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
        #    # Store values in drawing buffer
             self.drawing_buffer[y, x] = [r, g, b]
        #    # Send directly to display (already 8-bit)
             self.offscreen_canvas.SetPixel(x, y, r, g, b)
        return

    #Grid Management
    def _mark_cells_dirty(self, cells: List[Tuple[int, int]]):
        """Mark grid cells as dirty"""
        for gx, gy in cells:
            if 0 <= gx < self.grid_dirty.shape[1] and 0 <= gy < self.grid_dirty.shape[0]:
                self.grid_dirty[gy, gx] = True

    def _restore_cell(self, grid_x: int, grid_y: int):
        """Restore a single grid cell from drawing buffer"""
        debug(f"Starting restoration of cell ({grid_x}, {grid_y})", Level.DEBUG, Component.SPRITE)
        
        start_x = grid_x * GRID_SIZE
        start_y = grid_y * GRID_SIZE
        end_x = min(start_x + GRID_SIZE, self.matrix.width)
        end_y = min(start_y + GRID_SIZE, self.matrix.height)
        
        debug(f"Restoring pixel region: ({start_x},{start_y}) to ({end_x-1},{end_y-1})", 
            Level.DEBUG, Component.SPRITE)
        
        pixels_restored = 0
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                color = self.drawing_buffer[y, x]
                self.offscreen_canvas.SetPixel(x, y, int(color[0]), int(color[1]), int(color[2]))
                pixels_restored += 1

        debug(f"Restored {pixels_restored} pixels in cell ({grid_x}, {grid_y})", 
            Level.DEBUG, Component.SPRITE)
        
    def _restore_dirty_cells(self):
        """Restore all dirty grid cells from drawing buffer"""
        # Get indices of dirty cells
        dirty_yx = np.where(self.grid_dirty)
        debug(f"Found {len(dirty_yx[0])} dirty cells to restore", Level.DEBUG, Component.SPRITE)
        
        # Process each dirty cell
        for grid_y, grid_x in zip(dirty_yx[0], dirty_yx[1]):
            debug(f"Processing dirty cell ({grid_x}, {grid_y})", Level.DEBUG, Component.SPRITE)
            
            # Restore from drawing buffer
            self._restore_cell(grid_x, grid_y)
            self.grid_dirty[grid_y, grid_x] = False  # Clear dirty flag

            # Get overlapping sprites for this cell
            cell_sprites = self.sprite_manager.get_overlapping_sprites([(grid_x, grid_y)])
            if cell_sprites:
                debug(f"Found {len(cell_sprites)} sprites overlapping cell ({grid_x}, {grid_y})", 
                    Level.DEBUG, Component.SPRITE)
                # Draw sprites in z-order
                for sprite in cell_sprites:
                    debug(f"Redrawing sprite {sprite.name} in z-order", Level.DEBUG, Component.SPRITE)
                    self.copy_sprite_to_buffer(sprite, self.offscreen_canvas)

        # Update display if any cells were restored
        if len(dirty_yx[0]) > 0:
            debug(f"Restored {len(dirty_yx[0])} cells, updating display", Level.DEBUG, Component.SPRITE)

    def cleanup(self):
        """Clean up resources."""
        debug("Starting RGB_Api cleanup", Level.INFO, Component.SYSTEM)
        self.burnout_manager.stop()
        self.clear()
        debug("RGB_Api cleanup complete", Level.INFO, Component.SYSTEM)


