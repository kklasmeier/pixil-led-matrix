# File: rgb_matrix_lib/drawing_objects.py
import time
import threading
from queue import PriorityQueue, Empty
from typing import List, Tuple, Optional
from .debug import debug, Level, Component
from enum import Enum

# Constants
BURNOUT_WAKE_INTERVAL = 0.010  # 10ms wake interval
BURNOUT_THREAD_NAME = "BurnoutProcessor"

class ShapeType(Enum):
    """Represents a geometric shape type."""
    POINT = "point"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    POLYGON = "polygon"
    ELLIPSE = "ellipse"

class Region:
    """Represents a geometric region on the display."""
    
    def __init__(self, shape_type: ShapeType, bounds: tuple):
        """
        Initialize a region.
        
        Args:
            shape_type: Type of shape (point, line, rect, circle, etc)
            bounds: Shape-specific boundary info:
                POINT: (x, y)
                LINE: (x1, y1, x2, y2)
                RECTANGLE: (x, y, width, height)
                CIRCLE: (center_x, center_y, radius)
                POLYGON: (center_x, center_y, radius, sides)
        """
        self.shape_type = shape_type
        self.bounds = bounds
        debug(f"Created region: {shape_type.value} with bounds {bounds}",
              Level.DEBUG, Component.DRAWING)
    
    def get_bounding_box(self) -> tuple[int, int, int, int]:
        """Get rectangular bounds that contain the region (x, y, width, height)."""
        if self.shape_type == ShapeType.POINT:
            x, y = self.bounds
            return (x, y, 1, 1)
            
        elif self.shape_type == ShapeType.LINE:
            x1, y1, x2, y2 = self.bounds
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1) + 1
            height = abs(y2 - y1) + 1
            return (x, y, width, height)
            
        elif self.shape_type == ShapeType.RECTANGLE:
            return self.bounds  # Already in correct format
            
        elif self.shape_type == ShapeType.CIRCLE:
            center_x, center_y, radius = self.bounds
            return (center_x - radius, center_y - radius, radius * 2, radius * 2)
            
        elif self.shape_type == ShapeType.POLYGON:
            center_x, center_y, radius, sides = self.bounds
            return (center_x - radius, center_y - radius, radius * 2, radius * 2)
            
        debug(f"Unknown shape type for bounding box: {self.shape_type}",
              Level.WARNING, Component.DRAWING)
        return (0, 0, 0, 0)

