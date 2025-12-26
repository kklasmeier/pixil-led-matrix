# File: rgb_matrix_lib/sprite.py

import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from .debug import debug, Level, Component
from .utils import TRANSPARENT_COLOR, polygon_vertices, is_transparent, polygon_vertices


class MatrixSprite:
    def __init__(self, width: int, height: int, name: str):
        """Initialize a sprite with given dimensions."""
        debug(f"Creating sprite '{name}' ({width}x{height})", Level.INFO, Component.SPRITE)
        
        self.width = width
        self.height = height
        self.name = name
        self.buffer = np.zeros((height, width, 3), dtype=np.uint8)
        self.intensity_buffer = np.full((height, width), 100, dtype=np.uint8)  # Default intensity remains 100
        self.x = 0
        self.y = 0
        self.visible = False
        self.z_index = 0
        self.occupied_cells = set()

        # Initialize with transparent color
        self.clear()
        
        debug(f"Sprite buffer created and initialized transparent", Level.DEBUG, Component.SPRITE)

    def plot(self, x: int, y: int, color: Union[str, int, Tuple[int, int, int]], intensity: int = 100):
        """Plot a single pixel in the sprite buffer with intensity."""
        debug(f"Plotting on sprite '{self.name}' at ({x},{y}) with color {color} at {intensity}%", 
              Level.TRACE, Component.SPRITE)
        intensity = max(0, min(100, intensity))  # Changed from min(99, ...) to min(100, ...)
        from .utils import get_color_rgb
        rgb_color = get_color_rgb(color, 100)  # Store full brightness (intensity applied later)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = rgb_color
            self.intensity_buffer[y, x] = intensity  # Store intensity separately
            debug(f"Plotted pixel at ({x},{y}) with RGB {rgb_color} and intensity {intensity}", 
                  Level.TRACE, Component.SPRITE)
        else:
            debug(f"Plot coordinates ({x},{y}) out of sprite bounds ({self.width}x{self.height})", 
                  Level.WARNING, Component.SPRITE)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: Union[str, int, Tuple[int, int, int]], 
                  intensity: int = 100):
        """Draw a line in the sprite buffer with intensity."""
        debug(f"Drawing line on sprite '{self.name}' from ({x0},{y0}) to ({x1},{y1}) with color {color} at {intensity}%", 
              Level.DEBUG, Component.SPRITE)
        intensity = max(0, min(100, intensity))  # Changed from min(99, ...) to min(100, ...)
        from .utils import get_color_rgb
        rgb_color = get_color_rgb(color, 100)  # Full brightness
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        points_drawn = 0
        
        while True:
            if 0 <= x0 < self.width and 0 <= y0 < self.height:
                self.buffer[y0, x0] = rgb_color
                self.intensity_buffer[y0, x0] = intensity
                points_drawn += 1
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
        
        debug(f"Line complete on sprite '{self.name}', {points_drawn} points drawn", 
              Level.TRACE, Component.SPRITE)

    def draw_rectangle(self, x: int, y: int, width: int, height: int, color: Union[str, int, Tuple[int, int, int]], 
                       intensity: int = 100, fill: bool = False):
        """Draw a rectangle in the sprite buffer with intensity."""
        debug(f"Drawing {'filled' if fill else 'outline'} rectangle on sprite '{self.name}' at ({x},{y}) "
              f"size ({width}x{height}) with color {color} at {intensity}%", 
              Level.DEBUG, Component.SPRITE)
        intensity = max(0, min(100, intensity))  # Changed from min(99, ...) to min(100, ...)
        from .utils import get_color_rgb
        rgb_color = get_color_rgb(color, 100)  # Full brightness
        points_drawn = 0
        
        if fill:
            for i in range(max(0, x), min(x + width, self.width)):
                for j in range(max(0, y), min(y + height, self.height)):
                    self.buffer[j, i] = rgb_color
                    self.intensity_buffer[j, i] = intensity
                    points_drawn += 1
        else:
            # Top edge
            for i in range(max(0, x), min(x + width, self.width)):
                if 0 <= y < self.height:
                    self.buffer[y, i] = rgb_color
                    self.intensity_buffer[y, i] = intensity
                    points_drawn += 1
                if 0 <= y + height - 1 < self.height:
                    self.buffer[y + height - 1, i] = rgb_color
                    self.intensity_buffer[y + height - 1, i] = intensity
                    points_drawn += 1
            # Left and right edges
            for j in range(max(0, y), min(y + height, self.height)):
                if 0 <= x < self.width:
                    self.buffer[j, x] = rgb_color
                    self.intensity_buffer[j, x] = intensity
                    points_drawn += 1
                if 0 <= x + width - 1 < self.width:
                    self.buffer[j, x + width - 1] = rgb_color
                    self.intensity_buffer[j, x + width - 1] = intensity
                    points_drawn += 1
        
        debug(f"Rectangle complete on sprite '{self.name}', {points_drawn} points drawn", 
              Level.TRACE, Component.SPRITE)

    def draw_circle(self, x_center: int, y_center: int, radius: int, color: Union[str, int, Tuple[int, int, int]], 
                    intensity: int = 100, fill: bool = False):
        """Draw a circle in the sprite buffer with intensity."""
        debug(f"Drawing {'filled' if fill else 'outline'} circle on sprite '{self.name}' at ({x_center},{y_center}) "
              f"radius {radius} with color {color} at {intensity}%", 
              Level.DEBUG, Component.SPRITE)
        intensity = max(0, min(100, intensity))  # Changed from min(99, ...) to min(100, ...)
        from .utils import get_color_rgb
        rgb_color = get_color_rgb(color, 100)  # Full brightness
        points_drawn = 0
        
        def plot_circle_points(x: int, y: int):
            nonlocal points_drawn
            points = [
                (x, y), (-x, y), (x, -y), (-x, -y),
                (y, x), (-y, x), (y, -x), (-y, -x)
            ]
            for dx, dy in points:
                px, py = x_center + dx, y_center + dy
                if 0 <= px < self.width and 0 <= py < self.height:
                    self.buffer[py, px] = rgb_color
                    self.intensity_buffer[py, px] = intensity
                    points_drawn += 1

        def draw_line(x0: int, y0: int, x1: int):
            nonlocal points_drawn
            if 0 <= y0 < self.height:
                for x in range(max(0, x0), min(x1 + 1, self.width)):
                    self.buffer[y0, x] = rgb_color
                    self.intensity_buffer[y0, x] = intensity
                    points_drawn += 1

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
        
        debug(f"Circle complete on sprite '{self.name}', {points_drawn} points drawn", 
              Level.TRACE, Component.SPRITE)

    def draw_polygon(self, x_center: int, y_center: int, radius: int, sides: int, 
                     color: Union[str, int, Tuple[int, int, int]], intensity: int = 100, rotation: float = 0, 
                     fill: bool = False):
        """Draw a regular polygon in the sprite buffer with intensity."""
        debug(f"Drawing {'filled' if fill else 'outline'} polygon on sprite '{self.name}' at ({x_center},{y_center}) "
              f"radius {radius}, sides {sides}, rotation {rotation} with color {color} at {intensity}%", 
              Level.DEBUG, Component.SPRITE)
        intensity = max(0, min(100, intensity))  # Changed from min(99, ...) to min(100, ...)
        from .utils import get_color_rgb
        rgb_color = get_color_rgb(color, 100)  # Full brightness
        points = polygon_vertices(x_center, y_center, radius, sides, rotation)
        points_drawn = 0
        
        # Draw outline
        for i in range(len(points)):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % len(points)]
            dx = abs(x1 - x0)
            dy = -abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx + dy
            cx, cy = x0, y0
            
            while True:
                if 0 <= cx < self.width and 0 <= cy < self.height:
                    self.buffer[cy, cx] = rgb_color
                    self.intensity_buffer[cy, cx] = intensity
                    points_drawn += 1
                if cx == x1 and cy == y1:
                    break
                e2 = 2 * err
                if e2 >= dy:
                    err += dy
                    cx += sx
                if e2 <= dx:
                    err += dx
                    cy += sy
        
        # Fill if requested
        if fill:
            min_x = max(0, min(p[0] for p in points))
            max_x = min(self.width - 1, max(p[0] for p in points))
            min_y = max(0, min(p[1] for p in points))
            max_y = min(self.height - 1, max(p[1] for p in points))
            for y in range(min_y, max_y + 1):
                intersections = []
                for i in range(len(points)):
                    x0, y0 = points[i]
                    x1, y1 = points[(i + 1) % len(points)]
                    if (y0 < y and y1 >= y) or (y1 < y and y0 >= y):
                        x = int(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
                        intersections.append(x)
                intersections.sort()
                for i in range(0, len(intersections), 2):
                    if i + 1 < len(intersections):
                        start = max(min_x, min(intersections[i], intersections[i + 1]))
                        end = min(max_x, max(intersections[i], intersections[i + 1]))
                        for x in range(int(start), int(end) + 1):
                            if 0 <= x < self.width and 0 <= y < self.height:
                                self.buffer[y, x] = rgb_color
                                self.intensity_buffer[y, x] = intensity
                                points_drawn += 1
        
        debug(f"Polygon complete on sprite '{self.name}', {points_drawn} points drawn", 
              Level.TRACE, Component.SPRITE)

    def draw_ellipse(self, x_center: int, y_center: int, x_radius: int, y_radius: int, 
                    color: Union[str, int, Tuple[int, int, int]], intensity: int = 100, 
                    fill: bool = False, rotation: float = 0):
        """Draw an ellipse in the sprite buffer with intensity and optional rotation."""
        debug(f"Drawing {'filled' if fill else 'outline'} ellipse on sprite '{self.name}' "
            f"at ({x_center},{y_center}) radii ({x_radius},{y_radius}), rotation {rotation} "
            f"with color {color} at {intensity}%", 
            Level.DEBUG, Component.SPRITE)
        
        intensity = max(0, min(100, intensity))
        from .utils import get_color_rgb
        rgb_color = get_color_rgb(color, 100)  # Full brightness
        points_drawn = 0
        
        # Pre-compute sin/cos for rotation
        import math
        rotation_rad = math.radians(rotation)
        cos_rot = math.cos(rotation_rad)
        sin_rot = math.sin(rotation_rad)
        
        # Helper function to rotate a point around the origin
        def rotate_point(x, y):
            rx = round(x * cos_rot - y * sin_rot)
            ry = round(x * sin_rot + y * cos_rot)
            return rx, ry
        
        # Helper function to plot a pixel if it's within bounds
        def plot_pixel(x, y):
            nonlocal points_drawn
            if 0 <= x < self.width and 0 <= y < self.height:
                self.buffer[y, x] = rgb_color
                self.intensity_buffer[y, x] = intensity
                points_drawn += 1
        
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
            
            return
        
        # For filled ellipses, use a pixel-by-pixel approach
        if fill:
            # Determine a safe bounding box that will contain the rotated ellipse
            max_radius = max(x_radius, y_radius)
            min_x = max(0, x_center - max_radius - 1)
            max_x = min(self.width - 1, x_center + max_radius + 1)
            min_y = max(0, y_center - max_radius - 1)
            max_y = min(self.height - 1, y_center + max_radius + 1)
            
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
        
        debug(f"Ellipse complete on sprite '{self.name}', {points_drawn} points drawn", 
            Level.TRACE, Component.SPRITE)

    def draw_arc(self, x1: int, y1: int, x2: int, y2: int, arc_height: float, 
                    color: Union[str, int, Tuple[int, int, int]], intensity: int = 100, fill: bool = False):
            """
            Draw an arc in the sprite buffer from (x1, y1) to (x2, y2) with specified arc height.
            
            Args:
                x1, y1: Start point of the arc
                x2, y2: End point of the arc
                arc_height: Perpendicular distance from chord to arc peak (in pixels)
                        Positive = arc curves to port side (left when traveling from start to end)
                        Negative = arc curves to starboard side (right when traveling from start to end)
                        Zero = straight line
                color: Color name, spectral value, or RGB tuple
                intensity: Brightness 0-100
                fill: If True, fills the curved segment area
            """
            import math
            
            debug(f"Drawing arc on sprite '{self.name}' from ({x1},{y1}) to ({x2},{y2}) "
                f"with height {arc_height} and color {color} at {intensity}%", 
                Level.DEBUG, Component.SPRITE)
            
            intensity = max(0, min(100, intensity))
            from .utils import get_color_rgb
            rgb_color = get_color_rgb(color, 100)  # Full brightness
            points_drawn = 0
            
            # Special case: arc_height = 0 means straight line
            if arc_height == 0:
                self.draw_line(x1, y1, x2, y2, color, intensity)
                return
            
            # Calculate chord length and midpoint
            chord_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            if chord_length == 0:
                # Degenerate case: start and end points are the same
                self.plot(x1, y1, color, intensity)
                return
            
            # Midpoint of chord
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # Vector from start to end (chord direction)
            chord_dx = x2 - x1
            chord_dy = y2 - y1
            
            # Perpendicular vector (normalized) - rotated 90 degrees counterclockwise
            perp_dx = -chord_dy / chord_length
            perp_dy = chord_dx / chord_length
            
            # Calculate radius and center using the sagitta (arc height) formula
            half_chord = chord_length / 2
            radius = (arc_height**2 + half_chord**2) / (2 * abs(arc_height))
            
            # Distance from chord midpoint to circle center
            center_dist = math.sqrt(radius**2 - half_chord**2)
            
            # Adjust sign based on arc_height direction
            if arc_height < 0:
                center_dist = -center_dist
            
            # Circle center is perpendicular to chord midpoint
            center_x = mid_x + perp_dx * center_dist
            center_y = mid_y + perp_dy * center_dist
            
            # Calculate start and end angles
            start_angle = math.atan2(y1 - center_y, x1 - center_x)
            end_angle = math.atan2(y2 - center_y, x2 - center_x)
            
            # Determine sweep direction and angle range
            angle_diff = end_angle - start_angle
            
            # Normalize angle difference to [-π, π]
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # If arc_height is positive, we want counterclockwise arc
            # If arc_height is negative, we want clockwise arc
            if arc_height > 0 and angle_diff < 0:
                angle_diff += 2 * math.pi
            elif arc_height < 0 and angle_diff > 0:
                angle_diff -= 2 * math.pi
            
            # Calculate number of steps based on arc length
            arc_length = abs(radius * angle_diff)
            num_steps = max(int(arc_length) + 1, 2)
            
            # Draw the arc outline
            for i in range(num_steps + 1):
                t = i / num_steps
                angle = start_angle + t * angle_diff
                
                x = int(center_x + radius * math.cos(angle))
                y = int(center_y + radius * math.sin(angle))
                
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.buffer[y, x] = rgb_color
                    self.intensity_buffer[y, x] = intensity
                    points_drawn += 1
            
            # Fill the arc segment if requested
            if fill:
                # Get bounding box
                min_x = max(0, int(min(x1, x2, center_x - radius)) - 1)
                max_x = min(self.width - 1, int(max(x1, x2, center_x + radius)) + 1)
                min_y = max(0, int(min(y1, y2, center_y - radius)) - 1)
                max_y = min(self.height - 1, int(max(y1, y2, center_y + radius)) + 1)
                
                # For each scanline, find if point is in the segment
                for y in range(min_y, max_y + 1):
                    for x in range(min_x, max_x + 1):
                        dx = x - center_x
                        dy = y - center_y
                        dist = math.sqrt(dx**2 + dy**2)
                        
                        if dist <= radius:
                            # Point is inside circle, check if it's in our arc segment
                            point_angle = math.atan2(dy, dx)
                            
                            # Normalize to [0, 2π]
                            if point_angle < 0:
                                point_angle += 2 * math.pi
                            test_start = start_angle
                            if test_start < 0:
                                test_start += 2 * math.pi
                            test_end = end_angle
                            if test_end < 0:
                                test_end += 2 * math.pi
                            
                            # Check if point is in arc range
                            in_arc = False
                            if angle_diff > 0:
                                # Counterclockwise arc
                                if test_start <= test_end:
                                    in_arc = test_start <= point_angle <= test_end
                                else:
                                    in_arc = point_angle >= test_start or point_angle <= test_end
                            else:
                                # Clockwise arc
                                if test_start >= test_end:
                                    in_arc = test_end <= point_angle <= test_start
                                else:
                                    in_arc = point_angle <= test_start or point_angle >= test_end
                            
                            if in_arc:
                                # Also check that point is on the correct side of the chord
                                to_mid_x = mid_x - x
                                to_mid_y = mid_y - y
                                
                                # Check if on same side as center
                                cross1 = perp_dx * to_mid_y - perp_dy * to_mid_x
                                cross2 = perp_dx * (center_y - mid_y) - perp_dy * (center_x - mid_x)
                                
                                if cross1 * cross2 >= 0:
                                    self.buffer[y, x] = rgb_color
                                    self.intensity_buffer[y, x] = intensity
                                    points_drawn += 1
            
            debug(f"Arc complete on sprite '{self.name}', {points_drawn} points drawn", 
                Level.TRACE, Component.SPRITE)

    def clear(self):
        """Clear sprite buffer with transparent color."""
        self.buffer[:, :] = TRANSPARENT_COLOR
        self.intensity_buffer[:, :] = 100  # Reset intensity to default
        debug(f"Sprite '{self.name}' cleared with transparent color", Level.DEBUG, Component.SPRITE)
                
class SpriteManager:
    def __init__(self):
        """Initialize the sprite manager."""
        debug("Initializing SpriteManager", Level.INFO, Component.SPRITE)
        # Change to nested dictionary: { sprite_name: { instance_id: MatrixSprite } }
        self.sprites: Dict[str, Dict[int, MatrixSprite]] = {}
        # Update z_order to track (name, instance_id) tuples
        self.z_order: List[Tuple[str, int]] = []  # Track sprites in z-order

    def dispose_all_sprites(self):
        """
        Dispose of all sprites and clear their resources.
        """
        debug("Disposing of all sprites", Level.INFO, Component.SPRITE)
        
        # Get list of all visible sprite instances for cleanup
        visible_sprites = []
        for sprite_name, instances in self.sprites.items():
            for instance_id, sprite in instances.items():
                if sprite.visible:
                    visible_sprites.append(sprite)
        
        # Clear visible sprites from display
        dirty_cells = set()
        for sprite in visible_sprites:
            dirty_cells.update(sprite.occupied_cells)
            sprite.visible = False
            sprite.occupied_cells.clear()
        
        # Clear sprite collections
        self.sprites.clear()
        self.z_order.clear()
        
        debug(f"Disposed of all sprites, {len(dirty_cells)} cells marked dirty", 
            Level.DEBUG, Component.SPRITE)
        
        return list(dirty_cells)  # Return dirty cells for display cleanup
    
    def create_sprite(self, name: str, width: int, height: int) -> MatrixSprite:
        """Create a new sprite template (instance 0)."""
        debug(f"Creating new sprite: {name} ({width}x{height})", Level.INFO, Component.SPRITE)
        if name in self.sprites and 0 in self.sprites[name]:
            debug(f"Sprite '{name}' already exists", Level.ERROR, Component.SPRITE)
            raise ValueError(f"Sprite '{name}' already exists")
            
        # Create the sprite instance
        sprite = MatrixSprite(width, height, name)
        
        # Initialize the nested dictionary structure if needed
        if name not in self.sprites:
            self.sprites[name] = {}
        
        # Store as instance 0 (the template)
        self.sprites[name][0] = sprite
        self.z_order.append((name, 0))

        return sprite
    
    def create_sprite_instance(self, name: str, instance_id: int) -> Optional[MatrixSprite]:
        """Create a new instance of an existing sprite template."""
        debug(f"Creating instance {instance_id} of sprite '{name}'", Level.INFO, Component.SPRITE)
        
        # Check if template exists
        if name not in self.sprites or 0 not in self.sprites[name]:
            debug(f"Sprite template '{name}' not found", Level.ERROR, Component.SPRITE)
            return None
        
        # Check if instance already exists
        if instance_id in self.sprites[name]:
            debug(f"Instance {instance_id} of sprite '{name}' already exists", Level.WARNING, Component.SPRITE)
            return self.sprites[name][instance_id]
        
        # Create a new sprite based on the template
        template = self.sprites[name][0]
        instance = MatrixSprite(template.width, template.height, template.name)
        
        # Copy the visual data from template to instance
        instance.buffer = template.buffer.copy()
        instance.intensity_buffer = template.intensity_buffer.copy()
        
        # Store the instance and update z-order
        self.sprites[name][instance_id] = instance
        self.z_order.append((name, instance_id))
        
        debug(f"Created instance {instance_id} of sprite '{name}'", Level.DEBUG, Component.SPRITE)
        return instance

    def get_overlapping_sprites(self, cells: List[Tuple[int, int]]) -> List[MatrixSprite]:
        """Get all visible sprites that overlap given grid cells in z-order."""
        overlapping = []
        cells_set = set(cells)
        
        for name, instance_id in self.z_order:
            if name in self.sprites and instance_id in self.sprites[name]:
                sprite = self.sprites[name][instance_id]
                if sprite.visible and sprite.occupied_cells.intersection(cells_set):
                    overlapping.append(sprite)
                    debug(f"Found overlapping sprite: {name} instance {instance_id}", 
                          Level.DEBUG, Component.SPRITE)
        
        return overlapping
        
    def get_sprite(self, name: str, instance_id: int = 0) -> Optional[MatrixSprite]:
        """Get a specific sprite instance by name and instance ID."""
        if name not in self.sprites or instance_id not in self.sprites[name]:
            # Only log warnings for template sprites (instance 0)
            # For other instances, use TRACE level since they might be created on demand
            if instance_id == 0:
                debug(f"Sprite template '{name}' not found", Level.WARNING, Component.SPRITE)
            else:
                debug(f"Sprite '{name}' instance {instance_id} not found", Level.TRACE, Component.SPRITE)
            return None
        
        debug(f"Retrieved sprite '{name}' instance {instance_id}", Level.TRACE, Component.SPRITE)
        return self.sprites[name][instance_id]
    
    def dispose_sprite_instance(self, name: str, instance_id: int) -> List[Tuple[int, int]]:
        """
        Dispose of a specific sprite instance.
        Returns the dirty cells that need to be refreshed.
        """
        debug(f"Disposing sprite '{name}' instance {instance_id}", Level.INFO, Component.SPRITE)
        
        if name not in self.sprites or instance_id not in self.sprites[name]:
            debug(f"Sprite '{name}' instance {instance_id} not found for disposal", 
                  Level.WARNING, Component.SPRITE)
            return []
        
        sprite = self.sprites[name][instance_id]
        dirty_cells = []
        
        # If visible, mark cells as dirty
        if sprite.visible:
            dirty_cells = list(sprite.occupied_cells)
            sprite.visible = False
            sprite.occupied_cells.clear()
        
        # Remove from z-order and sprites dictionary
        if (name, instance_id) in self.z_order:
            self.z_order.remove((name, instance_id))
        
        del self.sprites[name][instance_id]
        
        # If no instances left, clean up the sprite entry
        if not self.sprites[name]:
            del self.sprites[name]
        
        debug(f"Disposed sprite '{name}' instance {instance_id}, {len(dirty_cells)} cells marked dirty", 
              Level.DEBUG, Component.SPRITE)
        
        return dirty_cells