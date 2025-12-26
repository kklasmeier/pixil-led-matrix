from queue import PriorityQueue
from threading import Thread, Lock
from typing import List, Tuple, TYPE_CHECKING
from enum import Enum
import time

class ShapeType(Enum):
    POINT = 1
    LINE = 2
    RECTANGLE = 3
    CIRCLE = 4
    POLYGON = 5
    ELLIPSE = 6
    ARC = 7  # Added arc support

class Region:
    def __init__(self, shape_type: ShapeType, bounds: tuple):
        self.shape_type = shape_type
        self.bounds = bounds

class DrawingObject:
    def __init__(self, removal_time: float, region: Region, points: List[Tuple[int, int]]):
        self.removal_time = removal_time
        self.region = region
        self.points = points

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

    def __init__(self, api: "RGB_Api"):  # Forward reference
        self.api = api
        self.burnout_queue = PriorityQueue()
        self.burnout_thread = None
        self.running = True
        self.pixel_index = {}  # (x, y) -> [(DrawingObject, removal_time), ...]
        self.index_lock = Lock()
        self.changes_made = False  # Flag to track if burnouts have made changes

    def start(self):
        if self.burnout_thread is None:
            self.burnout_thread = Thread(target=self._process_burnouts)
            self.burnout_thread.daemon = True
            self.burnout_thread.start()

    def _process_burnouts(self):
        while self.running:
            try:
                if not self.burnout_queue.empty():
                    current_time = time.time()
                    obj = self.burnout_queue.queue[0]
                    if obj.is_expired(current_time):
                        self.burnout_queue.get_nowait()
                        self._clear_object(obj)
                    else:
                        time.sleep(self.BURNOUT_WAKE_INTERVAL)
                else:
                    time.sleep(self.BURNOUT_WAKE_INTERVAL)
            except Exception as e:
                from .debug import debug, Level, Component
                debug(f"Error in burnout thread: {e}", Level.ERROR, Component.SYSTEM)
                time.sleep(self.BURNOUT_WAKE_INTERVAL)

    def add_object(self, shape_type: ShapeType, bounds: tuple, points: List[Tuple[int, int]], duration_ms: float):
        removal_time = time.time() + (duration_ms / 1000.0)
        region = Region(shape_type, bounds)
        obj = DrawingObject(removal_time, region, points)
        self.burnout_queue.put(obj)
        with self.index_lock:
            for x, y in points:
                if (x, y) not in self.pixel_index:
                    self.pixel_index[(x, y)] = []
                self.pixel_index[(x, y)].append((obj, removal_time))

    def _clear_object(self, obj: DrawingObject):
        """
        Clear an expired drawing object by setting its pixels to black.
        If other objects use the same pixels with later expiry times, preserve those pixels.
        """
        current_time = time.time()
        points_to_clear = obj.get_points()
        pixels_changed = False  # Track if any pixels were actually changed
        
        with self.index_lock:
            for x, y in points_to_clear:
                entries = self.pixel_index.get((x, y), [])
                if not entries or max(t for _, t in entries) <= current_time:
                    self.api._draw_to_buffers(x, y, 0, 0, 0)
                    pixels_changed = True  # Mark that pixels were changed
        
        with self.index_lock:
            for x, y in points_to_clear:
                if (x, y) in self.pixel_index:
                    self.pixel_index[(x, y)] = [(o, t) for o, t in self.pixel_index[(x, y)] if o != obj]
                    if not self.pixel_index[(x, y)]:
                        del self.pixel_index[(x, y)]

        if pixels_changed:
            self.changes_made = True  # Set the flag if any pixels were changed

    def clear_all(self):
        while not self.burnout_queue.empty():
            self.burnout_queue.get_nowait()
        with self.index_lock:
            self.pixel_index.clear()

    def stop(self):
        self.running = False
        if self.burnout_thread:
            self.burnout_thread.join()

    def check_and_reset_changes(self):
        """Check if changes have been made and reset the flag."""
        with self.index_lock:  # Use lock for thread safety
            changes = self.changes_made
            self.changes_made = False
            return changes