class DrawingObject:
    """Represents a drawing object with burnout timing and region information."""
    
    def __init__(self, removal_time: float, region: Region, points: List[Tuple[int, int]]):
        """
        Initialize a drawing object.
        
        Args:
            removal_time: Time when object should burn out (seconds since epoch)
            region: Region information for the shape
            points: List of (x, y) coordinates that make up this object
        """
        self.removal_time = removal_time
        self.region = region
        self.points = points
        debug(f"Created drawing object: {region.shape_type.value} with {len(points)} points",
              Level.DEBUG, Component.DRAWING)
              
    def __lt__(self, other):
        """Enable comparison for priority queue ordering."""
        return self.removal_time < other.removal_time
        
    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Check if the object has expired."""
        if current_time is None:
            current_time = time.time()
        return current_time >= self.removal_time
        
    def get_points(self) -> List[Tuple[int, int]]:
        """Get the list of points in this drawing object."""
        return self.points
        
    def get_region(self) -> Region:
        """Get the region information for this object."""
        return self.region
        
    def time_remaining(self, current_time: Optional[float] = None) -> float:
        """Get the remaining time before burnout."""
        if current_time is None:
            current_time = time.time()
        remaining = self.removal_time - current_time
        debug(f"Drawing object has {remaining:.2f} seconds remaining",
              Level.TRACE, Component.DRAWING)
        return remaining

class ThreadedBurnoutManager:
    """Manages drawing objects with threaded priority queue for burnout handling."""
    
    def __init__(self, api_instance):
        """Initialize the threaded burnout manager."""
        debug("Initializing ThreadedBurnoutManager", Level.INFO, Component.DRAWING)
        self.api = api_instance
        self.burnout_queue = PriorityQueue()
        self.is_running = threading.Event()
        self.burnout_thread = None

    def start(self):
        """Start the burnout processing thread."""
        debug("Starting burnout thread", Level.INFO, Component.DRAWING)
        self.is_running.set()
        self.burnout_thread = threading.Thread(
            target=self._process_burnouts,
            name=BURNOUT_THREAD_NAME,
            daemon=True
        )
        self.burnout_thread.start()

    def stop(self):
        """Stop the burnout processing thread."""
        debug("Stopping burnout thread", Level.INFO, Component.DRAWING)
        if self.is_running.is_set():
            self.is_running.clear()
            if self.burnout_thread:
                self.burnout_thread.join(timeout=1.0)

    def add_object(self, shape_type: ShapeType, bounds: tuple, 
                  points: List[Tuple[int, int]], duration_ms: float) -> DrawingObject:
        """Add a new drawing object to burnout queue."""
        try:
            removal_time = time.time() + (duration_ms / 1000.0)
            region = Region(shape_type, bounds)
            obj = DrawingObject(removal_time, region, points)
            self.burnout_queue.put(obj)
            debug(f"Added {shape_type.value} to burnout queue, duration {duration_ms}ms",
                  Level.DEBUG, Component.DRAWING)
            return obj
        except Exception as e:
            debug(f"Error adding object to burnout queue: {str(e)}", 
                  Level.ERROR, Component.DRAWING)
            raise

    def clear_all(self) -> None:
        """Remove all drawing objects from queue."""
        try:
            while not self.burnout_queue.empty():
                try:
                    self.burnout_queue.get_nowait()
                except Empty:
                    break
            debug("Cleared all drawing objects from queue",
                  Level.INFO, Component.DRAWING)
        except Exception as e:
            debug(f"Error clearing burnout queue: {str(e)}", 
                  Level.ERROR, Component.DRAWING)

    def _process_burnouts(self) -> None:
        """Main burnout processing loop."""
        debug("Burnout processing thread started", Level.INFO, Component.DRAWING)
        
        while self.is_running.is_set():
            try:
                # Process any expired objects
                current_time = time.time()
                
                while not self.burnout_queue.empty():
                    try:
                        # Peek at next object (don't remove yet)
                        obj = self.burnout_queue.queue[0]
                        
                        if obj.is_expired(current_time):
                            # Remove and process
                            obj = self.burnout_queue.get_nowait()
                            self._clear_object(obj)
                        else:
                            # If this one's not ready, later ones won't be
                            break
                    except Empty:
                        # Queue was cleared while processing
                        break
                    except Exception as e:
                        debug(f"Error processing burnout: {str(e)}", 
                              Level.ERROR, Component.DRAWING)
                
                # Sleep until next check
                time.sleep(BURNOUT_WAKE_INTERVAL)
                
            except Exception as e:
                debug(f"Error in burnout thread: {str(e)}", 
                      Level.ERROR, Component.DRAWING)
                # Continue running despite errors
                time.sleep(BURNOUT_WAKE_INTERVAL)

    def _clear_object(self, obj: DrawingObject) -> None:
        """Clear an expired object from the display."""
        try:
            region = obj.get_region()
            
            # Fast path for rectangles
            if region.shape_type == ShapeType.RECTANGLE:
                x, y, width, height = region.bounds
                # Clamp coordinates to matrix boundaries
                start_x = max(0, x)
                start_y = max(0, y)
                end_x = min(x + width, self.api.matrix.width)
                end_y = min(y + height, self.api.matrix.height)
                
                # Clear rectangle area only within bounds
                for i in range(start_x, end_x):
                    for j in range(start_y, end_y):
                        self.api._draw_to_buffers(i, j, 0, 0, 0)
            else:
                # For other shapes, clear individual points
                for point in obj.get_points():
                    self.api._draw_to_buffers(point[0], point[1], 0, 0, 0)
                    
        except Exception as e:
            debug(f"Error clearing object: {str(e)}", 
                  Level.ERROR, Component.DRAWING)