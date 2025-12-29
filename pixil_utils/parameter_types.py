from typing import Dict, List, Union, Literal

# Type definitions
ParamType = Literal['int', 'float', 'str', 'bool', 'color']
ParameterDef = Dict[str, Union[str, int, ParamType]]
CommandParams = List[ParameterDef]

# Command parameter definitions
PARAMETER_TYPES: Dict[str, CommandParams] = {
    'plot': [
        {'name': 'x', 'type': 'int', 'position': 0},
        {'name': 'y', 'type': 'int', 'position': 1},
        {'name': 'color', 'type': 'color', 'position': 2},
        {'name': 'intensity', 'type': 'int', 'position': 3, 'optional': True},
        {'name': 'duration', 'type': 'float', 'position': 4, 'optional': True},
        {'name': 'burnout_mode', 'type': 'str', 'position': 5, 'optional': True, 'default': 'instant'}
    ],
    'mplot': [
        {'name': 'x', 'type': 'int', 'position': 0},
        {'name': 'y', 'type': 'int', 'position': 1},
        {'name': 'color', 'type': 'color', 'position': 2},
        {'name': 'intensity', 'type': 'int', 'position': 3, 'optional': True},
        {'name': 'burnout', 'type': 'float', 'position': 4, 'optional': True},
        {'name': 'burnout_mode', 'type': 'str', 'position': 5, 'optional': True, 'default': 'instant'}
    ],
    'mflush': [],
    'draw_line': [
        {'name': 'x1', 'type': 'int', 'position': 0},
        {'name': 'y1', 'type': 'int', 'position': 1},
        {'name': 'x2', 'type': 'int', 'position': 2},
        {'name': 'y2', 'type': 'int', 'position': 3},
        {'name': 'color', 'type': 'color', 'position': 4},
        {'name': 'intensity', 'type': 'int', 'position': 5, 'optional': True},
        {'name': 'duration', 'type': 'float', 'position': 6, 'optional': True},
        {'name': 'burnout_mode', 'type': 'str', 'position': 7, 'optional': True, 'default': 'instant'}
    ],
    'draw_rectangle': [
        {'name': 'x', 'type': 'int', 'position': 0},
        {'name': 'y', 'type': 'int', 'position': 1},
        {'name': 'width', 'type': 'int', 'position': 2},
        {'name': 'height', 'type': 'int', 'position': 3},
        {'name': 'color', 'type': 'color', 'position': 4},
        {'name': 'intensity', 'type': 'int', 'position': 5, 'optional': True},
        {'name': 'filled', 'type': 'bool', 'position': 6, 'optional': True, 'default': 'false'},
        {'name': 'duration', 'type': 'float', 'position': 7, 'optional': True},
        {'name': 'burnout_mode', 'type': 'str', 'position': 8, 'optional': True, 'default': 'instant'}
    ],
    'draw_circle': [
        {'name': 'x', 'type': 'int', 'position': 0},
        {'name': 'y', 'type': 'int', 'position': 1},
        {'name': 'radius', 'type': 'int', 'position': 2},
        {'name': 'color', 'type': 'color', 'position': 3},
        {'name': 'intensity', 'type': 'int', 'position': 4, 'optional': True},
        {'name': 'filled', 'type': 'bool', 'position': 5},
        {'name': 'duration', 'type': 'float', 'position': 6, 'optional': True},
        {'name': 'burnout_mode', 'type': 'str', 'position': 7, 'optional': True, 'default': 'instant'}
    ],
    'draw_arc': [
        {'name': 'x1', 'type': 'int', 'position': 0},
        {'name': 'y1', 'type': 'int', 'position': 1},
        {'name': 'x2', 'type': 'int', 'position': 2},
        {'name': 'y2', 'type': 'int', 'position': 3},
        {'name': 'bulge', 'type': 'float', 'position': 4},
        {'name': 'color', 'type': 'color', 'position': 5},
        {'name': 'intensity', 'type': 'int', 'position': 6, 'optional': True, 'default': '100'},
        {'name': 'filled', 'type': 'bool', 'position': 7, 'optional': True, 'default': 'false'},
        {'name': 'duration', 'type': 'float', 'position': 8, 'optional': True},
        {'name': 'burnout_mode', 'type': 'str', 'position': 9, 'optional': True, 'default': 'instant'}
    ],
    'rest': [
        {'name': 'duration', 'type': 'float', 'position': 0}
    ],
    'define_sprite': [
        {'name': 'name', 'type': 'str', 'position': 0},
        {'name': 'width', 'type': 'int', 'position': 1},
        {'name': 'height', 'type': 'int', 'position': 2}
    ],
    'sprite_cel': [
        {'name': 'cel_index', 'type': 'int', 'position': 0, 'optional': True}
    ],
    'show_sprite': [
        {'name': 'name', 'type': 'str', 'position': 0},
        {'name': 'x', 'type': 'int', 'position': 1},
        {'name': 'y', 'type': 'int', 'position': 2},
        {'name': 'instance_id', 'type': 'int', 'position': 3, 'optional': True, 'default': '0'},
        {'name': 'z_index', 'type': 'int', 'position': 4, 'optional': True, 'default': '0'},
        {'name': 'cel_idx', 'type': 'int', 'position': 5, 'optional': True, 'default': '0'}
    ],
    'hide_sprite': [
        {'name': 'name', 'type': 'str', 'position': 0},
        {'name': 'instance_id', 'type': 'int', 'position': 1, 'optional': True, 'default': '0'}
    ],
    'move_sprite': [
        {'name': 'name', 'type': 'str', 'position': 0},
        {'name': 'x', 'type': 'int', 'position': 1},
        {'name': 'y', 'type': 'int', 'position': 2},
        {'name': 'instance_id', 'type': 'int', 'position': 3, 'optional': True, 'default': '0'},
        {'name': 'cel_idx', 'type': 'int', 'position': 4, 'optional': True}
    ],
    'dispose_sprite': [
        {'name': 'name', 'type': 'str', 'position': 0},
        {'name': 'instance_id', 'type': 'int', 'position': 1, 'optional': True, 'default': '0'}
    ],
    'sprite_draw': [
        {'name': 'sprite_name', 'type': 'str', 'position': 0},
        {'name': 'command', 'type': 'str', 'position': 1},
        {'name': 'args', 'type': 'str', 'position': 2}
    ],
    'dispose_all_sprites': [],
    'draw_polygon': [
        {'name': 'x', 'type': 'int', 'position': 0},
        {'name': 'y', 'type': 'int', 'position': 1},
        {'name': 'radius', 'type': 'int', 'position': 2},
        {'name': 'sides', 'type': 'int', 'position': 3},
        {'name': 'color', 'type': 'color', 'position': 4},
        {'name': 'intensity', 'type': 'int', 'position': 5, 'optional': True},
        {'name': 'rotation', 'type': 'float', 'position': 6, 'optional': True, 'default': '0'},
        {'name': 'filled', 'type': 'bool', 'position': 7, 'optional': True, 'default': 'false'},
        {'name': 'duration', 'type': 'float', 'position': 8, 'optional': True},
        {'name': 'burnout_mode', 'type': 'str', 'position': 9, 'optional': True, 'default': 'instant'}
    ],
    'draw_ellipse': [
        {'name': 'x_center', 'type': 'int', 'position': 0},
        {'name': 'y_center', 'type': 'int', 'position': 1},
        {'name': 'x_radius', 'type': 'int', 'position': 2},
        {'name': 'y_radius', 'type': 'int', 'position': 3},
        {'name': 'color', 'type': 'color', 'position': 4},
        {'name': 'intensity', 'type': 'int', 'position': 5, 'optional': True, 'default': '100'},
        {'name': 'fill', 'type': 'bool', 'position': 6, 'optional': True, 'default': 'false'},
        {'name': 'rotation', 'type': 'float', 'position': 7, 'optional': True, 'default': '0'},
        {'name': 'burnout', 'type': 'float', 'position': 8, 'optional': True},
        {'name': 'burnout_mode', 'type': 'str', 'position': 9, 'optional': True, 'default': 'instant'}
    ],
    'draw_text': [
        {'name': 'x', 'type': 'int', 'position': 0},
        {'name': 'y', 'type': 'int', 'position': 1},
        {'name': 'text', 'type': 'str', 'position': 2},
        {'name': 'font_name', 'type': 'str', 'position': 3},
        {'name': 'font_size', 'type': 'int', 'position': 4},
        {'name': 'color', 'type': 'color', 'position': 5},
        {'name': 'intensity', 'type': 'int', 'position': 6, 'optional': True},  # Added
        {'name': 'effect', 'type': 'str', 'position': 7, 'optional': True},
        {'name': 'effect_modifier', 'type': 'str', 'position': 8, 'optional': True}
    ],
    'clear_text': [
        {'name': 'x', 'type': 'int', 'position': 0},
        {'name': 'y', 'type': 'int', 'position': 1}
    ],
    'throttle': [
        {'name': 'factor', 'type': 'float', 'position': 0}
    ],    
    'clear': [],
    'sync_queue': []
}

