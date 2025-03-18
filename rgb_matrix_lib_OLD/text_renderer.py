# text_renderer.py
from PIL import Image, ImageDraw
from typing import Dict, Tuple, Optional
from .fonts import get_font_manager, FontError
from .text_effects import TextEffect, EffectModifier, validate_effect_modifier
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
        # Track text bounds by position
        self._text_bounds: Dict[Tuple[int, int], TextBounds] = {}
        self._api = api  # Store api reference

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

    def render_text(self, x: int, y: int, text: str, font_name: str, font_size: int, 
                   color: str, effect: TextEffect = TextEffect.NORMAL,
                   modifier: Optional[EffectModifier] = None) -> None:
        """
        Render text on the LED matrix.
        
        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to render
            font_name: Name of font to use
            font_size: Size of font in pixels
            color: Color name or specification
            effect: Text effect to apply
            modifier: Effect modifier (if applicable)
        """
        # Get font
        font = get_font_manager().get_font(font_name, font_size)
        
        # Calculate text dimensions
        text_width, text_height = font.getsize(text)
        
        # Create image for text
        img = Image.new('RGB', (text_width, text_height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), text, font=font, fill=(255, 255, 255))
        
        # Store bounds for this text
        self._text_bounds[(x, y)] = TextBounds(x, y, text_width, text_height)
        
        # Handle different effects
        if effect == TextEffect.NORMAL:
            self._render_normal(img, x, y, color)
        elif effect == TextEffect.TYPE:
            # Use MEDIUM speed if no modifier specified
            if modifier is None:
                modifier = EffectModifier.MEDIUM
            validate_effect_modifier(effect, modifier)
            self._render_type(img, x, y, text, color, modifier, font_name, font_size)
        elif effect == TextEffect.SCAN:  # Add this section
            self._render_scan(img, x, y, color)
        elif effect == TextEffect.SLIDE:
            if modifier is None:
                modifier = EffectModifier.LEFT  # Default direction
            validate_effect_modifier(effect, modifier)
            self._render_slide(img, x, y, color, modifier)         
        elif effect == TextEffect.DISSOLVE:
            self._render_dissolve(img, x, y, color, modifier)
        elif effect == TextEffect.WIPE:
            self._render_wipe(img, x, y, color, modifier)
        else:
            raise NotImplementedError(f"Effect {effect.name} not yet implemented")

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
            
            self._api.execute_command("begin_frame")
            for py in range(bounds.height):
                plot_y = bounds.y + py
                if 0 <= plot_y < matrix_height:
                    for px in range(bounds.width):
                        plot_x = bounds.x + px
                        if 0 <= plot_x < matrix_width:
                            self._api.execute_command(f"plot({plot_x}, {plot_y}, black)")
            self._api.execute_command("end_frame")
            
            # Remove tracking
            self._clear_tracking(x, y)

    def _render_normal(self, img: Image.Image, x: int, y: int, color: str) -> None:
        """
        Render text normally (all at once).
        
        Args:
            img: PIL Image containing rendered text
            x: X coordinate
            y: Y coordinate
            color: Color to render text in
        """
        # Get RGB color values
        rgb_color = self._api._get_color(color)
        pixels = img.load()
        matrix_width = self._api.matrix.width
        matrix_height = self._api.matrix.height
        
        self._api.execute_command("begin_frame")
        for y_offset in range(img.height):
            plot_y = y + y_offset
            if 0 <= plot_y < matrix_height:  # Only process rows that are in bounds
                for x_offset in range(img.width):
                    plot_x = x + x_offset
                    if 0 <= plot_x < matrix_width:  # Only process columns that are in bounds
                        if pixels[x_offset, y_offset] != (0, 0, 0):
                            self._api.execute_command(f"plot({plot_x}, {plot_y}, {color})")
        self._api.execute_command("end_frame")
        
    def _render_scan(self, img: Image.Image, x: int, y: int, color: str) -> None:
        """
        Render text normally (all at once).
        
        Args:
            img: PIL Image containing rendered text
            x: X coordinate
            y: Y coordinate
            color: Color to render text in
        """
        pixels = img.load()
        for py in range(img.height):
            for px in range(img.width):
                if pixels[px, py] != (0, 0, 0):  # If pixel is not black
                    self._api.execute_command(f"plot({x + px}, {y + py}, {color})")

    def _render_type(self, img: Image.Image, x: int, y: int, text: str, color: str, 
                    modifier: EffectModifier, font_name: str, font_size: int) -> None:
        """
        Render text with typewriter effect.
        
        Args:
            img: PIL Image containing full rendered text
            x: X coordinate
            y: Y coordinate
            text: Text string being rendered
            color: Color to render text in
            modifier: Speed modifier (SLOW, MEDIUM, FAST)
        """
        # Get font settings from original image
        font = get_font_manager().get_font(font_name, font_size)
        
        # Get delay based on modifier
        if modifier == EffectModifier.SLOW:
            char_delay = 0.2
        elif modifier == EffectModifier.FAST:
            char_delay = 0.05
        else:  # MEDIUM is default
            char_delay = 0.1
        
        current_x = x
        current_text = ""
        
        # Type each character
        for char in text:
            current_text += char
            
            # Create image for current text
            char_width, text_height = font.getsize(current_text)
            
            # Draw current text
            self._api.execute_command("begin_frame")
            
            # Draw text up to current character
            temp_img = Image.new('RGB', (char_width, text_height), color=(0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            temp_draw.text((0, 0), current_text, font=font, fill=(255, 255, 255))
            
            # Draw all pixels for current text
            pixels = temp_img.load()
            for py in range(text_height):
                for px in range(char_width):
                    if pixels[px, py] != (0, 0, 0):
                        self._api.execute_command(f"plot({x + px}, {y + py}, {color})")
            
            # Draw cursor
            for cy in range(text_height):
                self._api.execute_command(f"plot({x + char_width}, {y + cy}, cyan)")
                
            self._api.execute_command("end_frame")
            time.sleep(char_delay)
            
            # Clear cursor before next character
            self._api.execute_command("begin_frame")
            for cy in range(text_height):
                self._api.execute_command(f"plot({x + char_width}, {y + cy}, black)")
            self._api.execute_command("end_frame")

    def _render_slide(self, img: Image.Image, x: int, y: int, color: str, modifier: EffectModifier) -> None:
        """
        Render text with slide effect.
        
        Args:
            img: PIL Image containing rendered text
            x: X coordinate (final position)
            y: Y coordinate (final position)
            color: Color to render text in
            modifier: Direction modifier (LEFT, RIGHT, UP, DOWN)
        """
        matrix_width = self._api.matrix.width
        matrix_height = self._api.matrix.height
        #print("Precalculate")
        # Pre-calculate lit pixels
        pixels = img.load()
        lit_pixels = []
        for py in range(img.height):
            for px in range(img.width):
                if pixels[px, py] != (0, 0, 0):
                    lit_pixels.append((px, py))
        #print("Calculate over")
        
        # Calculate start and final positions
        if modifier == EffectModifier.LEFT:
            start_x = matrix_width
            start_y = y
            final_x = x
            final_y = y
        elif modifier == EffectModifier.RIGHT:
            start_x = -img.width
            start_y = y
            final_x = x
            final_y = y
        elif modifier == EffectModifier.UP:
            start_x = x
            start_y = matrix_height
            final_x = x
            final_y = y
        else:  # DOWN
            start_x = x
            start_y = -img.height
            final_x = x
            final_y = y
        math
        # Animation parameters
        duration = 1.0  # seconds
        frames = 40
        active_pixels = set()
        
        # Animation loop
        for frame in range(frames + 1):
            self._api.execute_command("begin_frame")
            
            # Calculate new position with easing
            progress = frame / frames
            eased_progress = 0.5 * (1 - math.cos(math.pi * progress))
            
            current_x = int(start_x + (final_x - start_x) * eased_progress)
            current_y = int(start_y + (final_y - start_y) * eased_progress)
            
            # Calculate new pixel positions
            new_active_pixels = set()
            for px, py in lit_pixels:
                plot_x = current_x + px
                plot_y = current_y + py
                if 0 <= plot_x < matrix_width and 0 <= plot_y < matrix_height:
                    new_active_pixels.add((plot_x, plot_y))
            
            # Clear pixels that are no longer active
            pixels_to_clear = active_pixels - new_active_pixels
            for px, py in pixels_to_clear:
                self._api.execute_command(f"plot({px}, {py}, black)")
            
            # Draw new pixels
            pixels_to_draw = new_active_pixels - active_pixels
            for px, py in pixels_to_draw:
                self._api.execute_command(f"plot({px}, {py}, {color})")
            
            # Update active pixels for next frame
            active_pixels = new_active_pixels
            
            self._api.execute_command("end_frame")
            time.sleep(duration / frames)
    
    def _render_dissolve(self, img: Image.Image, x: int, y: int, color: str, modifier: EffectModifier) -> None:
        """
        Render text with dissolve effect.
        
        Args:
            img: PIL Image containing rendered text
            x: X coordinate
            y: Y coordinate
            color: Color to render text in
            modifier: IN (dissolve in) or OUT (dissolve out)
        """
        # Get list of all lit pixels
        pixels = img.load()
        lit_pixels = []
        for py in range(img.height):
            for px in range(img.width):
                if pixels[px, py] != (0, 0, 0):
                    plot_x = x + px
                    plot_y = y + py
                    if 0 <= plot_x < self._api.matrix.width and 0 <= plot_y < self._api.matrix.height:
                        lit_pixels.append((plot_x, plot_y))
        
        if modifier == EffectModifier.IN:
            # Dissolve In
            remaining_pixels = lit_pixels.copy()
            
            while remaining_pixels:
                self._api.execute_command("begin_frame")
                
                # Add random pixels
                num_pixels = min(len(remaining_pixels), 5)  # Add 5 pixels per frame
                for _ in range(num_pixels):
                    if remaining_pixels:
                        idx = random.randint(0, len(remaining_pixels) - 1)
                        px, py = remaining_pixels.pop(idx)
                        self._api.execute_command(f"plot({px}, {py}, {color})")
                
                self._api.execute_command("end_frame")
                time.sleep(0.02)
                
        else:  # OUT (default)
            # Show text immediately
            self._api.execute_command("begin_frame")
            self._render_normal(img, x, y, color)
            self._api.execute_command("end_frame")
            time.sleep(0.5)  # Brief pause
            
            # Dissolve Out
            remaining_pixels = lit_pixels.copy()
            
            while remaining_pixels:
                self._api.execute_command("begin_frame")
                
                # Remove random pixels
                num_pixels = min(len(remaining_pixels), 5)  # Remove 5 pixels per frame
                for _ in range(num_pixels):
                    if remaining_pixels:
                        idx = random.randint(0, len(remaining_pixels) - 1)
                        px, py = remaining_pixels.pop(idx)
                        self._api.execute_command(f"plot({px}, {py}, black)")
                
                self._api.execute_command("end_frame")
                time.sleep(0.02)

    def _render_wipe(self, img: Image.Image, x: int, y: int, color: str, modifier: EffectModifier) -> None:
        """
        Render text with wipe effect.
        
        Args:
            img: PIL Image containing rendered text
            x: X coordinate
            y: Y coordinate
            color: Color to render text in
            modifier: Direction and type modifier (IN_LEFT, OUT_RIGHT, etc.)
        """
        # Get list of all lit pixels
        pixels = img.load()
        lit_pixels = []
        for py in range(img.height):
            for px in range(img.width):
                if pixels[px, py] != (0, 0, 0):
                    plot_x = x + px
                    plot_y = y + py
                    if 0 <= plot_x < self._api.matrix.width and 0 <= plot_y < self._api.matrix.height:
                        lit_pixels.append((plot_x, plot_y))

        # Determine direction and whether it's in or out
        is_out = modifier in [EffectModifier.OUT_LEFT, EffectModifier.OUT_RIGHT, 
                            EffectModifier.OUT_UP, EffectModifier.OUT_DOWN]
        
        # Sort pixels based on direction
        if modifier in [EffectModifier.IN_LEFT, EffectModifier.OUT_RIGHT]:
            lit_pixels.sort(key=lambda p: p[0])  # Sort by x coordinate
        elif modifier in [EffectModifier.IN_RIGHT, EffectModifier.OUT_LEFT]:
            lit_pixels.sort(key=lambda p: -p[0])  # Sort by negative x
        elif modifier in [EffectModifier.IN_UP, EffectModifier.OUT_DOWN]:
            lit_pixels.sort(key=lambda p: p[1])  # Sort by y coordinate
        elif modifier in [EffectModifier.IN_DOWN, EffectModifier.OUT_UP]:
            lit_pixels.sort(key=lambda p: -p[1])  # Sort by negative y

        # Animation parameters
        total_frames = 30
        pixels_per_frame = max(1, len(lit_pixels) // total_frames)

        if is_out:
            # Show text immediately first
            self._render_normal(img, x, y, color)
            time.sleep(0.5)  # Brief pause
            
            # Reverse sort order for out effect
            lit_pixels = lit_pixels[::-1]

        # Perform wipe animation
        revealed_pixels = set()
        for i in range(0, len(lit_pixels), pixels_per_frame):
            self._api.execute_command("begin_frame")
            
            # Get next batch of pixels
            new_pixels = lit_pixels[i:i + pixels_per_frame]
            
            # Draw new pixels or clear pixels
            for px, py in new_pixels:
                if is_out:
                    self._api.execute_command(f"plot({px}, {py}, black)")
                else:
                    self._api.execute_command(f"plot({px}, {py}, {color})")
                    revealed_pixels.add((px, py))
                
            self._api.execute_command("end_frame")
            time.sleep(0.02)