from queue import PriorityQueue
from threading import Thread, Lock
from typing import List, Tuple, TYPE_CHECKING, Optional
from enum import Enum
import time


class ShapeType(Enum):
    POINT = 1
    LINE = 2
    RECTANGLE = 3
    CIRCLE = 4
    POLYGON = 5
    ELLIPSE = 6
    ARC = 7


class BurnoutMode(Enum):
    INSTANT = 1  # Current behavior - stays lit, clears to black at expiration
    FADE = 2     # Gradual fade from full intensity to black over duration


class Region:
    def __init__(self, shape_type: ShapeType, bounds: tuple):
        self.shape_type = shape_type
        self.bounds = bounds


class DrawingObject:
    def __init__(self, removal_time: float, region: Region, points: List[Tuple[int, int]],
                 start_time: float,
                 mode: BurnoutMode = BurnoutMode.INSTANT,
                 pixel_colors: Optional[List[Tuple[int, int, int]]] = None):
        self.removal_time = removal_time
        self.region = region
        self.points = points
        self.start_time = start_time
        self.mode = mode
        self.pixel_colors = pixel_colors  # Only populated for FADE mode, parallel to points

    def get_region(self) -> Region:
        return self.region

    def get_points(self) -> List[Tuple[int, int]]:
        return self.points

    def is_expired(self, current_time: float) -> bool:
        return current_time >= self.removal_time

    def __lt__(self, other):
        return self.removal_time < other.removal_time


if TYPE_CHECKING:
    from .api import RGB_Api


class ThreadedBurnoutManager:
    BURNOUT_WAKE_INTERVAL = 0.01  # 10ms

    def __init__(self, api: "RGB_Api"):
        self.api = api
        self.burnout_queue = PriorityQueue()
        self.burnout_thread = None
        self.running = True
        self.pixel_index = {}  # (x, y) -> [(DrawingObject, removal_time), ...]
        self.index_lock = Lock()
        self.changes_made = False
        self.active_fades = set()  # Track objects currently fading

    def start(self):
        if self.burnout_thread is None:
            self.burnout_thread = Thread(target=self._process_burnouts)
            self.burnout_thread.daemon = True
            self.burnout_thread.start()

    def _process_burnouts(self):
        while self.running:
            try:
                current_time = time.time()
                
                # Process active fades
                self._update_active_fades(current_time)
                
                # Process expirations
                if not self.burnout_queue.empty():
                    obj = self.burnout_queue.queue[0]
                    if obj.is_expired(current_time):
                        self.burnout_queue.get_nowait()
                        self._clear_object(obj)
                        # Remove from active_fades if present
                        self.active_fades.discard(obj)
                
                time.sleep(self.BURNOUT_WAKE_INTERVAL)
            except Exception as e:
                from .debug import debug, Level, Component
                debug(f"Error in burnout thread: {e}", Level.ERROR, Component.SYSTEM)
                time.sleep(self.BURNOUT_WAKE_INTERVAL)

    def _update_active_fades(self, current_time: float):
        """Update intensity for all actively fading objects."""
        if not self.active_fades:
            return
        
        pixels_updated = False
        
        with self.index_lock:
            for obj in list(self.active_fades):
                # Skip if expired (will be handled by _clear_object)
                if obj.is_expired(current_time):
                    continue
                
                # Calculate fade progress
                duration = obj.removal_time - obj.start_time
                if duration <= 0:
                    continue
                    
                elapsed = current_time - obj.start_time
                progress = elapsed / duration  # 0.0 → 1.0
                intensity = max(0.0, 1.0 - progress)  # 1.0 → 0.0
                
                # Update each pixel if this object owns it
                for i, (x, y) in enumerate(obj.points):
                    if self._is_pixel_owner(x, y, obj):
                        r, g, b = obj.pixel_colors[i]
                        faded_r = int(r * intensity)
                        faded_g = int(g * intensity)
                        faded_b = int(b * intensity)
                        self.api._draw_to_buffers(x, y, faded_r, faded_g, faded_b)
                        pixels_updated = True
        
        if pixels_updated:
            self.changes_made = True

    def _is_pixel_owner(self, x: int, y: int, obj: DrawingObject) -> bool:
        """Check if the given object is the current owner of the pixel (has latest removal_time)."""
        entries = self.pixel_index.get((x, y), [])
        if not entries:
            return False
        
        # Find the entry with the latest removal_time
        latest_entry = max(entries, key=lambda e: e[1])
        return latest_entry[0] is obj

    def add_object(self, shape_type: ShapeType, bounds: tuple, points: List[Tuple[int, int]], 
                   duration_ms: float, mode: BurnoutMode = BurnoutMode.INSTANT,
                   pixel_colors: Optional[List[Tuple[int, int, int]]] = None):
        """
        Add a drawing object to the burnout manager.
        
        Args:
            shape_type: Type of shape (POINT, LINE, etc.)
            bounds: Shape parameters (coordinates, dimensions)
            points: List of (x, y) pixel coordinates
            duration_ms: Time until burnout in milliseconds
            mode: INSTANT (clear to black at expiration) or FADE (gradual fade)
            pixel_colors: For FADE mode, list of (r, g, b) tuples parallel to points
        """
        start_time = time.time()
        removal_time = start_time + (duration_ms / 1000.0)
        region = Region(shape_type, bounds)
        
        obj = DrawingObject(removal_time, region, points, start_time, mode, pixel_colors)
        
        self.burnout_queue.put(obj)
        
        with self.index_lock:
            for x, y in points:
                if (x, y) not in self.pixel_index:
                    self.pixel_index[(x, y)] = []
                self.pixel_index[(x, y)].append((obj, removal_time))
            
            # Track separately if it needs active fading
            if mode == BurnoutMode.FADE:
                self.active_fades.add(obj)

    def _clear_object(self, obj: DrawingObject):
        """
        Clear an expired drawing object by setting its pixels to black.
        If other objects use the same pixels with later expiry times, preserve those pixels.
        """
        current_time = time.time()
        points_to_clear = obj.get_points()
        pixels_changed = False

        with self.index_lock:
            for x, y in points_to_clear:
                entries = self.pixel_index.get((x, y), [])
                if not entries or max(t for _, t in entries) <= current_time:
                    self.api._draw_to_buffers(x, y, 0, 0, 0)
                    pixels_changed = True

        with self.index_lock:
            for x, y in points_to_clear:
                if (x, y) in self.pixel_index:
                    self.pixel_index[(x, y)] = [(o, t) for o, t in self.pixel_index[(x, y)] if o != obj]
                    if not self.pixel_index[(x, y)]:
                        del self.pixel_index[(x, y)]

        if pixels_changed:
            self.changes_made = True

    def clear_all(self):
        """Clear all burnout tracking."""
        while not self.burnout_queue.empty():
            self.burnout_queue.get_nowait()
        with self.index_lock:
            self.pixel_index.clear()
            self.active_fades.clear()

    def stop(self):
        """Stop the burnout processing thread."""
        self.running = False
        if self.burnout_thread:
            self.burnout_thread.join()

    def check_and_reset_changes(self) -> bool:
        """Check if changes have been made and reset the flag."""
        with self.index_lock:
            changes = self.changes_made
            self.changes_made = False
            return changes

    def has_active_fades(self) -> bool:
        """Check if there are any objects currently fading."""
        with self.index_lock:
            return len(self.active_fades) > 0