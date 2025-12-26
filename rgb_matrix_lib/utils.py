# File: rgb_matrix_lib/utils.py

from typing import Dict, Tuple, Optional, List, Union
from .debug import debug, Level, Component
import numpy as np
import math

# System Colors - Do Not Modify
TRANSPARENT_COLOR = (0, 0, 1)  # RGB value for transparent pixels
BLACK_COLOR = (0, 0, 0)        # True black
GRID_SIZE = 16                 # Grid cell size

# Named Colors (8-bit RGB values)
NAMED_COLORS = {
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'gray': (128, 128, 128),
    'light_gray': (192, 192, 192),
    'dark_gray': (64, 64, 64),
    'silver': (192, 192, 192),
    'red': (255, 0, 0),
    'crimson': (220, 20, 60),
    'maroon': (128, 0, 0),
    'rose': (255, 0, 128),
    'pink': (255, 0, 85),
    'salmon': (255, 85, 85),
    'coral': (255, 64, 64),
    'brown': (165, 42, 42),
    'standard_brown': (139, 69, 19),
    'dark_brown': (101, 67, 33),
    'wood_brown': (133, 94, 66),
    'tan': (210, 180, 140),
    'orange': (255, 85, 0),
    'gold': (255, 170, 0),
    'peach': (255, 218, 185),
    'bronze': (205, 127, 50),
    'yellow': (255, 255, 0),
    'lime': (85, 255, 0),
    'green': (0, 255, 0),
    'olive': (128, 128, 0),
    'spring_green': (0, 255, 64),
    'forest_green': (0, 212, 42),
    'mint': (62, 255, 192),
    'teal': (0, 255, 128),
    'turquoise': (0, 255, 212),
    'cyan': (0, 255, 255),
    'sky_blue': (0, 128, 255),
    'azure': (42, 212, 255),
    'blue': (0, 0, 255),
    'navy': (0, 0, 128),
    'royal_blue': (65, 105, 225),
    'ocean_blue': (0, 85, 255),
    'indigo': (85, 0, 255),
    'purple': (128, 0, 255),
    'violet': (212, 0, 255),
    'magenta': (255, 0, 255),
    'lavender': (212, 0, 212),
}

