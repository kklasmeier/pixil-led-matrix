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