# rgb_matrix_lib/__init__.py
from . import commands  # Add this line
from .api import execute_command, execute_single_command, cleanup, RGB_Api
from .debug import debug, Level, Component, configure_debug
from .utils import NAMED_COLORS, SPECTRAL_COLORS, parse_color_spec, get_color_rgb
from .fonts import get_font_manager, FontError
from .text_effects import TextEffect, EffectModifier
from .text_renderer import TextRenderer
from .drawing_objects import ShapeType, Region
from .drawing_objects import ShapeType

# Version info
__version__ = '1.0.0'

__all__ = [
    'execute_command',
    'execute_single_command',
    'cleanup',
    'RGB_Api',
    'debug',
    'Level',
    'Component',
    'configure_debug',
    'NAMED_COLORS',
    'SPECTRAL_COLORS',
    'parse_color_spec',
    'get_color_rgb',
    'get_font_manager',
    'FontError',
    'TextEffect',
    'EffectModifier',
    'TextRenderer',
    'ShapeType',
    'Region',
    'ShapeType',
    '__version__'
]
