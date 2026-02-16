# File: rgb_matrix_lib/background.py

import numpy as np
from typing import Optional
from .debug import debug, Level, Component
from .sprite import MatrixSprite, SpriteManager


class BackgroundState:
    """Tracks the active background's viewport and cel state."""

    def __init__(self, sprite: MatrixSprite):
        self.sprite = sprite          # Reference to the sprite template
        self.offset_x = 0             # Viewport X offset into pattern
        self.offset_y = 0             # Viewport Y offset into pattern
        self.current_cel = 0          # Which animation cel is displayed
        self._cached_viewport: Optional[np.ndarray] = None
        self._cache_key: Optional[tuple] = None  # (offset_x, offset_y, current_cel)

    def _invalidate_cache(self):
        """Invalidate the cached viewport."""
        self._cached_viewport = None
        self._cache_key = None

    def get_viewport(self, view_width: int = 64, view_height: int = 64) -> np.ndarray:
        """
        Extract tiled viewport from current cel with intensity applied.
        Uses integer math for performance. Returns a COPY safe for modification.
        Results are cached until offset or cel changes.
        """
        cache_key = (self.offset_x, self.offset_y, self.current_cel, view_width, view_height)
        if self._cached_viewport is not None and self._cache_key == cache_key:
            return self._cached_viewport.copy()

        color_buffer = self.sprite.get_cel_buffer(self.current_cel)
        intensity_buffer = self.sprite.get_cel_intensity(self.current_cel)

        # Tiled index calculation - handles wrapping for patterns larger or smaller than viewport
        y_indices = (np.arange(view_height) + self.offset_y) % self.sprite.height
        x_indices = (np.arange(view_width) + self.offset_x) % self.sprite.width

        # Extract views using advanced indexing
        color_view = color_buffer[np.ix_(y_indices, x_indices)].astype(np.uint16)
        intensity_view = intensity_buffer[np.ix_(y_indices, x_indices)].astype(np.uint16)

        # Apply intensity with integer math: (RGB * intensity) // 100
        scaled = (color_view * intensity_view[:, :, np.newaxis]) // 100
        result = scaled.astype(np.uint8)

        # Cache the result
        self._cached_viewport = result
        self._cache_key = cache_key

        return result.copy()

    def get_viewport_region(self, start_x: int, start_y: int, end_x: int, end_y: int,
                            view_width: int = 64, view_height: int = 64) -> np.ndarray:
        """
        Extract a sub-region from the viewport. Uses cached full viewport if available.
        Returns the region as a numpy array slice.
        
        Args:
            start_x, start_y: Top-left corner of region (in display coordinates)
            end_x, end_y: Bottom-right corner exclusive (in display coordinates)
            view_width, view_height: Full viewport dimensions
        """
        viewport = self.get_viewport(view_width, view_height)
        return viewport[start_y:end_y, start_x:end_x]

    def nudge(self, dx: int, dy: int, cel_index: Optional[int] = None):
        """
        Shift viewport by relative amount.
        
        Auto-advances cel if cel_index not specified.
        Pass explicit cel_index to hold on a specific frame.
        """
        self.offset_x += dx
        self.offset_y += dy
        self._invalidate_cache()

        if cel_index is not None:
            self.set_cel(cel_index)
        else:
            self.advance_cel()

    def set_offset(self, x: int, y: int, cel_index: Optional[int] = None):
        """
        Set viewport to absolute position.
        
        Auto-advances cel if cel_index not specified.
        Pass explicit cel_index to hold on a specific frame.
        """
        self.offset_x = x
        self.offset_y = y
        self._invalidate_cache()

        if cel_index is not None:
            self.set_cel(cel_index)
        else:
            self.advance_cel()

    def advance_cel(self):
        """Advance to next cel, wrapping to 0."""
        old_cel = self.current_cel
        self.current_cel = (self.current_cel + 1) % self.sprite.cel_count
        if old_cel != self.current_cel:
            self._invalidate_cache()

    def set_cel(self, cel_index: int):
        """Jump to specific cel."""
        if 0 <= cel_index < self.sprite.cel_count:
            if self.current_cel != cel_index:
                self._invalidate_cache()
            self.current_cel = cel_index


class BackgroundManager:
    """Manages the active background layer."""

    def __init__(self, sprite_manager: SpriteManager):
        self.sprite_manager = sprite_manager  # Reference to get sprite templates
        self.active: Optional[BackgroundState] = None
        self._active_sprite_name: Optional[str] = None  # Track which sprite is the background

    def set_background(self, sprite_name: str, cel_index: int = 0) -> bool:
        """
        Activate a sprite as the background.
        Returns True on success, False if sprite not found.
        """
        template = self.sprite_manager.get_template(sprite_name)
        if template is None:
            debug(f"Background sprite '{sprite_name}' not found", Level.ERROR, Component.SYSTEM)
            return False

        self.active = BackgroundState(template)
        self.active.current_cel = cel_index
        self._active_sprite_name = sprite_name
        debug(f"Background set to sprite '{sprite_name}' cel {cel_index} "
              f"({template.width}x{template.height})", Level.INFO, Component.SYSTEM)
        return True

    def hide_background(self):
        """Deactivate background (returns to black). Template still exists for reactivation."""
        if self.active:
            debug(f"Background hidden (was '{self._active_sprite_name}')", Level.INFO, Component.SYSTEM)
        self.active = None
        # Don't clear _active_sprite_name so we could potentially track what was last used

    def nudge(self, dx: int, dy: int, cel_index: Optional[int] = None):
        """Shift background viewport. Auto-advances cel unless cel_index specified."""
        if self.active:
            self.active.nudge(dx, dy, cel_index)
            debug(f"Background nudged by ({dx}, {dy})" +
                  (f" to cel {cel_index}" if cel_index is not None else " (auto-advance)"),
                  Level.DEBUG, Component.SYSTEM)

    def set_offset(self, x: int, y: int, cel_index: Optional[int] = None):
        """Set absolute background viewport position. Auto-advances cel unless cel_index specified."""
        if self.active:
            self.active.set_offset(x, y, cel_index)
            debug(f"Background offset set to ({x}, {y})" +
                  (f" cel {cel_index}" if cel_index is not None else " (auto-advance)"),
                  Level.DEBUG, Component.SYSTEM)

    def get_viewport(self, view_width: int = 64, view_height: int = 64) -> Optional[np.ndarray]:
        """Get current viewport, or None if no background."""
        if self.active:
            return self.active.get_viewport(view_width, view_height)
        return None

    def get_viewport_region(self, start_x: int, start_y: int, end_x: int, end_y: int,
                            view_width: int = 64, view_height: int = 64) -> Optional[np.ndarray]:
        """Get a sub-region of the viewport, or None if no background."""
        if self.active:
            return self.active.get_viewport_region(start_x, start_y, end_x, end_y,
                                                    view_width, view_height)
        return None

    def has_background(self) -> bool:
        """Check if a background is active."""
        return self.active is not None

    def on_sprite_disposed(self, sprite_name: str):
        """Called when a sprite template is disposed. Hides background if it used that sprite."""
        if self._active_sprite_name == sprite_name:
            debug(f"Background sprite '{sprite_name}' was disposed, hiding background",
                  Level.INFO, Component.SYSTEM)
            self.active = None
            self._active_sprite_name = None