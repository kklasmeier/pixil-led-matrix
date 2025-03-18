# File: rgb_matrix_lib/commands.py

import re
from typing import List, Any, Optional, Union
from .debug import debug, Level, Component
from .utils import NAMED_COLORS, get_color_rgb  # Removed parse_color_spec
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
            'draw_polygon': self._handle_draw_polygon,
            'define_sprite': self._handle_define_sprite,
            'sprite_draw': self._handle_sprite_draw,
            'show_sprite': self._handle_show_sprite,
            'hide_sprite': self._handle_hide_sprite,
            'move_sprite': self._handle_move_sprite,
            'dispose_sprite': self._handle_dispose_sprite,  # New command
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
            if command in ['end_frame', 'clear', 'dispose_all_sprites', 'sync_queue']:
                debug(f"Executing simple command: {command}", Level.DEBUG, Component.COMMAND)
                self.current_command = command
                handler = self.command_handlers.get(command)
                if handler:
                    handler()
                else:
                    raise ValueError(f"No handler found for command: {command}")
                return

            cmd_name, params = self._parse_command(command)
            self._execute_parsed_command(cmd_name, params)
            debug("Command executed successfully", Level.DEBUG, Component.COMMAND)
        finally:
            self.current_command = None
            
    def _parse_command(self, command: str) -> tuple[str, List[Any]]:
        """Parse a command string into name and parameters."""
        match = re.match(r'(\w+)\((.*)\)', command)
        if not match:
            debug(f"Invalid command format: {command}", Level.ERROR, Component.COMMAND)
            raise ValueError(f"Invalid command format: {command}")
                
        cmd_name, params_str = match.groups()
        self.current_command = cmd_name
        debug(f"Parsed command '{cmd_name}' with parameters: {params_str}",
              Level.TRACE, Component.COMMAND)

        params = self._parse_parameters(params_str)
        return cmd_name, params

    def _parse_parameters(self, params_str: str) -> List[Any]:
        """Parse parameter string into typed values."""
        if not params_str:
            return []
                
        params = []
        current_param = ""
        in_quotes = False
        i = 0
        
        while i < len(params_str):
            char = params_str[i]
            
            if char == '"':
                if in_quotes:
                    if i + 1 < len(params_str) and params_str[i + 1] == '"':
                        current_param += '"'
                        i += 2
                        continue
                    else:
                        in_quotes = False
                        i += 1
                        continue
                else:
                    in_quotes = True
                    i += 1
                    continue
                    
            if char == ',' and not in_quotes:
                param = current_param.strip()
                if param:
                    params.append(self._convert_parameter(param))
                current_param = ""
                i += 1
                continue
                
            current_param += char
            i += 1
        
        if current_param.strip():
            params.append(self._convert_parameter(current_param.strip()))
        
        return params

    def _convert_parameter(self, param: str) -> Any:
        """Convert a parameter string to its appropriate type."""
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
            # Return as string for named colors, text, etc.
            if param.startswith('"') and param.endswith('"'):
                inner_text = param[1:-1].replace('""', '"')
                return inner_text
            return param

    def _execute_parsed_command(self, cmd_name: str, params: List[Any]) -> None:
        """Execute a parsed command with its parameters."""
        handler = self.command_handlers[cmd_name]
        debug(f"Executing {cmd_name} with {len(params)} parameters: {params}", 
            Level.DEBUG, Component.COMMAND)
        try:
            handler(*params)
            debug(f"Successfully executed {cmd_name}", Level.DEBUG, Component.COMMAND)
        except TypeError as e:
            debug(f"Type error executing {cmd_name}: {str(e)}. Params: {params}", 
                Level.ERROR, Component.COMMAND)
            raise ValueError(f"Type error in {cmd_name}: {str(e)}")
        except Exception as e:
            debug(f"Error executing {cmd_name}: {str(e)}", Level.ERROR, Component.COMMAND)
            raise

    # Command Handlers
    def _handle_plot(self, x: int, y: int, color: Union[str, int], intensity: int = 100, burnout: int = None):
        """Handle plot command."""
        rgb_color = get_color_rgb(color, intensity)
        # Changed: No default burnout - if None is specified, it stays None (never burns out)
        debug(f"Handling plot command: ({x}, {y}) in {color} at {intensity}% with burnout {burnout if burnout is not None else 'None (permanent)'} -> RGB {rgb_color}", 
            Level.DEBUG, Component.COMMAND)
        self.api.plot(x, y, color, intensity, burnout)

    def _handle_draw_line(self, x0: int, y0: int, x1: int, y1: int, color: Union[str, int], 
                        intensity: int = 100, burnout: int = None):
        """Handle draw_line command."""
        rgb_color = get_color_rgb(color, intensity)
        # Changed: No default burnout - if None is specified, it stays None (never burns out)
        debug(f"Handling draw_line command: ({x0}, {y0}) to ({x1}, {y1}) in {color} at {intensity}% with burnout {burnout if burnout is not None else 'None (permanent)'}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_line(x0, y0, x1, y1, color, intensity, burnout)

    def _handle_draw_rectangle(self, x: int, y: int, width: int, height: int, color: Union[str, int], 
                            intensity: int = 100, fill: bool = False, burnout: Optional[int] = None):
        """Handle draw_rectangle command."""
        debug(f"Handling draw_rectangle command: ({x}, {y}) {width}x{height} in {color} at {intensity}%, fill={fill}, burnout {burnout if burnout is not None else 'None (permanent)'}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_rectangle(x, y, width, height, color, intensity, fill, burnout)

    def _handle_draw_circle(self, x: int, y: int, radius: int, color: Union[str, int], 
                            intensity: int = 100, fill: bool = False, burnout: Optional[int] = None):
        """Handle draw_circle command."""
        debug(f"Handling draw_circle command: center({x}, {y}) radius={radius} in {color} at {intensity}%, fill={fill}, burnout {burnout if burnout is not None else 'None (permanent)'}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_circle(x, y, radius, color, intensity, fill, burnout)

    def _handle_draw_polygon(self, x_center: int, y_center: int, radius: int, sides: int, 
                            color: Union[str, int], intensity: int = 100, rotation: float = 0, 
                            fill: bool = False, burnout: Optional[int] = None):
        """Handle draw_polygon command."""
        debug(f"Handling draw_polygon command: center({x_center}, {y_center}), r={radius}, sides={sides}, rot={rotation}°, in {color} at {intensity}%, fill={fill}, burnout {burnout if burnout is not None else 'None (permanent)'}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_polygon(x_center, y_center, radius, sides, color, intensity, rotation, fill, burnout)

    def _handle_define_sprite(self, name: str, width: int, height: int):
        """Handle define_sprite command."""
        debug(f"Handling define_sprite command: '{name}' {width}x{height}", 
              Level.DEBUG, Component.COMMAND)
        self.api.sprite_manager.create_sprite(name, width, height)

    def _handle_sprite_draw(self, name: str, cmd: str, *args):
        """Handle sprite_draw command."""
        debug(f"Handling sprite_draw command: sprite '{name}', command '{cmd}' with args {args}", 
            Level.DEBUG, Component.COMMAND)
        if cmd == 'plot' and len(args) >= 3:
            x, y, color = args[:3]
            intensity = int(args[3]) if len(args) > 3 else 100
            self.api.draw_to_sprite(name, cmd, x, y, color, intensity)
        elif cmd == 'draw_line' and len(args) >= 5:
            x0, y0, x1, y1, color = args[:5]
            intensity = int(args[5]) if len(args) > 5 else 100
            self.api.draw_to_sprite(name, cmd, x0, y0, x1, y1, color, intensity)
        elif cmd == 'draw_rectangle' and len(args) >= 5:
            x, y, width, height, color = args[:5]
            intensity = int(args[5]) if len(args) > 5 else 100
            fill = args[6] if len(args) > 6 else False
            self.api.draw_to_sprite(name, cmd, x, y, width, height, color, intensity, fill)
        elif cmd == 'draw_circle' and len(args) >= 4:
            x, y, radius, color = args[:4]
            intensity = int(args[4]) if len(args) > 4 else 100
            fill = args[5] if len(args) > 5 else False
            self.api.draw_to_sprite(name, cmd, x, y, radius, color, intensity, fill)
        elif cmd == 'draw_polygon' and len(args) >= 5:
            x, y, radius, sides, color = args[:5]
            intensity = int(args[5]) if len(args) > 5 else 100
            rotation = args[6] if len(args) > 6 else 0
            fill = args[7] if len(args) > 7 else False
            self.api.draw_to_sprite(name, cmd, x, y, radius, sides, color, intensity, rotation, fill)
        elif cmd == 'clear':
            self.api.draw_to_sprite(name, cmd)
        else:
            debug(f"Unsupported sprite command: {cmd}", Level.ERROR, Component.COMMAND)
            raise ValueError(f"Unsupported sprite command: {cmd}")

    def _handle_show_sprite(self, name: str, x: float, y: float, instance_id: int = 0):
        """Handle show_sprite command with optional instance ID."""
        debug(f"Handling show_sprite command: '{name}' instance {instance_id} at ({x}, {y})", 
            Level.DEBUG, Component.COMMAND)
        self.api.show_sprite(name, x, y, instance_id)

    def _handle_hide_sprite(self, name: str, instance_id: int = 0):
        """Handle hide_sprite command with optional instance ID."""
        debug(f"Handling hide_sprite command: '{name}' instance {instance_id}", 
            Level.DEBUG, Component.COMMAND)
        self.api.hide_sprite(name, instance_id)

    def _handle_move_sprite(self, name: str, x: float, y: float, instance_id: int = 0):
        """Handle move_sprite command with optional instance ID."""
        debug(f"Handling move_sprite command: '{name}' instance {instance_id} to ({x}, {y})", 
            Level.DEBUG, Component.COMMAND)
        self.api.move_sprite(name, x, y, instance_id)

    def _handle_dispose_sprite(self, name: str, instance_id: int = 0):
        """Handle new dispose_sprite command to remove a specific instance."""
        debug(f"Handling dispose_sprite command: '{name}' instance {instance_id}", 
            Level.DEBUG, Component.COMMAND)
        self.api.dispose_sprite_instance(name, instance_id)

    def _handle_clear(self):
        """Handle clear command."""
        debug("Handling clear command", Level.DEBUG, Component.COMMAND)
        self.api.clear()

    def _handle_rest(self, duration: float):
        """Handle rest command."""
        debug(f"Handling rest command: {duration}s", Level.DEBUG, Component.COMMAND)
        self.api.rest(duration)

    def _handle_begin_frame(self, preserve_changes: bool = False):
        """Handle begin_frame command."""
        debug(f"Handling begin_frame command with preserve_changes={preserve_changes}", 
              Level.DEBUG, Component.COMMAND)
        self.api.begin_frame(preserve_changes)

    def _handle_end_frame(self):
        """Handle end_frame command."""
        debug("Handling end_frame command", Level.DEBUG, Component.COMMAND)
        self.api.end_frame()

    def _handle_draw_text(self, x: int, y: int, text: Any, font_name: str, font_size: int, 
                            color: Union[str, int], intensity: int = 100, effect: str = "NORMAL", 
                            modifier: str = None):
            """Handle draw_text command."""
            debug(f"Handling draw_text command: '{text}' at ({x}, {y}) in {color} at {intensity}%", 
                Level.DEBUG, Component.COMMAND)
            text = str(text)  # Convert to string
            self.api.draw_text(x, y, text, font_name, font_size, color, intensity, effect, modifier)

    def _handle_clear_text(self, x: int, y: int) -> None:
        """Handle clear_text command."""
        self.api.clear_text(x, y)

    def _handle_dispose_all_sprites(self):
        """Handle dispose_all_sprites command."""
        debug("Starting dispose_all_sprites handler", Level.DEBUG, Component.COMMAND)
        try:
            self.api.dispose_all_sprites()
            debug("Successfully disposed all sprites", Level.DEBUG, Component.COMMAND)
        except Exception as e:
            debug(f"Error in dispose_all_sprites handler: {str(e)}", Level.ERROR, Component.COMMAND)
            raise

    def _handle_sync_queue(self):
        """Handle sync_queue command - exists purely for synchronization."""
        debug("Processing sync_queue", Level.DEBUG, Component.COMMAND)
        pass