# Cache the parameter types
PARAM_INFO_LOOKUP = {}
for command, params in PARAMETER_TYPES.items():
    PARAM_INFO_LOOKUP[command] = {}
    for param in params:
        position = param['position']
        PARAM_INFO_LOOKUP[command][position] = (
            param['type'],
            param.get('optional', False)
        )

__all__ = ['PARAMETER_TYPES', 'PARAM_INFO_LOOKUP', 'get_parameter_type', 'convert_to_type', 'validate_command_params']

def get_parameter_type(command: str, position: int) -> ParamType:
    """Get the expected type for a parameter at a specific position in a command."""
    if command not in PARAMETER_TYPES:
        raise KeyError(f"Unknown command: {command}")
        
    params = PARAMETER_TYPES[command]
    
    if position >= len(params):
        raise IndexError(f"Invalid parameter position {position} for command {command}")
    
    param = params[position]
    param_type = param['type']
    if isinstance(param_type, str):
        return param_type  # type: ignore
    else:
        return str(param_type)  # type: ignore

def split_command_parameters(param_string: str) -> List[str]:
    """
    Split command parameters while preserving nested function calls, expressions,
    and quoted strings with special characters.
    
    Args:
        param_string: Raw parameter string from command
        
    Returns:
        List of individual parameter strings
        
    Example:
        '32, round(10 - random(1, 5, 1), 2), "Hello, World!"' ->
        ["32", "round(10 - random(1, 5, 1), 2)", '"Hello, World!"']
    """
    params = []
    current_param = ""
    paren_level = 0
    in_quotes = False
    escape_next = False
    
    for char in param_string:
        # Handle escape sequences
        if escape_next:
            current_param += char
            escape_next = False
            continue
            
        # Check for escape character
        if char == '\\':
            current_param += char
            escape_next = True
            continue
        
        # Handle quotes
        if char == '"' and not escape_next:
            in_quotes = not in_quotes
            current_param += char
            continue
            
        # Handle parentheses for nested expressions
        if char == '(' and not in_quotes:
            paren_level += 1
            current_param += char
        elif char == ')' and not in_quotes:
            paren_level -= 1
            current_param += char
        # Only split on commas that are not in quotes and not in parentheses
        elif char == ',' and paren_level == 0 and not in_quotes:
            params.append(current_param.strip())
            current_param = ""
        else:
            current_param += char
            
    if current_param:
        params.append(current_param.strip())
        
    return params

