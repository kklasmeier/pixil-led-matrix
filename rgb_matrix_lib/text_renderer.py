# File: rgb_matrix_lib/text_renderer.py
from PIL import Image, ImageDraw
from typing import Dict, Tuple, Optional
from .fonts import get_font_manager, FontError
from .text_effects import TextEffect, EffectModifier, validate_effect_modifier
from .bitmap_font import BitmapFontAdapter
import time
import math
import random

class TextBounds:
    """Represents the bounding box of rendered text"""
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class TextRenderer:
    """Handles text rendering and coordinate tracking"""
    
    def __init__(self, api):
        self._text_bounds: Dict[Tuple[int, int], TextBounds] = {}
        self._api = api

    def _clear_tracking(self, x: int, y: int) -> None:
        """Clear tracking for a specific coordinate"""
        if (x, y) in self._text_bounds:
            del self._text_bounds[x, y]
            
    def clear_all_tracking(self) -> None:
        """Clear all text coordinate tracking"""
        self._text_bounds.clear()
        
    def get_text_bounds(self, x: int, y: int) -> Optional[TextBounds]:
        """Get bounds of text at specific coordinates"""
        return self._text_bounds.get((x, y))

    def _is_in_frame(self) -> tuple[bool, bool]:
        """
        Check if we're currently in a frame and get its preservation mode.
        
        Returns:
            tuple[bool, bool]: (in_frame, preserve_changes)
        """
        if hasattr(self._api, 'frame_mode'):
            in_frame = self._api.frame_mode
            preserve_changes = self._api.preserve_frame_changes if in_frame else False
            return in_frame, preserve_changes
        return False, False

    def _frame_aware_begin(self, preserve: bool = True) -> bool:
        """
        Begin a frame if not already in one, or handle existing frame state.
        
        Args:
            preserve: Whether to preserve existing content
            
        Returns:
            bool: True if a new frame was started, False if already in a frame
        """
        in_frame, frame_preserve = self._is_in_frame()
        
        if not in_frame:
            # Not in a frame, start a new one
            self._api.begin_frame(preserve)
            return True
        elif frame_preserve:
            # In a preserved frame - don't start a new one
            # We'll handle animation steps differently
            return False
        else:
            # In a non-preserved frame - don't start a new one
            return False
        
    def _frame_aware_end(self, frame_started: bool):
        """
        End a frame if one was started, possibly restore frame state.
        
        Args:
            frame_started: Whether a new frame was started by _frame_aware_begin
        """
        in_frame, preserve_changes = self._is_in_frame()
        
        if frame_started:
            # If we started a frame, end it
            self._api.end_frame()
        elif in_frame and preserve_changes:
            # If in a preserved frame that we didn't start, DO NOT restore state here
            # We'll handle animation steps differently
            pass

    def _frame_aware_render(self, render_func, *args, **kwargs):
        """
        Wrapper to handle frame-aware rendering for any effect method.
        
        Args:
            render_func: Function that performs the actual rendering
            *args, **kwargs: Arguments to pass to the render function
        """
        # Check current frame state
        in_frame, preserve_changes = self._is_in_frame()
        
        # Start a frame if needed
        frame_started = self._frame_aware_begin(True)
        
        try:
            # Call the render function
            render_func(*args, **kwargs)
        finally:
            # End frame if we started one, or restore state
            self._frame_aware_end(frame_started)

    def _render_normal(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int]) -> None:
        """Render text normally (all at once)."""
        # Define the actual rendering function
        def render():
            pixels = img.load()
            matrix_width = self._api.matrix.width
            matrix_height = self._api.matrix.height

            if pixels is None:
                # If pixels is None, skip rendering
                return
            
            for y_offset in range(img.height):
                plot_y = y + y_offset
                if 0 <= plot_y < matrix_height:
                    for x_offset in range(img.width):
                        plot_x = x + x_offset
                        if 0 <= plot_x < matrix_width and pixels[x_offset, y_offset] != (0, 0, 0):
                            self._api.plot(plot_x, plot_y, color)
        
        # Use our frame-aware wrapper to handle the rendering
        self._frame_aware_render(render)
        
    def render_text(self, x: int, y: int, text: str, font_name: str, font_size: int, 
                    color: Tuple[int, int, int], effect: TextEffect = TextEffect.NORMAL,
                    modifier: Optional[EffectModifier] = None) -> None:
        """
        Render text on the LED matrix.
        
        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to render
            font_name: Name of font to use
            font_size: Size of font in pixels
            color: RGB tuple (r, g, b)
            effect: Text effect to apply
            modifier: Effect modifier (if applicable)
        """
        # Get font from the manager
        font = get_font_manager().get_font(font_name, font_size)
        
        # Check if we're using the bitmap font
        using_bitmap_font = isinstance(font, BitmapFontAdapter)
        
        # Check current frame state
        in_frame, preserve_changes = self._is_in_frame()
        
        # If we're in a non-preserved frame, override to NORMAL effect
        original_effect = effect
        if in_frame and not preserve_changes:
            effect = TextEffect.NORMAL
            # Log if effect was overridden
            if original_effect != TextEffect.NORMAL:
                from .debug import debug, Level, Component
                debug(f"Text effect {original_effect.name} overridden to NORMAL in non-preserved frame", 
                    Level.DEBUG, Component.SYSTEM)
        
        if using_bitmap_font:
            # Get text dimensions from bitmap font
            text_width, text_height = font.getsize(text)
            
            # Get bitmap font image
            bitmap_manager = font.font_manager
            img = bitmap_manager.create_text_image(text)
            if img is None:
                # Handle error - create minimal image
                img = Image.new('RGB', (1, 5), color=(0, 0, 0))
                text_width, text_height = 1, 5
        else:
            # Existing code for PIL fonts
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            img = Image.new('RGB', (int(text_width), int(text_height)), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((-bbox[0], -bbox[1]), text, font=font, fill=(255, 255, 255))
        
        # Update text bounds tracking
        self._text_bounds[(x, y)] = TextBounds(x, y, int(text_width), int(text_height))
        
        # Apply the selected effect
        if effect == TextEffect.NORMAL:
            self._render_normal(img, x, y, color)
        elif effect == TextEffect.TYPE:
            if modifier is None:
                modifier = EffectModifier.MEDIUM
            validate_effect_modifier(effect, modifier)
            
            if using_bitmap_font:
                # For bitmap fonts, we use a direct rendering approach for TYPE
                self._render_bitmap_type(text, x, y, color, modifier, font)
            else:
                # Use existing implementation for PIL fonts
                self._render_type(img, x, y, text, color, modifier, font_name, font_size)
        elif effect == TextEffect.SCAN:
            self._render_scan(img, x, y, color)
        elif effect == TextEffect.SLIDE:
            if modifier is None:
                modifier = EffectModifier.LEFT
            validate_effect_modifier(effect, modifier)
            self._render_slide(img, x, y, color, modifier)
        elif effect == TextEffect.DISSOLVE:
            if modifier is None:
                modifier = EffectModifier.IN
            self._render_dissolve(img, x, y, color, modifier)
        elif effect == TextEffect.WIPE:
            if modifier is None:
                modifier = EffectModifier.IN_LEFT  # or another appropriate default
            self._render_wipe(img, x, y, color, modifier)
        else:
            raise NotImplementedError(f"Effect {effect.name} not yet implemented")

    def _render_bitmap_type(self, text: str, x: int, y: int, color: Tuple[int, int, int], 
                        modifier: EffectModifier, font_adapter: BitmapFontAdapter) -> None:
        """Render bitmap font text with typewriter effect."""
        # Check frame state
        in_frame, preserve_changes = self._is_in_frame()
        
        # If in a non-preserved frame, fall back to normal rendering
        if in_frame and not preserve_changes:
            # Create a temporary image for the whole text
            bitmap_manager = font_adapter.font_manager
            img = bitmap_manager.create_text_image(text)
            if img is not None:
                return self._render_normal(img, x, y, color)
            return
        
        bitmap_manager = font_adapter.font_manager
        
        # Determine typing speed
        if modifier == EffectModifier.SLOW:
            char_delay = 0.2
        elif modifier == EffectModifier.FAST:
            char_delay = 0.05
        else:  # MEDIUM
            char_delay = 0.1
        
        current_x = x
        cursor_rgb = (0, 255, 255)  # Cyan cursor
        
        for i, char in enumerate(text):
            # Get character bitmap
            bitmap = bitmap_manager.get_char_bitmap(char)
            if not bitmap:
                # Skip unknown characters
                current_x += 2  # Default width + spacing
                continue
            
            # Use actual width from bitmap
            char_width = len(bitmap[0])
            char_height = len(bitmap)
            y_offset = 0
            
            # Handle frame operations based on context
            if in_frame and preserve_changes:
                # End current frame to show this animation step
                self._api.end_frame()
                # Start a new preserved frame to continue animation
                self._api.begin_frame(True)
                
                # Draw character
                for py, row in enumerate(bitmap):
                    for px, pixel in enumerate(row):
                        if pixel == '1':
                            self._api.plot(current_x + px, y + y_offset + py, color)
                            
                # Draw cursor after character
                for cy in range(char_height):
                    self._api.plot(current_x + char_width, y + y_offset + cy, cursor_rgb)
            else:
                # Standard frame handling
                frame_started = self._frame_aware_begin(True)
                
                # Draw character
                for py, row in enumerate(bitmap):
                    for px, pixel in enumerate(row):
                        if pixel == '1':
                            self._api.plot(current_x + px, y + y_offset + py, color)
                            
                # Draw cursor after character
                for cy in range(char_height):
                    self._api.plot(current_x + char_width, y + y_offset + cy, cursor_rgb)
                    
                self._frame_aware_end(frame_started)
            
            # Add delay for animation timing
            time.sleep(char_delay)
            
            # Clear cursor
            if in_frame and preserve_changes:
                # End current frame
                self._api.end_frame()
                # Start new preserved frame
                self._api.begin_frame(True)
                
                # Clear cursor
                for cy in range(char_height):
                    self._api.plot(current_x + char_width, y + y_offset + cy, (0, 0, 0))
            else:
                frame_started = self._frame_aware_begin(True)
                
                # Clear cursor
                for cy in range(char_height):
                    self._api.plot(current_x + char_width, y + y_offset + cy, (0, 0, 0))
                    
                self._frame_aware_end(frame_started)
            
            # Move to next character position
            current_x += char_width + 1  # Add spacing
            
                        
    def clear_text(self, x: int, y: int) -> None:
        """Clear text at specified coordinates."""
        bounds = self.get_text_bounds(x, y)
        if bounds:
            # Define the actual clearing function
            def clear():
                matrix_width = self._api.matrix.width
                matrix_height = self._api.matrix.height
                
                for py in range(bounds.height):
                    plot_y = bounds.y + py
                    if 0 <= plot_y < matrix_height:
                        for px in range(bounds.width):
                            plot_x = bounds.x + px
                            if 0 <= plot_x < matrix_width:
                                self._api.plot(plot_x, plot_y, (0, 0, 0))  # Black to clear
            
            # Use our frame-aware wrapper to handle the clearing
            self._frame_aware_render(clear)
            
            self._clear_tracking(x, y)

    def _render_type(self, img: Image.Image, x: int, y: int, text: str, color: Tuple[int, int, int], 
                    modifier: EffectModifier, font_name: str, font_size: int) -> None:
        """Render text with typewriter effect."""
        # Check frame state
        in_frame, preserve_changes = self._is_in_frame()
        
        # If in a non-preserved frame, fall back to normal rendering
        if in_frame and not preserve_changes:
            return self._render_normal(img, x, y, color)
        
        # Get font and set up parameters
        font = get_font_manager().get_font(font_name, font_size)
        
        # Check if this is a bitmap font
        if isinstance(font, BitmapFontAdapter):
            # Use the dedicated bitmap rendering method
            return self._render_bitmap_type(text, x, y, color, modifier, font)
        
        if modifier == EffectModifier.SLOW:
            char_delay = 0.2
        elif modifier == EffectModifier.FAST:
            char_delay = 0.05
        else:  # MEDIUM
            char_delay = 0.1
        
        current_text = ""
        cursor_rgb = (0, 255, 255)  # Cyan cursor
        
        for char in text:
            current_text += char
            bbox = font.getbbox(current_text)
            char_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # For each animation step in a preserved frame, we need to:
            # 1. Call end_frame() to show the current state
            # 2. Call begin_frame(true) to start a new preserved frame
            # This maintains the overall frame while showing animation steps
            
            if in_frame and preserve_changes:
                # End current frame to show this animation step
                self._api.end_frame()
                # Start a new preserved frame to continue animation
                self._api.begin_frame(True)
                
                # Draw directly in the new frame
                temp_img = Image.new('RGB', (int(char_width), int(text_height)), color=(0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)
                temp_draw.text((0, 0), current_text, font=font, fill=(255, 255, 255))
                pixels = temp_img.load()
                
                for py in range(int(text_height)):
                    for px in range(int(char_width)):
                        if pixels is not None and pixels[px, py] != (0, 0, 0):
                            self._api.plot(x + px, y + py, color)
                    
                    # Draw cursor at the end of text
                    self._api.plot(x + int(char_width), y + py, cursor_rgb)
            else:
                # Not in a frame or just started our own frame
                # Use standard frame-aware rendering
                frame_started = self._frame_aware_begin(True)
                
                temp_img = Image.new('RGB', (int(char_width), int(text_height)), color=(0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)
                temp_draw.text((0, 0), current_text, font=font, fill=(255, 255, 255))
                pixels = temp_img.load()
                
                for py in range(int(text_height)):
                    for px in range(int(char_width)):
                        if pixels is not None and pixels[px, py] != (0, 0, 0):
                            self._api.plot(x + px, y + py, color)
                    
                    # Draw cursor at the end of text
                    self._api.plot(x + int(char_width), y + py, cursor_rgb)
                
                self._frame_aware_end(frame_started)
            
            # Add delay for animation timing
            time.sleep(char_delay)
            
            # Clear cursor (same pattern as above)
            if in_frame and preserve_changes:
                self._api.end_frame()
                self._api.begin_frame(True)
                
                for cy in range(int(text_height)):
                    self._api.plot(x + char_width, y + cy, (0, 0, 0))
            else:
                frame_started = self._frame_aware_begin(True)
                
                for cy in range(int(text_height)):
                    self._api.plot(x + char_width, y + cy, (0, 0, 0))
                    
                self._frame_aware_end(frame_started)
                
    def _render_scan(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int]) -> None:
        """Render text with scan effect (pixel-by-pixel)."""
        # Check frame state
        in_frame, preserve_changes = self._is_in_frame()
        
        # If in a non-preserved frame, fall back to normal rendering
        if in_frame and not preserve_changes:
            return self._render_normal(img, x, y, color)
        
        pixels = img.load()
        
        # Gather all lit pixels
        if pixels is None:
            lit_pixels = []
        else:
            lit_pixels = [(px, py) for py in range(img.height) for px in range(img.width) 
                        if pixels[px, py] != (0, 0, 0)]
        
        # Process pixels one by one with delay
        for px, py in lit_pixels:
            # Handle frame operations based on context
            if in_frame and preserve_changes:
                # End current frame to show this animation step
                self._api.end_frame()
                # Start a new preserved frame to continue animation
                self._api.begin_frame(True)
                
                # Plot this pixel
                self._api.plot(x + px, y + py, color)
            else:
                # Standard frame handling
                frame_started = self._frame_aware_begin(True)
                
                # Plot this pixel
                self._api.plot(x + px, y + py, color)
                    
                self._frame_aware_end(frame_started)
            
            # Add a small delay between pixels
            time.sleep(0.001)

    def _render_slide(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int], 
                    modifier: EffectModifier) -> None:
        """Render text with slide effect."""
        # Check frame state
        in_frame, preserve_changes = self._is_in_frame()
        
        # If in a non-preserved frame, fall back to normal rendering
        if in_frame and not preserve_changes:
            return self._render_normal(img, x, y, color)
        
        matrix_width = self._api.matrix.width
        matrix_height = self._api.matrix.height
        pixels = img.load()
        if pixels is None:
            lit_pixels = []
        else:
            lit_pixels = [(px, py) for py in range(img.height) for px in range(img.width) 
                        if pixels is not None and pixels[px, py] != (0, 0, 0)]
        
        # Calculate start and end positions based on direction
        if modifier == EffectModifier.LEFT:
            start_x, start_y = matrix_width, y
            final_x, final_y = x, y
        elif modifier == EffectModifier.RIGHT:
            start_x, start_y = -img.width, y
            final_x, final_y = x, y
        elif modifier == EffectModifier.UP:
            start_x, start_y = x, matrix_height
            final_x, final_y = x, y
        else:  # DOWN
            start_x, start_y = x, -img.height
            final_x, final_y = x, y
        
        duration = 1.0
        frames = 40
        active_pixels = set()
        
        for frame in range(frames + 1):
            progress = frame / frames
            eased_progress = 0.5 * (1 - math.cos(math.pi * progress))
            current_x = int(start_x + (final_x - start_x) * eased_progress)
            current_y = int(start_y + (final_y - start_y) * eased_progress)
            
            # Calculate new pixels for this frame
            new_active_pixels = {(current_x + px, current_y + py) for px, py in lit_pixels 
                                if 0 <= current_x + px < matrix_width and 
                                0 <= current_y + py < matrix_height}
            
            # Different handling based on frame state
            if in_frame and preserve_changes:
                # End current frame to show this animation step
                self._api.end_frame()
                # Start a new preserved frame to continue animation
                self._api.begin_frame(True)
                
                # Clear pixels that are no longer needed
                pixels_to_clear = active_pixels - new_active_pixels
                for px, py in pixels_to_clear:
                    self._api.plot(px, py, (0, 0, 0))
                
                # Draw new pixels
                pixels_to_draw = new_active_pixels - active_pixels
                for px, py in pixels_to_draw:
                    self._api.plot(px, py, color)
            else:
                # Not in a frame or just started our own frame
                frame_started = self._frame_aware_begin(True)
                
                # Clear pixels that are no longer needed
                pixels_to_clear = active_pixels - new_active_pixels
                for px, py in pixels_to_clear:
                    self._api.plot(px, py, (0, 0, 0))
                
                # Draw new pixels
                pixels_to_draw = new_active_pixels - active_pixels
                for px, py in pixels_to_draw:
                    self._api.plot(px, py, color)
                    
                self._frame_aware_end(frame_started)
            
            # Update active pixels set
            active_pixels = new_active_pixels
            
            # Add delay for animation timing
            time.sleep(duration / frames)

    def _render_dissolve(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int], 
                        modifier: EffectModifier) -> None:
        """Render text with dissolve effect."""
        # Check frame state
        in_frame, preserve_changes = self._is_in_frame()
        
        # If in a non-preserved frame, fall back to normal rendering
        if in_frame and not preserve_changes:
            return self._render_normal(img, x, y, color)
        
        pixels = img.load()
        if pixels is None:
            lit_pixels = []
        else:
            lit_pixels = [(x + px, y + py) for py in range(img.height) for px in range(img.width) 
                        if pixels[px, py] != (0, 0, 0) and 
                        0 <= x + px < self._api.matrix.width and 0 <= y + py < self._api.matrix.height]
        
        if modifier == EffectModifier.IN:
            # DISSOLVE IN
            remaining_pixels = lit_pixels.copy()
            
            while remaining_pixels:
                # Randomly select pixels to draw in this frame
                num_pixels = min(len(remaining_pixels), 5)
                to_draw = []
                
                for _ in range(num_pixels):
                    if remaining_pixels:
                        idx = random.randint(0, len(remaining_pixels) - 1)
                        to_draw.append(remaining_pixels.pop(idx))
                
                # Handle frame operations based on context
                if in_frame and preserve_changes:
                    # End current frame to show this animation step
                    self._api.end_frame()
                    # Start a new preserved frame to continue animation
                    self._api.begin_frame(True)
                    
                    # Draw selected pixels
                    for px, py in to_draw:
                        self._api.plot(px, py, color)
                else:
                    # Standard frame handling
                    frame_started = self._frame_aware_begin(True)
                    
                    # Draw selected pixels
                    for px, py in to_draw:
                        self._api.plot(px, py, color)
                        
                    self._frame_aware_end(frame_started)
                
                # Add delay for animation timing
                time.sleep(0.02)
                
        else:  # OUT
            # First render normally
            if in_frame and preserve_changes:
                # End current frame
                self._api.end_frame()
                # Start new preserved frame
                self._api.begin_frame(True)
                
                # Draw all pixels
                for px, py in lit_pixels:
                    self._api.plot(px, py, color)
            else:
                frame_started = self._frame_aware_begin(True)
                
                # Draw all pixels
                for px, py in lit_pixels:
                    self._api.plot(px, py, color)
                    
                self._frame_aware_end(frame_started)
            
            # Add delay before dissolving
            time.sleep(0.5)
            
            # Then dissolve out
            remaining_pixels = lit_pixels.copy()
            
            while remaining_pixels:
                # Randomly select pixels to clear in this frame
                num_pixels = min(len(remaining_pixels), 5)
                to_clear = []
                
                for _ in range(num_pixels):
                    if remaining_pixels:
                        idx = random.randint(0, len(remaining_pixels) - 1)
                        to_clear.append(remaining_pixels.pop(idx))
                
                # Handle frame operations based on context
                if in_frame and preserve_changes:
                    # End current frame to show this animation step
                    self._api.end_frame()
                    # Start a new preserved frame to continue animation
                    self._api.begin_frame(True)
                    
                    # Clear selected pixels
                    for px, py in to_clear:
                        self._api.plot(px, py, (0, 0, 0))
                else:
                    # Standard frame handling
                    frame_started = self._frame_aware_begin(True)
                    
                    # Clear selected pixels
                    for px, py in to_clear:
                        self._api.plot(px, py, (0, 0, 0))
                        
                    self._frame_aware_end(frame_started)
                
                # Add delay for animation timing
                time.sleep(0.02)

    def _render_wipe(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int], 
                    modifier: EffectModifier) -> None:
        """Render text with wipe effect."""
        # Check frame state
        in_frame, preserve_changes = self._is_in_frame()
        
        # If in a non-preserved frame, fall back to normal rendering
        if in_frame and not preserve_changes:
            return self._render_normal(img, x, y, color)
        
        pixels = img.load()
        if pixels is None:
            lit_pixels = []
        else:
            lit_pixels = [(x + px, y + py) for py in range(img.height) for px in range(img.width) 
                        if pixels[px, py] != (0, 0, 0) and 
                        0 <= x + px < self._api.matrix.width and 0 <= y + py < self._api.matrix.height]

        is_out = modifier in [EffectModifier.OUT_LEFT, EffectModifier.OUT_RIGHT, 
                            EffectModifier.OUT_UP, EffectModifier.OUT_DOWN]
        
        # Sort pixels based on direction
        if modifier in [EffectModifier.IN_LEFT, EffectModifier.OUT_RIGHT]:
            lit_pixels.sort(key=lambda p: p[0])
        elif modifier in [EffectModifier.IN_RIGHT, EffectModifier.OUT_LEFT]:
            lit_pixels.sort(key=lambda p: -p[0])
        elif modifier in [EffectModifier.IN_UP, EffectModifier.OUT_DOWN]:
            lit_pixels.sort(key=lambda p: p[1])
        elif modifier in [EffectModifier.IN_DOWN, EffectModifier.OUT_UP]:
            lit_pixels.sort(key=lambda p: -p[1])

        # For OUT effects, first render normally then wipe
        if is_out:
            if in_frame and preserve_changes:
                # End current frame
                self._api.end_frame()
                # Start new preserved frame
                self._api.begin_frame(True)
                
                # Draw all pixels
                for px, py in lit_pixels:
                    self._api.plot(px, py, color)
            else:
                frame_started = self._frame_aware_begin(True)
                
                # Draw all pixels
                for px, py in lit_pixels:
                    self._api.plot(px, py, color)
                    
                self._frame_aware_end(frame_started)
            
            # Add delay before wiping
            time.sleep(0.5)
            
            # Reverse for "out" effect
            lit_pixels = lit_pixels[::-1]

        total_frames = 30
        pixels_per_frame = max(1, len(lit_pixels) // total_frames)

        for i in range(0, len(lit_pixels), pixels_per_frame):
            batch_pixels = lit_pixels[i:i + pixels_per_frame]
            
            # Handle frame operations based on context
            if in_frame and preserve_changes:
                # End current frame to show this animation step
                self._api.end_frame()
                # Start a new preserved frame to continue animation
                self._api.begin_frame(True)
                
                # Process this batch of pixels
                for px, py in batch_pixels:
                    if is_out:
                        self._api.plot(px, py, (0, 0, 0))
                    else:
                        self._api.plot(px, py, color)
            else:
                # Standard frame handling
                frame_started = self._frame_aware_begin(True)
                
                # Process this batch of pixels
                for px, py in batch_pixels:
                    if is_out:
                        self._api.plot(px, py, (0, 0, 0))
                    else:
                        self._api.plot(px, py, color)
                    
                self._frame_aware_end(frame_started)
            
            # Add delay for animation timing
            time.sleep(0.02)