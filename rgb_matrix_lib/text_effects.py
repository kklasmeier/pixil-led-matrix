# text_effects.py
from enum import Enum, auto
import random

class TextEffect(Enum):
    """Defines available text effects"""
    NORMAL = auto()  # New immediate render
    SCAN = auto()    # Previous pixel-by-pixel render
    PIXEL = auto()
    TYPE = auto()
    SLIDE = auto()
    DISSOLVE = auto()
    WIPE = auto()

class EffectModifier(Enum):
    """Defines modifiers for text effects"""
    # NORMAL effect has no modifiers
    NONE = auto()
    
    # PIXEL effect modifiers
    TOP = auto()
    BOTTOM = auto()
    
    # TYPE effect modifiers
    SLOW = auto()
    MEDIUM = auto()
    FAST = auto()
    
    # SLIDE effect modifiers
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    
    # DISSOLVE effect modifiers
    IN = auto()
    OUT = auto()
    
    # WIPE effect modifiers
    IN_LEFT = auto()
    IN_RIGHT = auto()
    IN_UP = auto()
    IN_DOWN = auto()
    OUT_LEFT = auto()
    OUT_RIGHT = auto()
    OUT_UP = auto()
    OUT_DOWN = auto()

# Define valid modifier mappings and defaults
EFFECT_MODIFIER_MAP = {
    TextEffect.NORMAL: [EffectModifier.NONE],
    TextEffect.SCAN: [EffectModifier.NONE],
    TextEffect.PIXEL: [EffectModifier.TOP, EffectModifier.BOTTOM],
    TextEffect.TYPE: [EffectModifier.SLOW, EffectModifier.MEDIUM, EffectModifier.FAST],
    TextEffect.SLIDE: [EffectModifier.LEFT, EffectModifier.RIGHT, EffectModifier.UP, EffectModifier.DOWN],
    TextEffect.DISSOLVE: [EffectModifier.IN, EffectModifier.OUT],
    TextEffect.WIPE: [
        EffectModifier.IN_LEFT, EffectModifier.IN_RIGHT, EffectModifier.IN_UP, EffectModifier.IN_DOWN,
        EffectModifier.OUT_LEFT, EffectModifier.OUT_RIGHT, EffectModifier.OUT_UP, EffectModifier.OUT_DOWN
    ]
}

EFFECT_DEFAULT_MODIFIERS = {
    TextEffect.NORMAL: EffectModifier.NONE,
    TextEffect.PIXEL: EffectModifier.TOP,
    TextEffect.TYPE: EffectModifier.MEDIUM,
    TextEffect.SLIDE: EffectModifier.LEFT,
    TextEffect.DISSOLVE: EffectModifier.OUT,
    TextEffect.WIPE: EffectModifier.IN_LEFT
}

def validate_effect_modifier(effect: TextEffect, modifier: EffectModifier) -> None:
    """
    Validate that a modifier is valid for an effect
    
    Args:
        effect: The text effect
        modifier: The modifier to validate
        
    Raises:
        ValueError if modifier is not valid for the effect
    """
    if modifier not in EFFECT_MODIFIER_MAP[effect]:
        valid_modifiers = [m.name for m in EFFECT_MODIFIER_MAP[effect]]
        raise ValueError(
            f"Invalid modifier '{modifier.name}' for effect '{effect.name}'. "
            f"Valid modifiers are: {', '.join(valid_modifiers)}"
        )