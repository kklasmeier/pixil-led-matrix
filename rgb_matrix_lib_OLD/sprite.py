# File: rgb_matrix_lib/sprite.py

import numpy as np
from typing import List, Tuple, Dict, Optional
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
        self.x = 0
        self.y = 0
        self.visible = False
        self.z_index = 0
        self.occupied_cells = set()

        # Initialize with transparent color
        self.clear()
        
        debug(f"Sprite buffer created and initialized transparent", Level.DEBUG, Component.SPRITE)
    
    def plot(self, x: int, y: int, color: tuple):
        """Plot a single pixel in the sprite buffer."""
        debug(f"Plotting on sprite '{self.name}' at ({x},{y}) with color {color}", 
              Level.TRACE, Component.SPRITE)
              
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = color
        else:
            debug(f"Plot coordinates ({x},{y}) out of sprite bounds", 
                  Level.WARNING, Component.SPRITE)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: tuple):
        """Draw a line in the sprite buffer."""
        debug(f"Drawing line on sprite '{self.name}' from ({x0},{y0}) to ({x1},{y1})", 
              Level.DEBUG, Component.SPRITE)
              
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        points_drawn = 0
        while True:
            if 0 <= x0 < self.width and 0 <= y0 < self.height:
                self.buffer[y0, x0] = color
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
                
        debug(f"Line complete, {points_drawn} points drawn", Level.TRACE, Component.SPRITE)

    def draw_rectangle(self, x: int, y: int, width: int, height: int, color: tuple, fill: bool = False):
        """Draw a rectangle in the sprite buffer."""
        debug(f"Drawing {'filled' if fill else 'outline'} rectangle on sprite '{self.name}' at ({x},{y})", 
              Level.DEBUG, Component.SPRITE)
              
        points_drawn = 0
        
        if fill:
            for i in range(max(0, x), min(x + width, self.width)):
                for j in range(max(0, y), min(y + height, self.height)):
                    self.buffer[j, i] = color
                    points_drawn += 1
        else:
            # Draw horizontal lines
            for i in range(max(0, x), min(x + width, self.width)):
                if 0 <= y < self.height:
                    self.buffer[y, i] = color
                    points_drawn += 1
                if 0 <= y + height - 1 < self.height:
                    self.buffer[y + height - 1, i] = color
                    points_drawn += 1
            
            # Draw vertical lines
            for j in range(max(0, y), min(y + height, self.height)):
                if 0 <= x < self.width:
                    self.buffer[j, x] = color
                    points_drawn += 1
                if 0 <= x + width - 1 < self.width:
                    self.buffer[j, x + width - 1] = color
                    points_drawn += 1
                    
        debug(f"Rectangle complete, {points_drawn} points drawn", Level.TRACE, Component.SPRITE)

    def draw_circle(self, x_center: int, y_center: int, radius: int, color: tuple, fill: bool = False):
        """Draw a circle in the sprite buffer."""
        debug(f"Drawing {'filled' if fill else 'outline'} circle on sprite '{self.name}' at ({x_center},{y_center})", 
              Level.DEBUG, Component.SPRITE)
              
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
                    self.buffer[py, px] = color
                    points_drawn += 1

        def draw_line(x0: int, y0: int, x1: int):
            nonlocal points_drawn
            if 0 <= y0 < self.height:
                for x in range(max(0, x0), min(x1 + 1, self.width)):
                    self.buffer[y0, x] = color
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
                
        debug(f"Circle complete, {points_drawn} points drawn", Level.TRACE, Component.SPRITE)


    def draw_polygon(self, x_center: int, y_center: int, radius: int, sides: int, color: tuple, 
                rotation: float = 0, fill: bool = False):
        """
        Draw a regular polygon in the sprite buffer.
        
        Args:
            x_center, y_center: Center coordinates relative to sprite
            radius: Distance from center to vertices
            sides: Number of sides
            color: RGB color tuple
            rotation: Rotation in degrees clockwise
            fill: Whether to fill the polygon
        """
        debug(f"Drawing polygon on sprite '{self.name}' at ({x_center},{y_center})", 
            Level.DEBUG, Component.SPRITE)
            
        # Get vertices
        points = polygon_vertices(x_center, y_center, radius, sides, rotation)
        
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
                if 0 <= x0 < self.width and 0 <= y0 < self.height:
                    self.buffer[y0, x0] = color
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
            max_x = min(self.width - 1, max(p[0] for p in points))
            min_y = max(0, min(p[1] for p in points))
            max_y = min(self.height - 1, max(p[1] for p in points))
            
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
                            if 0 <= x < self.width and 0 <= y < self.height:
                                self.buffer[y, x] = color
    
    def clear(self):
        """Clear sprite buffer with transparent color."""
        self.buffer[:, :] = TRANSPARENT_COLOR
        debug(f"Sprite '{self.name}' cleared with transparent color", Level.DEBUG, Component.SPRITE)

class SpriteManager:
    def __init__(self):
        """Initialize the sprite manager."""
        debug("Initializing SpriteManager", Level.INFO, Component.SPRITE)
        self.sprites: Dict[str, MatrixSprite] = {}
        self.z_order: List[str] = []  # Track sprites in z-order


    def dispose_all_sprites(self):
        """
        Dispose of all sprites and clear their resources.
        """
        debug("Disposing of all sprites", Level.INFO, Component.SPRITE)
        
        # Get list of visible sprites for cleanup
        visible_sprites = [sprite for sprite in self.sprites.values() if sprite.visible]
        
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
        """Create a new sprite."""
        debug(f"Creating new sprite: {name} ({width}x{height})", Level.INFO, Component.SPRITE)
        if name in self.sprites:
            debug(f"Sprite '{name}' already exists", Level.ERROR, Component.SPRITE)
            raise ValueError(f"Sprite '{name}' already exists")
            
        sprite = MatrixSprite(width, height, name)
        self.z_order.append(name)
        self.sprites[name] = sprite

        return sprite

    def get_overlapping_sprites(self, cells: List[Tuple[int, int]]) -> List[MatrixSprite]:
        """Get all visible sprites that overlap given grid cells in z-order."""
        overlapping = []
        for name in self.z_order:
            sprite = self.sprites[name]
            if sprite.visible and sprite.occupied_cells.intersection(cells):
                overlapping.append(sprite)
                debug(f"Found overlapping sprite: {name} at z-index {self.z_order.index(name)}", Level.DEBUG, Component.SPRITE)
        return overlapping
        
    def get_sprite(self, name: str) -> Optional[MatrixSprite]:
        """Get a sprite by name."""
        sprite = self.sprites.get(name)
        if sprite is None:
            debug(f"Sprite '{name}' not found", Level.WARNING, Component.SPRITE)
        else:
            debug(f"Retrieved sprite '{name}'", Level.TRACE, Component.SPRITE)
        return sprite

