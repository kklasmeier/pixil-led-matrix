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


    def _render_normal(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int]) -> None:
        """Render text normally (all at once)."""
        pixels = img.load()
        matrix_width = self._api.matrix.width
        matrix_height = self._api.matrix.height
        self._api.begin_frame(True)
        for y_offset in range(img.height):
            plot_y = y + y_offset
            if 0 <= plot_y < matrix_height:
                for x_offset in range(img.width):
                    plot_x = x + x_offset
                    if 0 <= plot_x < matrix_width and pixels[x_offset, y_offset] != (0, 0, 0):
                        self._api.plot(plot_x, plot_y, color)
        self._api.end_frame()
        
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
            text_width, text_height = font.getsize(text)
            
            img = Image.new('RGB', (text_width, text_height), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((0, 0), text, font=font, fill=(255, 255, 255))
        
        # Update text bounds tracking
        self._text_bounds[(x, y)] = TextBounds(x, y, text_width, text_height)
        
        # Apply the selected effect (existing code continues)
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
            self._render_dissolve(img, x, y, color, modifier)
        elif effect == TextEffect.WIPE:
            self._render_wipe(img, x, y, color, modifier)
        else:
            raise NotImplementedError(f"Effect {effect.name} not yet implemented")

    def _render_bitmap_type(self, text: str, x: int, y: int, color: Tuple[int, int, int], 
                        modifier: EffectModifier, font_adapter: BitmapFontAdapter) -> None:
        """
        Render bitmap font text with typewriter effect.
        This is optimized for bitmap fonts to avoid recreating images.
        
        Args:
            text: Text to display
            x: X coordinate
            y: Y coordinate
            color: RGB color
            modifier: Speed modifier
            font_adapter: BitmapFontAdapter instance
        """
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
            
            # Determine if this character has a descender
            is_descender = char in bitmap_manager.descenders
            
            # Calculate vertical offset for descenders
            y_offset = 0
            if is_descender:
                # No vertical offset needed in our implementation
                # since descenders just have an extra row at the bottom
                pass
            
            # Draw the character
            self._api.begin_frame(True)
            for py, row in enumerate(bitmap):
                for px, pixel in enumerate(row):
                    if pixel == '1':
                        self._api.plot(current_x + px, y + y_offset + py, color)
                        
            # Draw cursor after character
            for cy in range(char_height):
                self._api.plot(current_x + char_width, y + y_offset + cy, cursor_rgb)
                
            self._api.end_frame()
            time.sleep(char_delay)
            
            # Clear cursor
            self._api.begin_frame(True)
            for cy in range(char_height):
                self._api.plot(current_x + char_width, y + y_offset + cy, (0, 0, 0))
            self._api.end_frame()
            
            # Move to next character position
            current_x += char_width + 1  # Add spacing
            
    def clear_text(self, x: int, y: int) -> None:
        """
        Clear text at the specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        bounds = self.get_text_bounds(x, y)
        if bounds:
            matrix_width = self._api.matrix.width
            matrix_height = self._api.matrix.height
            
            self._api.begin_frame(True)
            for py in range(bounds.height):
                plot_y = bounds.y + py
                if 0 <= plot_y < matrix_height:
                    for px in range(bounds.width):
                        plot_x = bounds.x + px
                        if 0 <= plot_x < matrix_width:
                            self._api.plot(plot_x, plot_y, (0, 0, 0))  # Black to clear
            self._api.end_frame()
            
            self._clear_tracking(x, y)

    def _render_type(self, img: Image.Image, x: int, y: int, text: str, color: Tuple[int, int, int], 
                     modifier: EffectModifier, font_name: str, font_size: int) -> None:
        """Render text with typewriter effect."""
        font = get_font_manager().get_font(font_name, font_size)
        
        if modifier == EffectModifier.SLOW:
            char_delay = 0.2
        elif modifier == EffectModifier.FAST:
            char_delay = 0.05
        else:  # MEDIUM
            char_delay = 0.1
        
        current_x = x
        current_text = ""
        cursor_rgb = (0, 255, 255)  # Cyan cursor
        
        for char in text:
            current_text += char
            char_width, text_height = font.getsize(current_text)
            
            self._api.begin_frame(True)
            temp_img = Image.new('RGB', (char_width, text_height), color=(0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            temp_draw.text((0, 0), current_text, font=font, fill=(255, 255, 255))
            pixels = temp_img.load()
            for py in range(text_height):
                for px in range(char_width):
                    if pixels[px, py] != (0, 0, 0):
                        self._api.plot(x + px, y + py, color)
                self._api.plot(x + char_width, y + py, cursor_rgb)
            self._api.end_frame()
            time.sleep(char_delay)
            
            self._api.begin_frame(True)
            for cy in range(text_height):
                self._api.plot(x + char_width, y + cy, (0, 0, 0))  # Clear cursor
            self._api.end_frame()

    def _render_scan(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int]) -> None:
        """Render text with scan effect (pixel-by-pixel)."""
        pixels = img.load()
        for py in range(img.height):
            for px in range(img.width):
                if pixels[px, py] != (0, 0, 0):
                    self._api.plot(x + px, y + py, color)

    def _render_slide(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int], 
                      modifier: EffectModifier) -> None:
        """Render text with slide effect."""
        matrix_width = self._api.matrix.width
        matrix_height = self._api.matrix.height
        pixels = img.load()
        lit_pixels = [(px, py) for py in range(img.height) for px in range(img.width) 
                      if pixels[px, py] != (0, 0, 0)]
        
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
            self._api.begin_frame(True)
            progress = frame / frames
            eased_progress = 0.5 * (1 - math.cos(math.pi * progress))
            current_x = int(start_x + (final_x - start_x) * eased_progress)
            current_y = int(start_y + (final_y - start_y) * eased_progress)
            
            new_active_pixels = {(current_x + px, current_y + py) for px, py in lit_pixels 
                                 if 0 <= current_x + px < matrix_width and 0 <= current_y + py < matrix_height}
            pixels_to_clear = active_pixels - new_active_pixels
            for px, py in pixels_to_clear:
                self._api.plot(px, py, (0, 0, 0))
            pixels_to_draw = new_active_pixels - active_pixels
            for px, py in pixels_to_draw:
                self._api.plot(px, py, color)
            active_pixels = new_active_pixels
            self._api.end_frame()
            time.sleep(duration / frames)

    def _render_dissolve(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int], 
                         modifier: EffectModifier) -> None:
        """Render text with dissolve effect."""
        pixels = img.load()
        lit_pixels = [(x + px, y + py) for py in range(img.height) for px in range(img.width) 
                      if pixels[px, py] != (0, 0, 0) and 
                      0 <= x + px < self._api.matrix.width and 0 <= y + py < self._api.matrix.height]
        
        if modifier == EffectModifier.IN:
            remaining_pixels = lit_pixels.copy()
            while remaining_pixels:
                self._api.begin_frame(True)
                num_pixels = min(len(remaining_pixels), 5)
                for _ in range(num_pixels):
                    if remaining_pixels:
                        idx = random.randint(0, len(remaining_pixels) - 1)
                        px, py = remaining_pixels.pop(idx)
                        self._api.plot(px, py, color)
                self._api.end_frame()
                time.sleep(0.02)
        else:  # OUT
            self._render_normal(img, x, y, color)
            time.sleep(0.5)
            remaining_pixels = lit_pixels.copy()
            while remaining_pixels:
                self._api.begin_frame(True)
                num_pixels = min(len(remaining_pixels), 5)
                for _ in range(num_pixels):
                    if remaining_pixels:
                        idx = random.randint(0, len(remaining_pixels) - 1)
                        px, py = remaining_pixels.pop(idx)
                        self._api.plot(px, py, (0, 0, 0))
                self._api.end_frame()
                time.sleep(0.02)

    def _render_wipe(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int], 
                     modifier: EffectModifier) -> None:
        """Render text with wipe effect."""
        pixels = img.load()
        lit_pixels = [(x + px, y + py) for py in range(img.height) for px in range(img.width) 
                      if pixels[px, py] != (0, 0, 0) and 
                      0 <= x + px < self._api.matrix.width and 0 <= y + py < self._api.matrix.height]

        is_out = modifier in [EffectModifier.OUT_LEFT, EffectModifier.OUT_RIGHT, 
                             EffectModifier.OUT_UP, EffectModifier.OUT_DOWN]
        
        if modifier in [EffectModifier.IN_LEFT, EffectModifier.OUT_RIGHT]:
            lit_pixels.sort(key=lambda p: p[0])
        elif modifier in [EffectModifier.IN_RIGHT, EffectModifier.OUT_LEFT]:
            lit_pixels.sort(key=lambda p: -p[0])
        elif modifier in [EffectModifier.IN_UP, EffectModifier.OUT_DOWN]:
            lit_pixels.sort(key=lambda p: p[1])
        elif modifier in [EffectModifier.IN_DOWN, EffectModifier.OUT_UP]:
            lit_pixels.sort(key=lambda p: -p[1])

        total_frames = 30
        pixels_per_frame = max(1, len(lit_pixels) // total_frames)

        if is_out:
            self._render_normal(img, x, y, color)
            time.sleep(0.5)
            lit_pixels = lit_pixels[::-1]

        revealed_pixels = set()
        for i in range(0, len(lit_pixels), pixels_per_frame):
            self._api.begin_frame(True)
            new_pixels = lit_pixels[i:i + pixels_per_frame]
            for px, py in new_pixels:
                if is_out:
                    self._api.plot(px, py, (0, 0, 0))
                else:
                    self._api.plot(px, py, color)
                    revealed_pixels.add((px, py))
            self._api.end_frame()
            time.sleep(0.02)