def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    Convert HSV color to RGB.
    
    Args:
        h: Hue (0-360)
        s: Saturation (0-1)
        v: Value (0-1)
    
    Returns:
        Tuple[int, int, int]: RGB values (0-255)
    """
    h = float(h)
    s = float(s)
    v = float(v)
    
    h60 = h / 60.0
    h60f = math.floor(h60)
    hi = int(h60f) % 6
    f = h60 - h60f
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    
    r, g, b = 0, 0, 0
    if hi == 0:
        r, g, b = v, t, p
    elif hi == 1:
        r, g, b = q, v, p
    elif hi == 2:
        r, g, b = p, v, t
    elif hi == 3:
        r, g, b = p, q, v
    elif hi == 4:
        r, g, b = t, p, v
    elif hi == 5:
        r, g, b = v, p, q
    
    r, g, b = int(r * 255), int(g * 255), int(b * 255)
    return (r, g, b)

def generate_spectral_colors() -> Dict[int, Tuple[int, int, int]]:
    """
    Generate spectral colors using HSV color space.
    Maps 0-99 to full hue range with max saturation/value.
    
    Returns:
        Dict mapping 0-99 to RGB tuples
    """
    colors = {}
    for i in range(100):
        hue = (i * 359.9) / 99.0
        colors[i] = hsv_to_rgb(hue, 1.0, 1.0)
    return colors

# Spectral System (0-99 mapped to 8-bit RGB)
SPECTRAL_COLORS = generate_spectral_colors()

def get_color_rgb(color: Union[str, int, Tuple[int, int, int]], intensity: int = 100) -> Tuple[int, int, int]:
    """
    Get RGB values for a color and optional intensity.
    
    Args:
        color: Named color (str), spectral number (int, 0-99), or RGB tuple
        intensity: Color intensity (0-100), defaults to 100
    
    Returns:
        Tuple[int, int, int]: RGB values scaled by intensity
    """
    # Clamp intensity to valid range
    intensity = max(0, min(100, intensity))
    scale = intensity / 100.0

    # Handle RGB tuple input
    if isinstance(color, tuple) and len(color) == 3:
        base_rgb = color
    # Handle spectral colors (numeric input)
    elif isinstance(color, int):
        if 0 <= color <= 99:
            base_rgb = SPECTRAL_COLORS[color]
        else:
            clamped = max(0, min(99, color))
            base_rgb = SPECTRAL_COLORS[clamped]
            debug(f"Clamped spectral color {color} to {clamped}", 
                  Level.WARNING, Component.SYSTEM)
    # Handle named colors
    else:
        color_lower = color.lower()
        base_rgb = NAMED_COLORS.get(color_lower, NAMED_COLORS['white'])
        if color_lower not in NAMED_COLORS:
            debug(f"Unknown color '{color}', defaulting to white", 
                  Level.WARNING, Component.SYSTEM)
    
    # Apply intensity scaling with explicit unpacking to ensure correct return type
    r, g, b = base_rgb
    return (int(r * scale), int(g * scale), int(b * scale))

def is_transparent(color: Tuple[int, int, int]) -> bool:
    """Check if a color is the transparent color."""
    return color == TRANSPARENT_COLOR

def get_color_palette() -> Dict[str, Tuple[int, int, int]]:
    """Get the standard color palette."""
    debug("Creating color palette", Level.TRACE, Component.SYSTEM)
    palette = {
        "transparent": TRANSPARENT_COLOR,
        **NAMED_COLORS
    }
    return palette

def clamp_coordinates(x: int, y: int, width: int, height: int) -> Tuple[int, int]:
    """
    Clamp coordinates to matrix boundaries.
    
    Args:
        x, y: Coordinates to clamp
        width, height: Matrix dimensions
        
    Returns:
        Tuple of clamped (x, y) coordinates
    """
    clamped_x = max(0, min(x, width - 1))
    clamped_y = max(0, min(y, height - 1))
    
    if clamped_x != x or clamped_y != y:
        debug(f"Clamped coordinates ({x}, {y}) to ({clamped_x}, {clamped_y})", 
              Level.TRACE, Component.SYSTEM)
              
    return clamped_x, clamped_y

def validate_bounds(x: int, y: int, width: int, height: int) -> bool:
    """
    Check if coordinates are within bounds.
    
    Args:
        x, y: Coordinates to check
        width, height: Matrix dimensions
        
    Returns:
        bool: True if coordinates are within bounds
    """
    valid = 0 <= x < width and 0 <= y < height
    if not valid:
        debug(f"Coordinates ({x}, {y}) out of bounds", Level.WARNING, Component.SYSTEM)
    return valid

def calculate_burnout_time(milliseconds: Optional[int]) -> Optional[float]:
    """
    Calculate burnout time from milliseconds.
    
    Args:
        milliseconds: Duration in milliseconds (None for no burnout)
        
    Returns:
        Optional[float]: Time in seconds when burnout should occur
    """
    if milliseconds is None:
        return None
        
    import time
    burnout_time = time.time() + (milliseconds / 1000.0)
    debug(f"Calculated burnout time: {burnout_time} for {milliseconds}ms", 
          Level.TRACE, Component.SYSTEM)
    return burnout_time

#Grid Management
def get_grid_cells(x: int, y: int, width: int, height: int) -> List[Tuple[int, int]]:
    """Return list of grid cells covered by a region"""
    start_grid_x = x // GRID_SIZE
    start_grid_y = y // GRID_SIZE
    end_grid_x = (x + width - 1) // GRID_SIZE
    end_grid_y = (y + height - 1) // GRID_SIZE
    
    return [(gx, gy) for gx in range(start_grid_x, end_grid_x + 1)
                     for gy in range(start_grid_y, end_grid_y + 1)]

def is_cell_empty(buffer: np.ndarray, grid_x: int, grid_y: int) -> bool:
    """Check if a grid cell is completely black"""
    start_x = grid_x * GRID_SIZE
    start_y = grid_y * GRID_SIZE
    cell = buffer[start_y:start_y + GRID_SIZE, start_x:start_x + GRID_SIZE]
    return bool(np.all(cell == 0))

def polygon_vertices(x_center: int, y_center: int, radius: int, sides: int, rotation: float = 0) -> List[Tuple[int, int]]:
    # Calculate default offset based on number of sides
    # For odd number of sides, offset by 90 degrees to point up
    # For even number of sides, offset by 90 - (180/sides) to align flat side at top
    default_offset = 90 if sides % 2 != 0 else (90 - (180/sides))
    
    # Convert rotation to radians and adjust for clockwise rotation
    angle = -math.radians(rotation + default_offset)
    
    vertices = []
    for i in range(sides):
        # Calculate angle for each vertex
        theta = angle + (2 * math.pi * i) / sides
        
        # Convert polar to cartesian coordinates
        x = x_center + int(radius * math.cos(theta))
        y = y_center + int(radius * math.sin(theta))
        
        vertices.append((x, y))
    
    return vertices

def rotate_points(points: List[Tuple[int, int]], x_center: int, y_center: int, 
                 angle_deg: float) -> List[Tuple[int, int]]:
    # Convert to radians and adjust for clockwise rotation
    angle = -math.radians(angle_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    
    rotated = []
    for x, y in points:
        # Translate to origin
        dx = x - x_center
        dy = y - y_center
        
        # Rotate
        rx = int(dx * cos_a - dy * sin_a)
        ry = int(dx * sin_a + dy * cos_a)
        
        # Translate back
        rotated.append((rx + x_center, ry + y_center))
    
    return rotated


def arc_points(x1: int, y1: int, x2: int, y2: int, bulge: float, 
               filled: bool = False) -> List[Tuple[int, int]]:
    """
    Calculate pixel coordinates for an arc defined by two endpoints and a bulge value.
    
    The arc is defined by:
    - Start point (x1, y1)
    - End point (x2, y2)
    - Bulge: perpendicular distance from chord midpoint to arc peak
      - Positive bulge: arc curves to port (left when traveling from start to end)
      - Negative bulge: arc curves to starboard (right)
      - Zero bulge: straight line
    
    Args:
        x1, y1: Start point coordinates
        x2, y2: End point coordinates
        bulge: Perpendicular distance from chord to arc peak
        filled: If True, fill the chord area (between arc and straight chord line)
    
    Returns:
        List of (x, y) pixel coordinates
    """
    points = set()
    
    # Handle degenerate case: bulge = 0 means straight line
    if abs(bulge) < 0.001:
        debug(f"Arc with zero bulge - drawing straight line from ({x1},{y1}) to ({x2},{y2})", 
              Level.TRACE, Component.DRAWING)
        return _line_points(x1, y1, x2, y2)
    
    # Calculate chord properties
    chord_dx = x2 - x1
    chord_dy = y2 - y1
    chord_length = math.sqrt(chord_dx * chord_dx + chord_dy * chord_dy)
    
    # Handle degenerate case: start and end are the same point
    if chord_length < 0.001:
        debug(f"Arc with coincident endpoints - returning single point", 
              Level.TRACE, Component.DRAWING)
        return [(round(x1), round(y1))]
    
    # Chord midpoint
    mx = (x1 + x2) / 2.0
    my = (y1 + y2) / 2.0
    
    # Unit vector along chord
    ux = chord_dx / chord_length
    uy = chord_dy / chord_length
    
    # Perpendicular unit vector (rotated 90° counterclockwise = "port" side)
    # When traveling from start to end, port is to the left
    px = -uy
    py = ux
    
    # The arc peak point (on the arc, perpendicular to chord midpoint)
    # Positive bulge = port side, negative = starboard side
    peak_x = mx + px * bulge
    peak_y = my + py * bulge
    
    # Now find the circle center and radius
    # The center lies on the perpendicular bisector of the chord
    # and is equidistant from start, end, and peak
    
    # Using the relationship between chord, sagitta (bulge), and radius:
    # For a chord of length L with sagitta h:
    # radius = (L²/4 + h²) / (2|h|)
    half_chord = chord_length / 2.0
    abs_bulge = abs(bulge)
    radius = (half_chord * half_chord + abs_bulge * abs_bulge) / (2.0 * abs_bulge)
    
    # Distance from chord midpoint to center (along perpendicular)
    # center_dist = radius - |bulge| (center is on opposite side of chord from peak)
    center_dist = radius - abs_bulge
    
    # Center position: move from midpoint toward the peak, then continue past it
    # Actually: center is on the OPPOSITE side of the chord from the peak
    # If bulge > 0 (peak on port side), center is on starboard side
    cx = mx - px * bulge / abs_bulge * center_dist
    cy = my - py * bulge / abs_bulge * center_dist
    
    debug(f"Arc: chord_len={chord_length:.2f}, bulge={bulge:.2f}, radius={radius:.2f}, "
          f"center=({cx:.2f},{cy:.2f})", Level.TRACE, Component.DRAWING)
    
    # Calculate start and end angles from center
    start_angle = math.atan2(y1 - cy, x1 - cx)
    end_angle = math.atan2(y2 - cy, x2 - cx)
    
    # Determine sweep direction based on bulge sign
    # Positive bulge (port side curve): we need to go the "short way" that passes through peak
    # We need to determine if we should go clockwise or counterclockwise
    
    # Calculate the angle to the peak point
    peak_angle = math.atan2(peak_y - cy, peak_x - cx)
    
    # Normalize angles to [0, 2π)
    def normalize_angle(a):
        while a < 0:
            a += 2 * math.pi
        while a >= 2 * math.pi:
            a -= 2 * math.pi
        return a
    
    start_angle_norm = normalize_angle(start_angle)
    end_angle_norm = normalize_angle(end_angle)
    peak_angle_norm = normalize_angle(peak_angle)
    
    # Determine if going counterclockwise from start to end passes through peak
    def angle_between_ccw(start, end, test):
        """Check if test angle is between start and end going counterclockwise"""
        if start <= end:
            return start <= test <= end
        else:
            return test >= start or test <= end
    
    ccw_passes_peak = angle_between_ccw(start_angle_norm, end_angle_norm, peak_angle_norm)
    
    # Choose direction that passes through the peak
    if ccw_passes_peak:
        # Go counterclockwise
        if end_angle_norm < start_angle_norm:
            end_angle_norm += 2 * math.pi
        sweep = end_angle_norm - start_angle_norm
        direction = 1  # counterclockwise
    else:
        # Go clockwise
        if start_angle_norm < end_angle_norm:
            start_angle_norm += 2 * math.pi
        sweep = start_angle_norm - end_angle_norm
        direction = -1  # clockwise
    
    # Number of steps based on arc length
    arc_length = abs(sweep) * radius
    num_steps = max(int(arc_length * 2), 20)  # At least 20 steps, ~0.5 pixel per step
    
    debug(f"Arc sweep: {math.degrees(sweep):.1f}° in {num_steps} steps, direction={direction}", 
          Level.TRACE, Component.DRAWING)
    
    # Generate arc points
    arc_outline = []
    for i in range(num_steps + 1):
        t = i / num_steps
        if direction == 1:
            angle = start_angle + t * sweep
        else:
            angle = start_angle - t * sweep
        
        px_arc = round(cx + radius * math.cos(angle))
        py_arc = round(cy + radius * math.sin(angle))
        arc_outline.append((px_arc, py_arc))
        points.add((px_arc, py_arc))
    
    if filled:
        # Chord fill: fill the area between the arc and the straight chord line
        # Use scanline fill algorithm
        
        # Get chord line points
        chord_points = _line_points(x1, y1, x2, y2)
        
        # Build a closed polygon: arc points + chord points (reversed to close)
        # Actually, we just need the arc outline - the chord closes it
        polygon = arc_outline.copy()
        
        # Find bounding box
        all_x = [p[0] for p in polygon]
        all_y = [p[1] for p in polygon]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Scanline fill between arc and chord
        for y in range(min_y, max_y + 1):
            # Find arc intersections at this y
            arc_intersections = []
            for i in range(len(arc_outline) - 1):
                ax1, ay1 = arc_outline[i]
                ax2, ay2 = arc_outline[i + 1]
                if (ay1 <= y < ay2) or (ay2 <= y < ay1):
                    if ay2 != ay1:
                        t = (y - ay1) / (ay2 - ay1)
                        x_intersect = ax1 + t * (ax2 - ax1)
                        arc_intersections.append(x_intersect)
            
            # Find chord intersection at this y
            chord_intersections = []
            if (y1 <= y < y2) or (y2 <= y < y1):
                if y2 != y1:
                    t = (y - y1) / (y2 - y1)
                    x_intersect = x1 + t * (x2 - x1)
                    chord_intersections.append(x_intersect)
            
            # Combine and sort all intersections
            all_intersections = arc_intersections + chord_intersections
            if len(all_intersections) >= 2:
                all_intersections.sort()
                # Fill between pairs
                for i in range(0, len(all_intersections) - 1, 2):
                    x_start = int(round(all_intersections[i]))
                    x_end = int(round(all_intersections[i + 1]))
                    for x in range(x_start, x_end + 1):
                        points.add((x, y))
    
    return list(points)


def _line_points(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    """
    Generate points along a line using Bresenham's algorithm.
    
    Args:
        x0, y0: Start point
        x1, y1: End point
    
    Returns:
        List of (x, y) coordinates along the line
    """
    points = []
    
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
    
    return points