def convert_to_type(value: Union[str, int, float, bool], target_type: ParamType) -> Union[str, int, float, bool]:
    """Convert a value to the target type with appropriate rounding for numeric types."""
    try:
        if target_type == 'int':
            # Handle float to int conversion with rounding
            if isinstance(value, float):
                return round(value)
            # Handle string that might contain a float
            if isinstance(value, str) and '.' in value:
                return round(float(value))
            return int(value)
            
        elif target_type == 'float':
            return float(value)
            
        elif target_type == 'bool':
            if isinstance(value, str):
                return value.lower() == 'true'
            return bool(value)
            
        elif target_type == 'str':
            return str(value)

        elif target_type == 'color':
            # For now, pass through the value - actual color parsing will be handled in expression_parser.py
            return value
            
        else:
            raise ValueError(f"Unsupported target type: {target_type}")
            
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert {value} to {target_type}: {str(e)}")

def validate_command_params(command: str, param_string: str) -> List[str]:
    """
    Split and validate command parameters.
    
    Args:
        command: Command name
        param_string: Raw parameter string from command
        
    Returns:
        List of validated parameter strings
        
    Raises:
        KeyError: If command not found
        ValueError: If parameter count is invalid
    """
    # First split parameters
    params = split_command_parameters(param_string)
    
    if command not in PARAMETER_TYPES:
        raise KeyError(f"Unknown command: {command}")
        
    command_params = PARAMETER_TYPES[command]
    
    # Count required parameters (those without optional=True)
    required_params = sum(1 for param in command_params 
                         if not param.get('optional', False))
    total_params = len(command_params)
    
    if len(params) < required_params:
        raise ValueError(
            f"Command '{command}' requires at least {required_params} parameters, "
            f"but got {len(params)}"
        )
    
    if len(params) > total_params:
        raise ValueError(
            f"Command '{command}' accepts at most {total_params} parameters, "
            f"but got {len(params)}"
        )
    
    return params