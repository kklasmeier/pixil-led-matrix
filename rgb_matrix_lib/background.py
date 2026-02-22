# File: rgb_matrix_lib/background.py

import numpy as np
from typing import Optional, Dict
from .debug import debug, Level, Component
from .utils import TRANSPARENT_COLOR


class BackgroundLayerState:
    """State for a single background layer."""
    __slots__ = ['sprite_name', 'offset_x', 'offset_y', 'cel_index', 'visible']

    def __init__(self, sprite_name: str, cel_index: int = 0):
        self.sprite_name = sprite_name
        self.offset_x = 0
        self.offset_y = 0
        self.cel_index = cel_index
        self.visible = True


class BackgroundManager:
    """
    Manages multiple background layers composited behind the drawing buffer.

    Rendering order (bottom to top):
        1. Transparent base (0, 0, 1)
        2. Background layer 0
        3. Background layer 1
        4. ... (ascending layer number)
        5. Drawing buffer (managed by api.py)
        6. Sprites (managed by api.py)

    Each layer independently stores a sprite reference, scroll offset,
    current cel, and visibility flag. Layers are composited bottom-up;
    transparent pixels (0, 0, 1) in higher layers let lower layers show
    through.
    """

    def __init__(self, sprite_manager):
        self.sprite_manager = sprite_manager
        self._layers: Dict[int, BackgroundLayerState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_background(self, sprite_name: str, cel_index: int = 0, layer: int = 0) -> bool:
        """
        Activate a sprite as a background layer.

        If the layer already has a background assigned, replace it (swap the
        sprite reference, reset offset to 0,0, set the cel). This lets
        callers change what a layer shows without hide + re-set.

        Args:
            sprite_name: Name of a defined sprite template.
            cel_index:   Initial cel (default 0).
            layer:       Layer number (default 0). Must be >= 0.

        Returns:
            True on success, False if sprite not found or invalid layer.
        """
        if layer < 0:
            debug(f"Background layer number must be >= 0, got {layer}", Level.ERROR, Component.SYSTEM)
            return False

        template = self.sprite_manager.get_template(sprite_name)
        if template is None:
            debug(f"Background sprite '{sprite_name}' not found", Level.ERROR, Component.SYSTEM)
            return False

        if cel_index >= template.cel_count:
            debug(f"Cel index {cel_index} out of range for sprite '{sprite_name}' "
                  f"(has {template.cel_count} cels)", Level.ERROR, Component.SYSTEM)
            return False

        # Create or replace the layer state
        state = BackgroundLayerState(sprite_name, cel_index)
        self._layers[layer] = state

        debug(f"Background layer {layer} set to sprite '{sprite_name}' cel {cel_index}",
              Level.INFO, Component.SYSTEM)
        return True

    def hide_background(self, layer: Optional[int] = None):
        """
        Hide a background layer (preserves state for reactivation).

        Args:
            layer: Layer to hide. Defaults to 0 for backward compatibility.
                   If no argument is provided, only layer 0 is hidden.
        """
        target = 0 if layer is None else layer

        if target not in self._layers:
            debug(f"Background layer {target} does not exist, nothing to hide",
                  Level.WARNING, Component.SYSTEM)
            return

        self._layers[target].visible = False
        debug(f"Background layer {target} hidden", Level.INFO, Component.SYSTEM)

    def hide_all(self):
        """Hide all background layers (preserves state)."""
        for layer_num, state in self._layers.items():
            state.visible = False
        debug("All background layers hidden", Level.INFO, Component.SYSTEM)

    def destroy_all(self):
        """Destroy all background layer state. Called by dispose_all_sprites."""
        self._layers.clear()
        debug("All background layer state destroyed", Level.INFO, Component.SYSTEM)

    def nudge(self, dx: int, dy: int, cel_index: Optional[int] = None, layer: int = 0):
        """
        Shift background offset relative to current position.

        Args:
            dx, dy:    Relative shift (positive or negative).
            cel_index: If omitted, auto-advance cel. If specified, hold on that cel.
            layer:     Layer number (default 0).
        """
        if layer not in self._layers:
            debug(f"Background layer {layer} does not exist for nudge",
                  Level.ERROR, Component.SYSTEM)
            return

        state = self._layers[layer]
        state.offset_x += dx
        state.offset_y += dy
        self._update_cel(state, cel_index)

        debug(f"Background layer {layer} nudged by ({dx},{dy}) -> offset ({state.offset_x},{state.offset_y}), "
              f"cel {state.cel_index}", Level.TRACE, Component.SYSTEM)

    def set_offset(self, x: int, y: int, cel_index: Optional[int] = None, layer: int = 0):
        """
        Set absolute background offset position.

        Args:
            x, y:      Absolute offset.
            cel_index: If omitted, auto-advance cel. If specified, hold on that cel.
            layer:     Layer number (default 0).
        """
        if layer not in self._layers:
            debug(f"Background layer {layer} does not exist for set_offset",
                  Level.ERROR, Component.SYSTEM)
            return

        state = self._layers[layer]
        state.offset_x = x
        state.offset_y = y
        self._update_cel(state, cel_index)

        debug(f"Background layer {layer} offset set to ({x},{y}), cel {state.cel_index}",
              Level.TRACE, Component.SYSTEM)

    def has_background(self) -> bool:
        """Return True if any background layer is visible."""
        return any(s.visible for s in self._layers.values())

    def get_viewport(self, width: int, height: int) -> np.ndarray:
        """
        Composite all visible background layers into a single viewport buffer.

        The buffer is built bottom-up: layer 0 first, then layer 1 on top,
        etc. Transparent pixels (0, 0, 1) in higher layers let lower layers
        show through.

        Args:
            width:  Display width (64).
            height: Display height (64).

        Returns:
            np.ndarray of shape (height, width, 3) with composited background.
            Pixels where no layer drew anything will be TRANSPARENT_COLOR (0,0,1).
        """
        # Transparent sentinel as numpy array for fast comparison
        tc = np.array(TRANSPARENT_COLOR, dtype=np.uint8)

        # Start with a fully transparent base
        viewport = np.full((height, width, 3), tc, dtype=np.uint8)

        # Iterate layers in ascending order
        for layer_num in sorted(self._layers.keys()):
            state = self._layers[layer_num]
            if not state.visible:
                continue

            template = self.sprite_manager.get_template(state.sprite_name)
            if template is None:
                debug(f"Background layer {layer_num}: sprite '{state.sprite_name}' template missing",
                      Level.WARNING, Component.SYSTEM)
                continue

            layer_buf = self._render_layer(template, state, width, height)

            # Overlay: only paint non-transparent pixels from this layer
            # A pixel is non-transparent if ANY channel differs from the sentinel
            mask = np.any(layer_buf != tc, axis=2)
            viewport[mask] = layer_buf[mask]

        return viewport

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_cel(self, state: BackgroundLayerState, cel_index: Optional[int]):
        """Auto-advance or explicitly set the cel on a layer state."""
        template = self.sprite_manager.get_template(state.sprite_name)
        if template is None:
            return

        if cel_index is not None:
            # Explicit cel — hold
            state.cel_index = cel_index % template.cel_count
        else:
            # Auto-advance
            state.cel_index = (state.cel_index + 1) % template.cel_count

    def _render_layer(self, template, state: BackgroundLayerState, width: int, height: int) -> np.ndarray:
        """
        Render a single background layer into a (height, width, 3) buffer
        by tiling the sprite with the current offset applied.

        Uses vectorized numpy operations for performance:
        1. Build coordinate index arrays for the tiled+offset lookup
        2. Gather all pixels in one indexing operation
        3. Apply intensity scaling with vectorized multiply
        4. Fix any pixels that accidentally land on the sentinel value
        """
        cel_buf = template.get_cel_buffer(state.cel_index)
        cel_int = template.get_cel_intensity(state.cel_index)
        sp_h, sp_w = cel_buf.shape[:2]

        # Build source coordinate arrays: each display pixel maps to a sprite pixel
        # via (display_coord + offset) % sprite_size
        # arange(width) -> [0, 1, 2, ... 63], add offset, mod sprite width
        src_x = (np.arange(width)  + state.offset_x) % sp_w   # shape (width,)
        src_y = (np.arange(height) + state.offset_y) % sp_h   # shape (height,)

        # Use meshgrid indexing to gather the full 64x64 tile in one shot
        # src_y[:, None] broadcasts to (height, width) indexing rows
        # src_x[None, :] broadcasts to (height, width) indexing cols
        result = cel_buf[src_y[:, None], src_x[None, :]].copy()  # shape (height, width, 3)

        # Gather the intensity values the same way
        intensity = cel_int[src_y[:, None], src_x[None, :]]      # shape (height, width), dtype uint8

        # Build a mask of pixels that need intensity scaling (intensity != 100)
        needs_scaling = intensity != 100

        if np.any(needs_scaling):
            # Scale only the pixels that need it
            # Convert to float32 for the multiply, then back to uint8
            scale = intensity[needs_scaling].astype(np.float32) / 100.0  # shape (N,)
            pixels = result[needs_scaling].astype(np.float32)            # shape (N, 3)
            pixels[:, 0] *= scale
            pixels[:, 1] *= scale
            pixels[:, 2] *= scale
            result[needs_scaling] = pixels.astype(np.uint8)

        # Guard: if any scaled pixel accidentally landed on the sentinel (0,0,1),
        # nudge it to (0,0,0) so it doesn't get treated as transparent.
        # This is extremely rare (only happens if the source pixel had R=0,G=0
        # and intensity scaling brought B to exactly 1).
        tc = np.array(TRANSPARENT_COLOR, dtype=np.uint8)
        sentinel_hits = np.all(result == tc, axis=2) & needs_scaling
        if np.any(sentinel_hits):
            result[sentinel_hits] = (0, 0, 0)

        return result