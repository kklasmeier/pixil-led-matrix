# File: rgb_matrix_lib/bitmap_font.py

import os
from typing import Dict, List, Tuple, Optional
from PIL import Image
from .debug import debug, Level, Component

class BitmapFontManager:
    """Manages the custom bitmap font for LED matrix display"""
    
    _instance = None  # Singleton instance
    
    @classmethod
    def get_instance(cls) -> 'BitmapFontManager':
        """Get or create the singleton instance of BitmapFontManager"""
        if cls._instance is None:
            cls._instance = BitmapFontManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the bitmap font manager"""
        if BitmapFontManager._instance is not None:
            debug("BitmapFontManager already initialized, use get_instance()", 
                  Level.WARNING, Component.SYSTEM)
            return
            
        self.font_data: Dict[str, List[str]] = {}
        self.font_loaded = False
        self.descenders = ['g', 'j', 'p', 'q', 'y']  # Characters with descenders
        
        # Try to load the font at initialization
        self._load_font()
    
    def _load_font(self) -> bool:
        """Load the bitmap font data from file"""
        if self.font_loaded:
            return True
            
        try:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(current_dir, 'tiny64_font.txt')
            
            debug(f"Loading bitmap font from {font_path}", Level.INFO, Component.SYSTEM)
            
            with open(font_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Split the line into parts
                    parts = line.split(',')
                    if len(parts) < 2:
                        debug(f"Invalid line in bitmap font file: {line}", 
                              Level.WARNING, Component.SYSTEM)
                        continue
                    
                    # First part is the character
                    char = parts[0]
                    # Remaining parts are the bitmap rows
                    bitmap = parts[1:]
                    
                    self.font_data[char] = bitmap
            
            self.font_loaded = True
            debug(f"Bitmap font loaded successfully with {len(self.font_data)} characters", 
                  Level.INFO, Component.SYSTEM)
            return True
            
        except Exception as e:
            debug(f"Error loading bitmap font: {str(e)}", Level.ERROR, Component.SYSTEM)
            return False
    
    def ensure_font_loaded(self) -> bool:
        """Ensure the font is loaded before use"""
        if not self.font_loaded:
            return self._load_font()
        return True
    
    def get_char_bitmap(self, char: str) -> Optional[List[str]]:
        """Get the bitmap data for a character"""
        if not self.ensure_font_loaded() or not char:
            return None
            
        # Return the bitmap data if the character exists
        return self.font_data.get(char)
    
    def get_char_dimensions(self, char: str) -> Tuple[int, int]:
        """Get the width and height of a character"""
        bitmap = self.get_char_bitmap(char)
        if not bitmap:
            # Default to a space character (typically 2x5)
            return (2, 5)
            
        # Width is determined by the actual width of the bitmap
        # (length of the first row)
        width = len(bitmap[0])
        height = len(bitmap)
        
        return (width, height)
    
    def get_text_dimensions(self, text: str) -> Tuple[int, int]:
        """Calculate the dimensions of a complete text string"""
        if not text or not self.ensure_font_loaded():
            return (0, 0)
            
        total_width = 0
        max_height = 5  # Default height
        
        for i, char in enumerate(text):
            width, height = self.get_char_dimensions(char)
            total_width += width
            max_height = max(max_height, height)
            
            # Add spacing between characters (except after the last one)
            if i < len(text) - 1:
                total_width += 1
        
        return (total_width, max_height)
    
    def create_text_image(self, text: str) -> Optional[Image.Image]:
        """Create a PIL Image from the bitmap font data for the given text"""
        if not text or not self.ensure_font_loaded():
            return None
            
        # Get the dimensions of the text
        width, height = self.get_text_dimensions(text)
        if width == 0 or height == 0:
            return None
            
        # Create a new blank image
        img = Image.new('RGB', (width, height), color=(0, 0, 0))
        
        # Position for drawing the next character
        x_pos = 0
        
        for char in text:
            bitmap = self.get_char_bitmap(char)
            if not bitmap:
                # Skip unknown characters
                x_pos += 2  # Default width + spacing
                continue
                
            char_width = len(bitmap[0])  # Use actual width from bitmap
            char_height = len(bitmap)
            
            # Determine vertical position (handle descenders)
            y_offset = 0
            if char in self.descenders:
                y_offset = 0  # Descenders start at the top but extend lower
            
            # Draw the character
            for y, row in enumerate(bitmap):
                for x, pixel in enumerate(row):
                    if pixel == '1':
                        img.putpixel((x_pos + x, y_offset + y), (255, 255, 255))
            
            # Move to the next character position
            x_pos += char_width + 1  # Add spacing
        
        return img   
     
    def get_bitmap_font_image(self, text: str, font_size: int = 5) -> Tuple[Image.Image, Tuple[int, int]]:
        """
        Get a PIL Image with the text rendered using the bitmap font.
        This method serves as a bridge to the existing text rendering system.
        
        Args:
            text: Text to render
            font_size: Ignored, kept for API compatibility
            
        Returns:
            A tuple containing:
            - The PIL Image with the rendered text
            - The dimensions (width, height) of the text
        """
        # Ensure font is loaded
        if not self.ensure_font_loaded():
            # Return a minimal empty image
            img = Image.new('RGB', (1, 5), color=(0, 0, 0))
            return img, (1, 5)
        
        # Get text dimensions
        dimensions = self.get_text_dimensions(text)
        
        # Create the image
        img = self.create_text_image(text)
        if img is None:
            # Return a minimal empty image
            img = Image.new('RGB', (1, 5), color=(0, 0, 0))
            return img, (1, 5)
            
        return img, dimensions
    
    def getsize(self, text: str) -> Tuple[int, int]:
        """
        Get the size of text when rendered with the bitmap font.
        This method mimics the PIL ImageFont.getsize method for compatibility.
        
        Args:
            text: Text to measure
            
        Returns:
            A tuple containing the width and height of the text
        """
        return self.get_text_dimensions(text)


# Helper function to access the bitmap font
def get_bitmap_font_manager() -> BitmapFontManager:
    """Get the singleton instance of the BitmapFontManager"""
    return BitmapFontManager.get_instance()


class BitmapFontAdapter:
    """
    Adapter class to make the bitmap font compatible with
    the existing text rendering system that expects PIL ImageFont objects
    """
    
    def __init__(self, font_size: int = 5):
        """
        Initialize the adapter with the bitmap font manager
        
        Args:
            font_size: Ignored, kept for API compatibility
        """
        self.font_manager = get_bitmap_font_manager()
        
    def getsize(self, text: str) -> Tuple[int, int]:
        """
        Get the size of text when rendered with the bitmap font
        
        Args:
            text: Text to measure
            
        Returns:
            A tuple containing the width and height of the text
        """
        return self.font_manager.getsize(text)