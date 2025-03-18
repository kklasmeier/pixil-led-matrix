# File: rgb_matrix_lib/debug.py

from enum import Enum
from typing import Set, Optional
import inspect

class Level(Enum):
    """Debug levels from most severe to least."""
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    TRACE = 5

class Component(Enum):
    """System components for debug messages."""
    SPRITE = "SPRITE"
    DRAWING = "DRAWING"
    COMMAND = "COMMAND"
    SYSTEM = "SYSTEM"
    MATRIX = "MATRIX"

class DebugManager:
    """Simple debug manager for logging messages with caller tracking."""
    # Default to ERROR level - only ERROR and CRITICAL will show by default
    min_level = Level.WARNING
    enabled_components: Set[Component] = set(Component)

    @classmethod
    def configure(cls, 
                 level: Optional[Level] = None,
                 components: Optional[Set[Component]] = None) -> None:
        """
        Configure debug settings for the entire application.
        
        Args:
            level: Minimum debug level to display (if None, keeps current level)
            components: Set of components to enable (if None, all enabled)
        """
        if level is not None:
            cls.min_level = level
        if components is not None:
            cls.enabled_components = set(components)
        
        # Log the configuration change
        cls.debug(
            f"Debug configured - Level: {cls.min_level.name}, "
            f"Components: {[c.name for c in cls.enabled_components]}",
            Level.ERROR,  # Use ERROR level to ensure this message is seen
            Component.SYSTEM
        )

    @classmethod
    def debug(cls, message: str, level: Level = Level.DEBUG, component: Component = Component.SYSTEM) -> None:
        """
        Log a debug message if it meets the minimum level and component criteria.
        
        Args:
            message: Debug message to log
            level: Debug level of the message
            component: System component the message relates to
        """
        if level.value >= cls.min_level.value and component in cls.enabled_components:
            # Get the calling module name
            frame = inspect.currentframe()
            if frame:
                caller_frame = frame.f_back
                if caller_frame:
                    caller = caller_frame.f_globals['__name__']
                    # Get just the final part of the module path
                    if '.' in caller:
                        caller = caller.split('.')[-1]
                    
                    print(f"[{level.name:<8}] [{caller:<8}] [{component.value:<8}] {message}")
                    
                    # Clean up reference cycles
                    del caller_frame
                del frame

# Convenience functions
debug = DebugManager.debug
configure_debug = DebugManager.configure
