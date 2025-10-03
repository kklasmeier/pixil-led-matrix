# fonts.py
import os
from PIL import ImageFont
from PIL.ImageFont import FreeTypeFont
from typing import Dict, List, Optional, Any, Union
from .bitmap_font import BitmapFontAdapter  # Import our new adapter

class FontError(Exception):
    """
    Exception raised for font-related errors.
    
    Used for:
    - Font not found errors
    - Font loading failures
    - Invalid font names
    - Font validation failures
    """
    pass

class FontManager:
    """Manages font discovery and caching"""
    
    _instance = None  # Singleton instance

    @classmethod
    def get_instance(cls) -> 'FontManager':
        """Get or create the singleton instance of FontManager"""
        if cls._instance is None:
            cls._instance = FontManager()
        return cls._instance

    def __init__(self):
        # Cache of found font paths (name -> path)
        self._font_paths: Dict[str, str] = {}
        # Cache of loaded fonts (name, size) -> font object
        self._loaded_fonts: Dict[tuple, Any] = {}
        # Flag to track if we've scanned for fonts
        self._initialized = False
        
    def _scan_font_directories(self) -> None:
        """
        Scan system directories for available fonts.
        Called once on first use.
        """
        FONT_DIRECTORIES = [
            "/usr/share/fonts/truetype",
            "/usr/local/share/fonts",
            "~/.fonts"
        ]
        
        for base_dir in FONT_DIRECTORIES:
            base_dir = os.path.expanduser(base_dir)  # Handle ~ in paths
            if not os.path.exists(base_dir):
                continue
                
            for root, _, files in os.walk(base_dir):
                for file in files:
                    if file.lower().endswith(('.ttf', '.otf')):
                        font_path = os.path.join(root, file)
                        # Store font name without extension, lowercase for case-insensitive matching
                        font_name = os.path.splitext(file)[0].lower()
                        self._font_paths[font_name] = font_path
        
        self._initialized = True

    def _validate_font(self, font_path: str) -> bool:
        """
        Test if a font file can be loaded.
        
        Args:
            font_path: Path to font file
            
        Returns:
            bool: True if font can be loaded, False otherwise
        """
        try:
            # Attempt to load font at a small size
            ImageFont.truetype(font_path, 8)
            return True
        except Exception:
            return False

    def get_font(self, font_name: str, size: int) -> Union[FreeTypeFont, BitmapFontAdapter]:
        """
        Get a font by name and size.
        
        Args:
            font_name: Name of the font (without extension)
            size: Font size in pixels
            
        Returns:
            FreeTypeFont object or BitmapFontAdapter
            
        Raises:
            FontError if font not found or can't be loaded
        """
        # Special case for our bitmap font
        if font_name.lower() == "tiny64_font":
            # Check if we've already loaded this font
            cache_key = ("tiny64_font", size)
            if cache_key in self._loaded_fonts:
                return self._loaded_fonts[cache_key]
                
            # Create a new adapter
            bitmap_adapter = BitmapFontAdapter(size)
            self._loaded_fonts[cache_key] = bitmap_adapter
            return bitmap_adapter
            
        # Normal font loading process
        # Initialize if needed
        if not self._initialized:
            self._scan_font_directories()

        # Convert font name to lowercase for case-insensitive matching
        font_name = font_name.lower()
        
        # Check if we've already loaded this font/size
        cache_key = (font_name, size)
        if cache_key in self._loaded_fonts:
            return self._loaded_fonts[cache_key]

        # Check if font exists
        if font_name not in self._font_paths:
            raise FontError(
                f"Font '{font_name}' not found. Available fonts: {', '.join(sorted(self._font_paths.keys()))}"
            )

        font_path = self._font_paths[font_name]

        # Validate font can be loaded
        if not self._validate_font(font_path):
            raise FontError(f"Font file '{font_path}' exists but cannot be loaded")

        try:
            font = ImageFont.truetype(font_path, size)
            # Cache this font
            self._loaded_fonts[cache_key] = font
            return font
        except Exception as e:
            raise FontError(f"Error loading font '{font_name}': {str(e)}")

    def list_available_fonts(self) -> List[str]:
        """
        Get list of all available fonts.
        
        Returns:
            List of font names that can be used with get_font()
        """
        # Initialize if needed
        if not self._initialized:
            self._scan_font_directories()
            
        # Add our bitmap font to the list
        fonts = list(sorted(self._font_paths.keys()))
        fonts.append("tiny64_font")
        
        # Return sorted list of font names
        return sorted(fonts)

# Global font manager instance
_font_manager: Optional[FontManager] = None

def get_font_manager() -> FontManager:
    """Get or create the global FontManager instance"""
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
    return _font_manager