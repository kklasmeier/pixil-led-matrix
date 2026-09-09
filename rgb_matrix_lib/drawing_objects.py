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
        # Original and last-rendered colors, parallel to points. Keeping the
        # latter lets a covered burnout distinguish its own pixels from an
        # untracked/permanent overlay.
        self.pixel_colors = pixel_colors
        self.last_pixel_colors = list(pixel_colors) if pixel_colors is not None else None
        self.point_indexes = {point: i for i, point in enumerate(points)}

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
    # The panel cannot present object animation above 60 FPS. Running fade
    # bookkeeping at 100 Hz only steals CPU from drawing and queue handling.
    BURNOUT_WAKE_INTERVAL = 1.0 / 60.0
    
    # Optimization #5: Gamma correction for perceptual fade
    # 2.2 is standard sRGB gamma - makes fade appear more linear to human eyes
    FADE_GAMMA = 2.2

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
            tick_started = time.monotonic()
            try:
                current_time = time.time()
                
                # Process active fades
                self._update_active_fades(current_time)
                
                # Process ALL expired objects (not just one per cycle)
                while not self.burnout_queue.empty():
                    obj = self.burnout_queue.queue[0]
                    if obj.is_expired(current_time):
                        self.burnout_queue.get_nowait()
                        self._clear_object(obj)
                        # Remove from active_fades if present
                        with self.index_lock:
                            self.active_fades.discard(obj)
                    else:
                        # Queue is sorted by removal_time, so if first isn't expired, none are
                        break

                elapsed = time.monotonic() - tick_started
                time.sleep(max(0.0, self.BURNOUT_WAKE_INTERVAL - elapsed))
            except Exception as e:
                from .debug import debug, Level, Component
                debug(f"Error in burnout thread: {e}", Level.ERROR, Component.SYSTEM)
                time.sleep(self.BURNOUT_WAKE_INTERVAL)

    def _update_active_fades(self, current_time: float):
        """
        Update intensity for all actively fading objects.
        
        Optimization #4: Reduced lock scope - only lock for data structure access,
        not during pixel writes.
        """
        # Optimization #4: Quick check without lock first
        if not self.active_fades:
            return
        
        # Snapshot only the visible fade at each occupied pixel. Walking every
        # point in every fade object makes covered trail stacks increasingly
        # expensive even though none of those hidden objects can draw.
        with self.index_lock:
            visible_fades = []
            for (x, y), entries in self.pixel_index.items():
                for obj, removal_time in reversed(entries):
                    if removal_time > current_time:
                        if obj.mode == BurnoutMode.FADE:
                            point_index = obj.point_indexes.get((x, y))
                            if point_index is not None:
                                visible_fades.append((x, y, obj, point_index))
                        break
        
        pixels_updated = False

        # Most shapes use one source color for many points. Cache each object's
        # fade multiplier instead of repeating time math and pow() per pixel.
        intensity_by_object = {}
        for x, y, obj, point_index in visible_fades:
            intensity = intensity_by_object.get(obj)
            if intensity is None:
                duration = obj.removal_time - obj.start_time
                if duration <= 0:
                    continue
                progress = max(0.0, min(1.0, (current_time - obj.start_time) / duration))
                intensity = pow(1.0 - progress, self.FADE_GAMMA)
                intensity_by_object[obj] = intensity

            r, g, b = obj.pixel_colors[point_index]
            color = (int(r * intensity), int(g * intensity), int(b * intensity))

            # Registration can happen after the snapshot, so validate ownership
            # and update atomically. Covered fades remain indexed for reveal.
            with self.index_lock:
                if not self._is_pixel_owner(x, y, obj, current_time):
                    continue
                current = self.api.drawing_buffer[y, x]
                expected = obj.last_pixel_colors[point_index]
                if (
                    int(current[0]) != expected[0]
                    or int(current[1]) != expected[1]
                    or int(current[2]) != expected[2]
                ):
                    continue
                self.api._draw_to_buffers(x, y, *color)
                obj.last_pixel_colors[point_index] = color
                pixels_updated = True
        
        if pixels_updated:
            self.changes_made = True

    def _is_pixel_owner(
        self, x: int, y: int, obj: DrawingObject, current_time: Optional[float] = None
    ) -> bool:
        """Return whether obj is the most recently drawn live burnout at a pixel."""
        entries = self.pixel_index.get((x, y), [])
        if not entries:
            return False

        now = time.time() if current_time is None else current_time
        for candidate, removal_time in reversed(entries):
            if removal_time > now:
                return candidate is obj
        return False

    def _color_at(self, obj: DrawingObject, point_index: int, current_time: float) -> Tuple[int, int, int]:
        """Return an object's current color, including elapsed fade."""
        r, g, b = obj.pixel_colors[point_index]
        if obj.mode != BurnoutMode.FADE:
            return r, g, b

        duration = obj.removal_time - obj.start_time
        if duration <= 0:
            return 0, 0, 0
        progress = max(0.0, min(1.0, (current_time - obj.start_time) / duration))
        intensity = pow(1.0 - progress, self.FADE_GAMMA)
        return int(r * intensity), int(g * intensity), int(b * intensity)

    @staticmethod
    def _point_index(obj: DrawingObject, x: int, y: int) -> Optional[int]:
        """Find a pixel's parallel color index in an object."""
        return obj.point_indexes.get((x, y))

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
            pixel_colors: Original (r, g, b) values parallel to points
        """
        start_time = time.time()
        removal_time = start_time + (duration_ms / 1000.0)
        region = Region(shape_type, bounds)

        # Instant burnouts historically omitted colors. Capture them now so an
        # expired covering object can reveal another live burnout underneath.
        if pixel_colors is None:
            pixel_colors = [
                tuple(int(channel) for channel in self.api.drawing_buffer[y, x])
                for x, y in points
            ]

        obj = DrawingObject(removal_time, region, points, start_time, mode, pixel_colors)
        
        self.burnout_queue.put(obj)
        
        with self.index_lock:
            for i, (x, y) in enumerate(points):
                if (x, y) not in self.pixel_index:
                    self.pixel_index[(x, y)] = []
                self.pixel_index[(x, y)].append((obj, removal_time))

                # Drawing and registration are separate API operations. If the
                # fade thread repainted this pixel in that small gap, reassert
                # the newly registered (and therefore topmost) draw.
                current = self.api.drawing_buffer[y, x]
                color = obj.pixel_colors[i]
                if (
                    int(current[0]) != color[0]
                    or int(current[1]) != color[1]
                    or int(current[2]) != color[2]
                ):
                    self.api._draw_to_buffers(x, y, *color)
                    obj.last_pixel_colors[i] = color
            
            # Track separately if it needs active fading
            if mode == BurnoutMode.FADE:
                self.active_fades.add(obj)

    def _clear_object(self, obj: DrawingObject):
        """
        Remove an expired object. If it was visible, reveal the most recently
        drawn live burnout underneath at its current fade level.
        """
        current_time = time.time()
        points_to_clear = obj.get_points()
        pixels_changed = False

        with self.index_lock:
            for point_index, (x, y) in enumerate(points_to_clear):
                entries = self.pixel_index.get((x, y), [])
                if not entries:
                    continue

                # obj is expired at this point, so determine visibility from
                # draw order before removing it instead of live ownership.
                obj_positions = [
                    i for i, (candidate, _) in enumerate(entries) if candidate is obj
                ]
                # Rasterized outlines can contain the same coordinate more
                # than once. The first occurrence removes all entries for this
                # object; later duplicates must be harmless.
                if not obj_positions:
                    continue
                obj_position = obj_positions[-1]
                later_entries = entries[obj_position + 1:]
                was_top = not any(t > current_time for _, t in later_entries)

                expected = obj.last_pixel_colors[point_index]
                current = self.api.drawing_buffer[y, x]
                was_visible = was_top and (
                    int(current[0]) == expected[0]
                    and int(current[1]) == expected[1]
                    and int(current[2]) == expected[2]
                )

                remaining = [(o, t) for o, t in entries if o is not obj]
                if remaining:
                    self.pixel_index[(x, y)] = remaining
                else:
                    del self.pixel_index[(x, y)]

                if not was_visible:
                    continue

                underneath = next(
                    ((o, t) for o, t in reversed(remaining) if t > current_time),
                    None,
                )
                if underneath is None:
                    self.api._draw_to_buffers(x, y, 0, 0, 1)  # TRANSPARENT_COLOR
                else:
                    under_obj = underneath[0]
                    under_index = self._point_index(under_obj, x, y)
                    if under_index is None:
                        continue
                    color = self._color_at(under_obj, under_index, current_time)
                    self.api._draw_to_buffers(x, y, *color)
                    under_obj.last_pixel_colors[under_index] = color
                pixels_changed = True

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