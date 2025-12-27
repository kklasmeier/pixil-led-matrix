# File: rgb_matrix_lib/sprite.py

import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from .debug import debug, Level, Component
from .utils import TRANSPARENT_COLOR, polygon_vertices, is_transparent


class MatrixSprite:
    """
    Sprite template containing one or more animation cels.
    This is the shared definition - instances reference this template.
    """
    def __init__(self, width: int, height: int, name: str):
        """Initialize a sprite template with given dimensions."""
        debug(f"Creating sprite template '{name}' ({width}x{height})", Level.INFO, Component.SPRITE)
        
        self.width = width
        self.height = height
        self.name = name
        
        # Cel storage - list of (buffer, intensity_buffer) tuples
        # Initialized with one cel (cel 0) for backward compatibility
        self._cels: List[Tuple[np.ndarray, np.ndarray]] = []
        self._add_cel()  # Add default cel 0
        
        # Track which cel is currently being drawn to during definition
        self._active_cel_index = 0
        
        debug(f"Sprite template created with initial cel 0", Level.DEBUG, Component.SPRITE)

    def _add_cel(self) -> int:
        """Add a new cel and return its index."""
        buffer = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        intensity_buffer = np.full((self.height, self.width), 100, dtype=np.uint8)
        # Initialize with transparent color
        buffer[:, :] = TRANSPARENT_COLOR
        self._cels.append((buffer, intensity_buffer))
        return len(self._cels) - 1

    @property
    def cel_count(self) -> int:
        """Return the number of cels in this sprite."""
        return len(self._cels)

    def get_cel_buffer(self, cel_index: int = 0) -> np.ndarray:
        """Get the color buffer for a specific cel."""
        if 0 <= cel_index < len(self._cels):
            return self._cels[cel_index][0]
        raise IndexError(f"Cel index {cel_index} out of range (0-{len(self._cels)-1})")

    def get_cel_intensity(self, cel_index: int = 0) -> np.ndarray:
        """Get the intensity buffer for a specific cel."""
        if 0 <= cel_index < len(self._cels):
            return self._cels[cel_index][1]
        raise IndexError(f"Cel index {cel_index} out of range (0-{len(self._cels)-1})")

    # Backward compatibility properties - access cel 0 as default
    @property
    def buffer(self) -> np.ndarray:
        """Backward compatible access to cel 0's buffer."""
        return self.get_cel_buffer(self._active_cel_index)

    @property
    def intensity_buffer(self) -> np.ndarray:
        """Backward compatible access to cel 0's intensity buffer."""
        return self.get_cel_intensity(self._active_cel_index)

    def set_active_cel(self, cel_index: int):
        """Set which cel drawing commands should target."""
        if 0 <= cel_index < len(self._cels):
            self._active_cel_index = cel_index
            debug(f"Sprite '{self.name}' active cel set to {cel_index}", Level.DEBUG, Component.SPRITE)
        else:
            raise IndexError(f"Cel index {cel_index} out of range (0-{len(self._cels)-1})")

    def ensure_cel_exists(self, cel_index: int):
        """Ensure a cel exists at the given index, creating it if necessary."""
        while len(self._cels) <= cel_index:
            self._add_cel()
            debug(f"Created cel {len(self._cels)-1} for sprite '{self.name}'", Level.DEBUG, Component.SPRITE)

    def plot(self, x: int, y: int, color: Union[str, int, Tuple[int, int, int]], intensity: int = 100):
        """Plot a single pixel in the active cel buffer with intensity."""
        debug(f"Plotting on sprite '{self.name}' cel {self._active_cel_index} at ({x},{y}) with color {color} at {intensity}%", 
              Level.TRACE, Component.SPRITE)
        intensity = max(0, min(100, intensity))
        from .utils import get_color_rgb
        rgb_color = get_color_rgb(color, 100)  # Store full brightness (intensity applied later)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = rgb_color
            self.intensity_buffer[y, x] = intensity
            debug(f"Plotted pixel at ({x},{y}) with RGB {rgb_color} and intensity {intensity}", 
                  Level.TRACE, Component.SPRITE)
        else:
            debug(f"Plot coordinates ({x},{y}) out of sprite bounds ({self.width}x{self.height})", 
                  Level.WARNING, Component.SPRITE)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: Union[str, int, Tuple[int, int, int]], 
                  intensity: int = 100):
        """Draw a line in the active cel buffer with intensity."""
        debug(f"Drawing line on sprite '{self.name}' cel {self._active_cel_index} from ({x0},{y0}) to ({x1},{y1}) with color {color} at {intensity}%", 
              Level.DEBUG, Component.SPRITE)
        intensity = max(0, min(100, intensity))
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
        """Draw a rectangle in the active cel buffer with intensity."""
        debug(f"Drawing {'filled' if fill else 'outline'} rectangle on sprite '{self.name}' cel {self._active_cel_index} at ({x},{y}) "
              f"size ({width}x{height}) with color {color} at {intensity}%", 
              Level.DEBUG, Component.SPRITE)
        intensity = max(0, min(100, intensity))
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
        """Draw a circle in the active cel buffer with intensity."""
        debug(f"Drawing {'filled' if fill else 'outline'} circle on sprite '{self.name}' cel {self._active_cel_index} at ({x_center},{y_center}) "
              f"radius {radius} with color {color} at {intensity}%", 
              Level.DEBUG, Component.SPRITE)
        intensity = max(0, min(100, intensity))
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
        """Draw a regular polygon in the active cel buffer with intensity."""
        debug(f"Drawing {'filled' if fill else 'outline'} polygon on sprite '{self.name}' cel {self._active_cel_index} at ({x_center},{y_center}) "
              f"radius {radius}, sides {sides}, rotation {rotation} with color {color} at {intensity}%", 
              Level.DEBUG, Component.SPRITE)
        intensity = max(0, min(100, intensity))
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
        """Draw an ellipse in the active cel buffer with intensity and optional rotation."""
        debug(f"Drawing {'filled' if fill else 'outline'} ellipse on sprite '{self.name}' cel {self._active_cel_index} "
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
                    d1 += b_squared + dx
                else:
                    y -= 1
                    dy -= 2 * a_squared
                    d1 += b_squared + dx - dy
                
                # Plot points in all four quadrants
                rx, ry = rotate_point(x, y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(-x, y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(x, -y)
                plot_pixel(x_center + rx, y_center + ry)
                
                rx, ry = rotate_point(-x, -y)
                plot_pixel(x_center + rx, y_center + ry)
            
            # Region 2
            d2 = (b_squared * ((x + 0.5) ** 2)) + (a_squared * ((y - 1) ** 2)) - (a_squared * b_squared)
            
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
            Draw an arc in the active cel buffer from (x1, y1) to (x2, y2) with specified arc height.
            
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
            
            debug(f"Drawing arc on sprite '{self.name}' cel {self._active_cel_index} from ({x1},{y1}) to ({x2},{y2}) "
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

    def clear(self, cel_index: Optional[int] = None):
        """Clear sprite buffer(s) with transparent color.
        
        Args:
            cel_index: If specified, clear only that cel. If None, clear all cels.
        """
        if cel_index is not None:
            if 0 <= cel_index < len(self._cels):
                buffer, intensity = self._cels[cel_index]
                buffer[:, :] = TRANSPARENT_COLOR
                intensity[:, :] = 100
                debug(f"Sprite '{self.name}' cel {cel_index} cleared", Level.DEBUG, Component.SPRITE)
        else:
            for i, (buffer, intensity) in enumerate(self._cels):
                buffer[:, :] = TRANSPARENT_COLOR
                intensity[:, :] = 100
            debug(f"Sprite '{self.name}' all cels cleared", Level.DEBUG, Component.SPRITE)


class SpriteInstance:
    """
    Lightweight instance of a sprite on screen.
    References a shared MatrixSprite template and tracks instance-specific state.
    """
    def __init__(self, template: MatrixSprite, x: float = 0, y: float = 0, 
                 z_index: int = 0, current_cel: int = 0):
        self.template = template
        self.x = x
        self.y = y
        self.current_cel = current_cel
        self.visible = False
        self.z_index = z_index
        self.occupied_cells: set = set()
    
    @property
    def width(self) -> int:
        return self.template.width
    
    @property
    def height(self) -> int:
        return self.template.height
    
    @property
    def name(self) -> str:
        return self.template.name
    
    @property
    def buffer(self) -> np.ndarray:
        """Get the color buffer for the current cel."""
        return self.template.get_cel_buffer(self.current_cel)
    
    @property
    def intensity_buffer(self) -> np.ndarray:
        """Get the intensity buffer for the current cel."""
        return self.template.get_cel_intensity(self.current_cel)
    
    @property
    def cel_count(self) -> int:
        """Get the number of cels in the template."""
        return self.template.cel_count
    
    def advance_cel(self) -> int:
        """Advance to the next cel, wrapping around. Returns the new cel index."""
        self.current_cel = (self.current_cel + 1) % self.template.cel_count
        return self.current_cel
    
    def set_cel(self, cel_index: int):
        """Set the current cel to a specific index."""
        if 0 <= cel_index < self.template.cel_count:
            self.current_cel = cel_index
        else:
            raise IndexError(f"Cel index {cel_index} out of range (0-{self.template.cel_count-1})")


class SpriteManager:
    """Manages sprite templates and instances."""
    
    def __init__(self):
        """Initialize the sprite manager."""
        debug("Initializing SpriteManager", Level.INFO, Component.SPRITE)
        
        # Sprite templates: { name: MatrixSprite }
        self.templates: Dict[str, MatrixSprite] = {}
        
        # Sprite instances: { name: { instance_id: SpriteInstance } }
        self.instances: Dict[str, Dict[int, SpriteInstance]] = {}
        
        # Z-order tracking: list of (name, instance_id) tuples
        self.z_order: List[Tuple[str, int]] = []
        
        # Sprite definition state (for building sprites)
        self._defining_sprite: Optional[MatrixSprite] = None
        self._cel_indices_used: set = set()
        self._next_auto_cel_index: int = 0
        self._in_cel_block: bool = False

    # ========== Sprite Definition Methods ==========
    
    def begin_sprite_definition(self, name: str, width: int, height: int) -> MatrixSprite:
        """Begin defining a new sprite template."""
        debug(f"Beginning sprite definition: {name} ({width}x{height})", Level.INFO, Component.SPRITE)
        
        if name in self.templates:
            debug(f"Sprite template '{name}' already exists", Level.ERROR, Component.SPRITE)
            raise ValueError(f"Sprite template '{name}' already exists")
        
        if self._defining_sprite is not None:
            debug(f"Already defining sprite '{self._defining_sprite.name}'", Level.ERROR, Component.SPRITE)
            raise RuntimeError(f"Already defining sprite '{self._defining_sprite.name}'")
        
        # Create new template
        sprite = MatrixSprite(width, height, name)
        self._defining_sprite = sprite
        self._cel_indices_used = {0}  # Cel 0 is created by default
        self._next_auto_cel_index = 1  # Next auto-assigned index
        self._in_cel_block = False
        
        return sprite
    
    def start_cel(self, cel_index: Optional[int] = None) -> int:
        """
        Start defining a new cel within the current sprite definition.
        
        Args:
            cel_index: Explicit cel index, or None for auto-assignment
            
        Returns:
            The cel index being defined
        """
        if self._defining_sprite is None:
            raise RuntimeError("Not currently defining a sprite")
        
        # Determine cel index
        if cel_index is None:
            # Auto-assignment: if this is the first sprite_cel() call and cel 0 
            # exists but hasn't been explicitly used, start at 0
            if self._next_auto_cel_index == 1 and 0 in self._cel_indices_used and not self._in_cel_block:
                # First sprite_cel() call - reuse cel 0
                cel_index = 0
            else:
                cel_index = self._next_auto_cel_index
                self._next_auto_cel_index = cel_index + 1
        else:
            # Update auto index to be at least past this explicit index
            self._next_auto_cel_index = max(self._next_auto_cel_index, cel_index + 1)
        
        # Check for duplicates (but allow redefining cel 0 on first sprite_cel call)
        if cel_index in self._cel_indices_used and cel_index != 0:
            raise ValueError(f"Duplicate cel index: {cel_index}")
        if cel_index == 0 and self._in_cel_block:
            # Already used cel 0 with an explicit sprite_cel() call
            raise ValueError(f"Duplicate cel index: {cel_index}")
        
        # Ensure cel exists in template
        self._defining_sprite.ensure_cel_exists(cel_index)
        self._defining_sprite.set_active_cel(cel_index)
        self._cel_indices_used.add(cel_index)
        self._in_cel_block = True
        
        # If this was auto-assigned and was cel 0, update next auto to 1
        if cel_index == 0:
            self._next_auto_cel_index = max(self._next_auto_cel_index, 1)
        
        debug(f"Started cel {cel_index} for sprite '{self._defining_sprite.name}'", 
              Level.DEBUG, Component.SPRITE)
        
        return cel_index
    
    def end_sprite_definition(self) -> MatrixSprite:
        """
        End the current sprite definition and validate cel indices.
        
        Returns:
            The completed sprite template
        """
        if self._defining_sprite is None:
            raise RuntimeError("Not currently defining a sprite")
        
        sprite = self._defining_sprite
        
        # Validate cel indices are sequential with no gaps
        max_cel = max(self._cel_indices_used) if self._cel_indices_used else 0
        expected_indices = set(range(max_cel + 1))
        missing = expected_indices - self._cel_indices_used
        
        if missing:
            raise ValueError(f"Gap in cel indices for sprite '{sprite.name}': missing {sorted(missing)}")
        
        # Store template
        self.templates[sprite.name] = sprite
        
        # Reset definition state
        self._defining_sprite = None
        self._cel_indices_used = set()
        self._next_auto_cel_index = 0
        self._in_cel_block = False
        
        debug(f"Completed sprite definition '{sprite.name}' with {sprite.cel_count} cel(s)", 
              Level.INFO, Component.SPRITE)
        
        return sprite
    
    def get_drawing_target(self) -> Optional[MatrixSprite]:
        """Get the sprite currently being defined (for drawing commands)."""
        return self._defining_sprite

    # ========== Template and Instance Access ==========
    
    def get_template(self, name: str) -> Optional[MatrixSprite]:
        """Get a sprite template by name."""
        return self.templates.get(name)

    def get_instance(self, name: str, instance_id: int = 0) -> Optional[SpriteInstance]:
        """Get a specific sprite instance by name and instance ID."""
        if name not in self.instances or instance_id not in self.instances[name]:
            # This is DEBUG level because it's expected when showing a sprite for the first time
            # (show_sprite will call create_instance after this returns None)
            debug(f"Sprite instance '{name}[{instance_id}]' not found (will create if showing)", 
                  Level.DEBUG, Component.SPRITE)
            return None
        
        debug(f"Retrieved sprite instance '{name}[{instance_id}]'", Level.TRACE, Component.SPRITE)
        return self.instances[name][instance_id]

    # ========== Instance Management ==========
    
    def create_instance(self, name: str, instance_id: int, x: float = 0, y: float = 0,
                       z_index: int = 0, cel_index: int = 0) -> Optional[SpriteInstance]:
        """Create a new instance of an existing sprite template."""
        debug(f"Creating instance {instance_id} of sprite '{name}'", Level.INFO, Component.SPRITE)
        
        # Check if template exists
        template = self.templates.get(name)
        if template is None:
            debug(f"Sprite template '{name}' not found", Level.ERROR, Component.SPRITE)
            return None
        
        # Validate cel index
        if cel_index >= template.cel_count:
            debug(f"Cel index {cel_index} out of range for sprite '{name}'", Level.ERROR, Component.SPRITE)
            return None
        
        # Initialize instance dict if needed
        if name not in self.instances:
            self.instances[name] = {}
        
        # Check if instance already exists
        if instance_id in self.instances[name]:
            debug(f"Instance {instance_id} of sprite '{name}' already exists", Level.WARNING, Component.SPRITE)
            return self.instances[name][instance_id]
        
        # Create the instance
        instance = SpriteInstance(template, x, y, z_index, cel_index)
        self.instances[name][instance_id] = instance
        self.z_order.append((name, instance_id))
        
        debug(f"Created instance {instance_id} of sprite '{name}' at cel {cel_index}", 
              Level.DEBUG, Component.SPRITE)
        return instance

    def get_overlapping_sprites(self, cells: List[Tuple[int, int]]) -> List[SpriteInstance]:
        """Get all visible sprite instances that overlap given grid cells in z-order."""
        overlapping = []
        cells_set = set(cells)
        
        for name, instance_id in self.z_order:
            if name in self.instances and instance_id in self.instances[name]:
                instance = self.instances[name][instance_id]
                if instance.visible and instance.occupied_cells.intersection(cells_set):
                    overlapping.append(instance)
                    debug(f"Found overlapping sprite: {name} instance {instance_id}", 
                          Level.DEBUG, Component.SPRITE)
        
        return overlapping

    def dispose_sprite_instance(self, name: str, instance_id: int) -> List[Tuple[int, int]]:
        """
        Dispose of a specific sprite instance.
        Returns the dirty cells that need to be refreshed.
        """
        debug(f"Disposing sprite '{name}' instance {instance_id}", Level.INFO, Component.SPRITE)
        
        if name not in self.instances or instance_id not in self.instances[name]:
            debug(f"Sprite '{name}' instance {instance_id} not found for disposal", 
                  Level.WARNING, Component.SPRITE)
            return []
        
        instance = self.instances[name][instance_id]
        dirty_cells = []
        
        # If visible, mark cells as dirty
        if instance.visible:
            dirty_cells = list(instance.occupied_cells)
            instance.visible = False
            instance.occupied_cells.clear()
        
        # Remove from z-order and instances dictionary
        if (name, instance_id) in self.z_order:
            self.z_order.remove((name, instance_id))
        
        del self.instances[name][instance_id]
        
        # If no instances left, clean up the instance entry (but keep template)
        if not self.instances[name]:
            del self.instances[name]
        
        debug(f"Disposed sprite '{name}' instance {instance_id}, {len(dirty_cells)} cells marked dirty", 
              Level.DEBUG, Component.SPRITE)
        
        return dirty_cells

    def dispose_all_sprites(self) -> List[Tuple[int, int]]:
        """
        Dispose of all sprite instances and templates.
        Returns dirty cells for display cleanup.
        """
        debug("Disposing of all sprites", Level.INFO, Component.SPRITE)
        
        # Collect dirty cells from visible instances
        dirty_cells = set()
        for sprite_name, instances in self.instances.items():
            for instance_id, instance in instances.items():
                if instance.visible:
                    dirty_cells.update(instance.occupied_cells)
                    instance.visible = False
                    instance.occupied_cells.clear()
        
        # Clear all collections
        self.instances.clear()
        self.templates.clear()
        self.z_order.clear()
        
        debug(f"Disposed of all sprites, {len(dirty_cells)} cells marked dirty", 
            Level.DEBUG, Component.SPRITE)
        
        return list(dirty_cells)