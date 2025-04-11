from queue import PriorityQueue
from threading import Thread, Lock
from typing import List, Tuple
from enum import Enum
import time

class ShapeType(Enum):
    POINT = 1
    LINE = 2
    RECTANGLE = 3
    CIRCLE = 4
    POLYGON = 5
    ELLIPSE = 6

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

class ThreadedBurnoutManager:
    BURNOUT_WAKE_INTERVAL = 0.01  # 10ms

    def __init__(self, api: "RGB_Api"):  # Forward reference
        self.api = api
        self.burnout_queue = PriorityQueue()
        self.burnout_thread = None
        self.running = True
        self.pixel_index = {}  # (x, y) -> [(DrawingObject, removal_time), ...]
        self.index_lock = Lock()

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
        current_time = time.time()
        points_to_clear = obj.get_points()
        with self.index_lock:
            for x, y in points_to_clear:
                entries = self.pixel_index.get((x, y), [])
                if not entries or max(t for _, t in entries) <= current_time:
                    self.api._draw_to_buffers(x, y, 0, 0, 0)
        with self.index_lock:
            for x, y in points_to_clear:
                if (x, y) in self.pixel_index:
                    self.pixel_index[(x, y)] = [(o, t) for o, t in self.pixel_index[(x, y)] if o != obj]
                    if not self.pixel_index[(x, y)]:
                        del self.pixel_index[(x, y)]

    def clear_all(self):
        while not self.burnout_queue.empty():
            self.burnout_queue.get_nowait()
        with self.index_lock:
            self.pixel_index.clear()

    def stop(self):
        self.running = False
        if self.burnout_thread:
            self.burnout_thread.join()