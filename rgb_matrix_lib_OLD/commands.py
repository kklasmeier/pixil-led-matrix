# File: rgb_matrix_lib/commands.py

import re
from typing import List, Any, Dict, Callable, Optional
from .debug import debug, Level, Component
from .utils import NAMED_COLORS, parse_color_spec, get_color_rgb, get_color_palette
from .text_effects import TextEffect, EffectModifier

class CommandExecutor:
    """Handles parsing and execution of drawing commands."""
    
    def __init__(self, api):
        """Initialize command executor."""
        debug("Initializing CommandExecutor", Level.INFO, Component.COMMAND)
        self.api = api
        self.command_handlers = {
            'plot': self._handle_plot,
            'draw_line': self._handle_draw_line,
            'draw_rectangle': self._handle_draw_rectangle,
            'draw_circle': self._handle_draw_circle,
            'draw_polygon': self._handle_draw_polygon,  # Add new handler
            'define_sprite': self._handle_define_sprite,
            'sprite_draw': self._handle_sprite_draw,
            'show_sprite': self._handle_show_sprite,
            'hide_sprite': self._handle_hide_sprite,
            'move_sprite': self._handle_move_sprite,
            'clear': self._handle_clear,
            'rest': self._handle_rest,
            'begin_frame': self._handle_begin_frame,
            'end_frame': self._handle_end_frame,
            'draw_text': self._handle_draw_text,
            'clear_text': self._handle_clear_text,
            'dispose_all_sprites': self._handle_dispose_all_sprites,  
            'sync_queue': self._handle_sync_queue,
        }
        self.current_command = None
        self.current_sprite_command = None
        debug(f"Registered {len(self.command_handlers)} command handlers", 
            Level.DEBUG, Component.COMMAND)

    def execute_command(self, command: str) -> None:
        """Execute a single command."""
        if not command:
            debug("Empty command received, ignoring", Level.WARNING, Component.COMMAND)
            return
                
        debug(f"Processing command: {command}", Level.DEBUG, Component.COMMAND)

        try:
            # Handle simple commands without parameters
            if command in ['begin_frame', 'end_frame', 'clear', 'dispose_all_sprites', 'sync_queue']:
                debug(f"Executing simple command: {command}", Level.DEBUG, Component.COMMAND)
                self.current_command = command
                handler = self.command_handlers.get(command)
                if handler:
                    debug(f"Found handler for command: {command}", Level.DEBUG, Component.COMMAND)
                    try:
                        handler()
                        debug(f"Handler execution completed for: {command}", Level.DEBUG, Component.COMMAND)
                    except Exception as e:
                        debug(f"Handler execution failed for {command}: {str(e)}", Level.ERROR, Component.COMMAND)
                        raise
                else:
                    debug(f"No handler found for command: {command}", Level.ERROR, Component.COMMAND)
                    raise ValueError(f"No handler found for command: {command}")
                return

            # Parse command and execute
            cmd_name, params = self._parse_command(command)
            self._execute_parsed_command(cmd_name, params)
            debug("Command executed successfully", Level.DEBUG, Component.COMMAND)
        finally:
            # Always clear command state after execution
            self.current_command = None
            
    def _parse_command(self, command: str) -> tuple[str, List[Any]]:
        """Parse a command string into name and parameters."""
        match = re.match(r'(\w+)\((.*)\)', command)
        if not match:
            debug(f"Invalid command format: {command}", Level.ERROR, Component.COMMAND)
            raise ValueError(f"Invalid command format: {command}")
                
        cmd_name, params_str = match.groups()
        # Set current command before parsing parameters
        self.current_command = cmd_name
        debug(f"Parsed command '{cmd_name}' with parameters: {params_str}",
            Level.TRACE, Component.COMMAND)

        # Parse parameters with command context
        params = self._parse_parameters(params_str)
        return cmd_name, params

    def _parse_parameters(self, params_str: str) -> List[Any]:
        """Parse parameter string into typed values."""
        if not params_str:
            return []
                
        params = []
        param_index = 0
        
        # Process the parameters string
        current_param = ""
        in_quotes = False
        i = 0
        
        while i < len(params_str):
            char = params_str[i]
            
            # Handle quoted text
            if char == '"':
                if in_quotes:
                    # Check for escaped quote
                    if i + 1 < len(params_str) and params_str[i + 1] == '"':
                        current_param += '"'
                        i += 2
                        continue
                    else:
                        # End of quoted text
                        in_quotes = False
                        i += 1
                        continue
                else:
                    # Start of quoted text
                    in_quotes = True
                    i += 1
                    continue
                    
            # Handle commas
            if char == ',' and not in_quotes:
                # End of parameter
                param = current_param.strip()
                if param:
                    param_index += 1
                    params.append(self._convert_parameter(param, param_index))
                current_param = ""
                i += 1
                continue
                
            # Add character to current parameter
            current_param += char
            i += 1
        
        # Add final parameter
        if current_param.strip():
            param_index += 1
            params.append(self._convert_parameter(current_param.strip(), param_index))
        
        return params

    def _convert_parameter(self, param: str, param_index: int) -> Any:
        """Convert a parameter string to its appropriate type."""
        # Check if this is color parameter
        if self._is_color_parameter(param_index):
            debug(f"Detected color parameter at position {param_index}", Level.TRACE, Component.COMMAND)
            # Process as color spec
            debug(f"Processing as color specification: {param}", Level.TRACE, Component.COMMAND)
            color_base, intensity = parse_color_spec(param)
            rgb_color = get_color_rgb(color_base, intensity)
            debug(f"Resolved color {param} to RGB: {rgb_color}", Level.TRACE, Component.COMMAND)
            return rgb_color

        # Handle boolean values
        if param.lower() == 'true':
            return True
        elif param.lower() == 'false':
            return False

        # Try numeric conversion
        try:
            if '.' in param:
                return float(param)
            return int(param)
        except ValueError:
            # Not a number, return as string
            # If it's a quoted string, process escaped quotes
            if param.startswith('"') and param.endswith('"'):
                inner_text = param[1:-1]  # Remove outer quotes
                return inner_text.replace('""', '"')
            return param

    def _is_color_parameter(self, index: int) -> bool:
        """Determine if parameter at given index should be treated as a color."""
        # Color parameter positions for each command
        color_positions = {
            'plot': 3,
            'draw_line': 5,
            'draw_rectangle': 5,
            'draw_circle': 4,
            'draw_polygon': 5,
        }
        
        debug(f"Checking if parameter {index} is color for command {self.current_command}", 
            Level.TRACE, Component.COMMAND)
        
        if self.current_command == 'sprite_draw':
            # For sprite_draw, check the wrapped command
            if self.current_sprite_command in color_positions:
                # Add 2 to account for sprite name and command type
                color_pos = color_positions[self.current_sprite_command] + 2
                debug(f"Sprite draw color position: {color_pos}", Level.TRACE, Component.COMMAND)
                return index == color_pos
        elif self.current_command in color_positions:
            color_pos = color_positions[self.current_command]
            debug(f"Command color position: {color_pos}", Level.TRACE, Component.COMMAND)
            return index == color_pos
            
        return False
    
    def _execute_parsed_command(self, cmd_name: str, params: List[Any]) -> None:
        """
        Execute a parsed command with its parameters.
        
        Args:
            cmd_name: Name of the command to execute
            params: List of parsed parameters
        """
        handler = self.command_handlers[cmd_name]
        debug(f"Executing {cmd_name} with {len(params)} parameters", 
              Level.DEBUG, Component.COMMAND)
        try:
            handler(*params)
            debug(f"Successfully executed {cmd_name}", Level.DEBUG, Component.COMMAND)
        except Exception as e:
            debug(f"Error executing {cmd_name}: {str(e)}", Level.ERROR, Component.COMMAND)
            raise

    # Command Handlers
    def _handle_plot(self, x: int, y: int, color: str, burnout: int = None):
        """Handle plot command."""
        debug(f"Handling plot command: ({x}, {y}) in {color}", Level.DEBUG, Component.COMMAND)
        self.api.plot(x, y, color, burnout)

    def _handle_draw_line(self, x0: int, y0: int, x1: int, y1: int, color: str, burnout: int = None):
        """Handle draw_line command."""
        debug(f"Handling draw_line command: ({x0}, {y0}) to ({x1}, {y1}) in {color}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_line(x0, y0, x1, y1, color, burnout)  

    def _handle_draw_rectangle(self, x: int, y: int, width: int, height: int, color: str, 
                            fill: bool = False, burnout: int = None):
        """Handle draw_rectangle command."""
        debug(f"Handling draw_rectangle command: ({x}, {y}) {width}x{height} in {color}, fill={fill}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_rectangle(x, y, width, height, color, fill, burnout)

    def _handle_draw_circle(self, x: int, y: int, radius: int, color: str, 
                        fill: bool = False, burnout: int = None):
        """Handle draw_circle command."""
        debug(f"Handling draw_circle command: center({x}, {y}) radius={radius} in {color}, fill={fill}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_circle(x, y, radius, color, fill, burnout)

    def _handle_define_sprite(self, name: str, width: int, height: int):
        """Handle define_sprite command."""
        debug(f"Handling define_sprite command: '{name}' {width}x{height}", 
              Level.DEBUG, Component.COMMAND)
        self.api.sprite_manager.create_sprite(name, width, height)

    def _handle_sprite_draw(self, name: str, cmd: str, *args):
        """Handle sprite_draw command."""
        try:
            debug(f"Handling sprite_draw command: sprite '{name}', command '{cmd}'", 
                Level.DEBUG, Component.COMMAND)
            self.current_sprite_command = cmd
            self.api.draw_to_sprite(name, cmd, *args)
        finally:
            self.current_sprite_command = None

    def _handle_show_sprite(self, name: str, x: float, y: float):
        """Handle show_sprite command."""
        debug(f"Handling show_sprite command: '{name}' at ({x}, {y})", 
              Level.DEBUG, Component.COMMAND)
        self.api.show_sprite(name, x, y)

    def _handle_hide_sprite(self, name: str):
        """Handle hide_sprite command."""
        debug(f"Handling hide_sprite command: '{name}'", Level.DEBUG, Component.COMMAND)
        self.api.hide_sprite(name)

    def _handle_move_sprite(self, name: str, x: float, y: float):
        """Handle move_sprite command."""
        debug(f"Handling move_sprite command: '{name}' to ({x}, {y})", 
              Level.DEBUG, Component.COMMAND)
        self.api.move_sprite(name, x, y)

    def _handle_clear(self):
        """Handle clear command."""
        debug("Handling clear command", Level.DEBUG, Component.COMMAND)
        self.api.clear()

    def _handle_rest(self, duration: float):
        """Handle rest command."""
        debug(f"Handling rest command: {duration}s", Level.DEBUG, Component.COMMAND)
        self.api.rest(duration)

    def _handle_begin_frame(self):
        """Handle begin_frame command."""
        debug("Handling begin_frame command", Level.DEBUG, Component.COMMAND)
        self.api.begin_frame()

    def _handle_end_frame(self):
        """Handle end_frame command."""
        debug("Handling end_frame command", Level.DEBUG, Component.COMMAND)
        self.api.end_frame()

    def _handle_draw_polygon(self, x_center: int, y_center: int, radius: int, sides: int, color: str, 
                        rotation: float = 0, fill: bool = False, burnout: Optional[int] = None):
        """Handle draw_polygon command."""
        debug(f"Handling draw_polygon command: center({x_center}, {y_center}), r={radius}, sides={sides}, rot={rotation}°", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_polygon(x_center, y_center, radius, sides, color, rotation, fill, burnout)

    def _handle_draw_text(self, x: int, y: int, text: str, font_name: str, font_size: int, 
                         color: str, effect: str = "NORMAL", modifier: str = None) -> None:
        """Handle draw_text command"""
        # Ensure text is a string
        text = str(text)  # Convert any numeric text to string

        # Convert string parameters to enums
        text_effect = TextEffect[effect.upper()]
        effect_modifier = EffectModifier[modifier.upper()] if modifier else None
        
        self.api.draw_text(x, y, text, font_name, font_size, color, text_effect, effect_modifier)

    def _handle_clear_text(self, x: int, y: int) -> None:
        """Handle clear_text command"""
        self.api.clear_text(x, y)

    def _handle_dispose_all_sprites(self):
        """Handle dispose_all_sprites command."""
        debug("Starting dispose_all_sprites handler", Level.DEBUG, Component.COMMAND)
        try:
            debug("Calling api.dispose_all_sprites()", Level.DEBUG, Component.COMMAND)
            self.api.dispose_all_sprites()
            debug("Successfully disposed all sprites", Level.DEBUG, Component.COMMAND)
        except Exception as e:
            debug(f"Error in dispose_all_sprites handler: {str(e)}", Level.ERROR, Component.COMMAND)
            raise

    def _handle_sync_queue(self):
        """Handle sync_queue command - exists purely for synchronization"""
        debug("Processing sync_queue", Level.DEBUG, Component.COMMAND)
        pass  # Simply consuming the command is sufficient
