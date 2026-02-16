# File: rgb_matrix_lib/commands.py

import re
from typing import List, Any, Optional, Union
from .debug import debug, Level, Component
from .utils import NAMED_COLORS, get_color_rgb  # Removed parse_color_spec
from .text_effects import TextEffect, EffectModifier
from shared.mplot_protocol import decode_buffer, unpack_mplot_batch
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
            'draw_ellipse': self._handle_draw_ellipse,
            'draw_arc': self._handle_draw_arc,
            'define_sprite': self._handle_define_sprite,
            'endsprite': self._handle_endsprite,
            'sprite_cel': self._handle_sprite_cel,
            'sprite_draw': self._handle_sprite_draw,
            'show_sprite': self._handle_show_sprite,
            'hide_sprite': self._handle_hide_sprite,
            'move_sprite': self._handle_move_sprite,
            'dispose_sprite': self._handle_dispose_sprite,
            'clear': self._handle_clear,
            'rest': self._handle_rest,
            'begin_frame': self._handle_begin_frame,
            'end_frame': self._handle_end_frame,
            'draw_text': self._handle_draw_text,
            'clear_text': self._handle_clear_text,
            'dispose_all_sprites': self._handle_dispose_all_sprites,
            'sync_queue': self._handle_sync_queue,
            'plot_batch': self._handle_plot_batch,
            'set_background': self._handle_set_background,
            'hide_background': self._handle_hide_background,
            'nudge_background': self._handle_nudge_background,
            'set_background_offset': self._handle_set_background_offset,
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
            if command in ['end_frame', 'clear', 'dispose_all_sprites', 'sync_queue', 'endsprite', 'hide_background']:
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
        """
        Parse parameter string into typed values with robust quote and escape handling.
        Properly handles:
        - Quoted strings with commas and special characters
        - Escaped quotes within quoted strings
        - Nested quotes with proper escaping
        """
        if not params_str:
            return []
                
        params = []
        current_param = ""
        in_quotes = False
        escape_next = False
        i = 0
        
        while i < len(params_str):
            char = params_str[i]
            
            # Handle escape sequences
            if escape_next:
                # Add the escaped character as-is
                current_param += char
                escape_next = False
                i += 1
                continue
                
            # Check for escape character
            if char == '\\':
                current_param += char  # Keep the escape character in the parameter
                escape_next = True
                i += 1
                continue
                
            # Handle quotes
            if char == '"':
                current_param += char  # Keep the quote character in the parameter
                if not escape_next:  # Only toggle quote state if not escaped
                    in_quotes = not in_quotes
                i += 1
                continue
                    
            # Handle parameter separation (only outside quotes)
            if char == ',' and not in_quotes:
                param = current_param.strip()
                if param:
                    params.append(self._convert_parameter(param))
                current_param = ""
                i += 1
                continue
                
            # Default: add character to current parameter
            current_param += char
            i += 1
        
        # Add the last parameter
        if current_param.strip():
            params.append(self._convert_parameter(current_param.strip()))
        
        # Debug output
        debug(f"Parsed parameters: {params}", Level.DEBUG, Component.COMMAND)
        
        return params
    
    def _convert_parameter(self, param: str) -> Any:
        """Convert a parameter string to its appropriate type with escape handling."""
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
                # Extract quoted string content and process escape sequences
                inner_text = param[1:-1]
                
                # Process escape sequences
                i = 0
                result = ""
                while i < len(inner_text):
                    if inner_text[i] == '\\' and i + 1 < len(inner_text):
                        # Handle various escape sequences
                        if inner_text[i+1] in ['"', '\\', 'n', 't', 'r']:
                            if inner_text[i+1] == 'n':
                                result += '\n'
                            elif inner_text[i+1] == 't':
                                result += '\t'
                            elif inner_text[i+1] == 'r':
                                result += '\r'
                            else:  # " or \
                                result += inner_text[i+1]
                            i += 2
                            continue
                    # Normal character
                    result += inner_text[i]
                    i += 1
                    
                return result
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
    def _handle_plot(self, x: int, y: int, color: Union[str, int], intensity: int = 100, 
                     burnout: Optional[int] = None, burnout_mode: str = "instant"):
        """Handle plot command."""
        rgb_color = get_color_rgb(color, intensity)
        debug(f"Handling plot command: ({x}, {y}) in {color} at {intensity}% with burnout {burnout if burnout is not None else 'None (permanent)'}, mode={burnout_mode} -> RGB {rgb_color}", 
            Level.DEBUG, Component.COMMAND)
        self.api.plot(x, y, color, intensity, burnout, burnout_mode)

    def _handle_draw_line(self, x0: int, y0: int, x1: int, y1: int, color: Union[str, int], 
                        intensity: int = 100, burnout: Optional[int] = None, burnout_mode: str = "instant"):
        """Handle draw_line command."""
        rgb_color = get_color_rgb(color, intensity)
        debug(f"Handling draw_line command: ({x0}, {y0}) to ({x1}, {y1}) in {color} at {intensity}% with burnout {burnout if burnout is not None else 'None (permanent)'}, mode={burnout_mode}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_line(x0, y0, x1, y1, color, intensity, burnout, burnout_mode)

    def _handle_draw_rectangle(self, x: int, y: int, width: int, height: int, color: Union[str, int], 
                            intensity: int = 100, fill: bool = False, burnout: Optional[int] = None,
                            burnout_mode: str = "instant"):
        """Handle draw_rectangle command."""
        debug(f"Handling draw_rectangle command: ({x}, {y}) {width}x{height} in {color} at {intensity}%, fill={fill}, burnout {burnout if burnout is not None else 'None (permanent)'}, mode={burnout_mode}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_rectangle(x, y, width, height, color, intensity, fill, burnout, burnout_mode)

    def _handle_draw_circle(self, x: int, y: int, radius: int, color: Union[str, int], 
                            intensity: int = 100, fill: bool = False, burnout: Optional[int] = None,
                            burnout_mode: str = "instant"):
        """Handle draw_circle command."""
        debug(f"Handling draw_circle command: center({x}, {y}) radius={radius} in {color} at {intensity}%, fill={fill}, burnout {burnout if burnout is not None else 'None (permanent)'}, mode={burnout_mode}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_circle(x, y, radius, color, intensity, fill, burnout, burnout_mode)

    def _handle_draw_polygon(self, x_center: int, y_center: int, radius: int, sides: int, 
                            color: Union[str, int], intensity: int = 100, rotation: float = 0, 
                            fill: bool = False, burnout: Optional[int] = None, burnout_mode: str = "instant"):
        """Handle draw_polygon command."""
        debug(f"Handling draw_polygon command: center({x_center}, {y_center}), r={radius}, sides={sides}, rot={rotation}°, in {color} at {intensity}%, fill={fill}, burnout {burnout if burnout is not None else 'None (permanent)'}, mode={burnout_mode}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_polygon(x_center, y_center, radius, sides, color, intensity, rotation, fill, burnout, burnout_mode)

    def _handle_draw_ellipse(self, x_center: int, y_center: int, x_radius: int, y_radius: int, 
                        color: Union[str, int], intensity: int = 100, fill: bool = False, 
                        rotation: float = 0, burnout: Optional[int] = None, burnout_mode: str = "instant"):
        """Handle draw_ellipse command."""
        debug(f"Handling draw_ellipse command: center({x_center}, {y_center}), radii=({x_radius}, {y_radius}), "
            f"rotation={rotation}° in {color} at {intensity}%, fill={fill}, "
            f"burnout {burnout if burnout is not None else 'None (permanent)'}, mode={burnout_mode}", 
            Level.DEBUG, Component.COMMAND)
        self.api.draw_ellipse(x_center, y_center, x_radius, y_radius, color, 
                            intensity, fill, rotation, burnout, burnout_mode)

    def _handle_draw_arc(self, x1: int, y1: int, x2: int, y2: int, bulge: float,
                         color: Union[str, int], intensity: int = 100, fill: bool = False,
                         burnout: Optional[int] = None, burnout_mode: str = "instant"):
        """Handle draw_arc command."""
        debug(f"Handling draw_arc command: ({x1}, {y1}) to ({x2}, {y2}), bulge={bulge}, "
              f"in {color} at {intensity}%, fill={fill}, "
              f"burnout {burnout if burnout is not None else 'None (permanent)'}, mode={burnout_mode}", 
              Level.DEBUG, Component.COMMAND)
        self.api.draw_arc(x1, y1, x2, y2, bulge, color, intensity, fill, burnout, burnout_mode)
        
    def _handle_define_sprite(self, name: str, width: int, height: int):
        """Handle define_sprite command - begins sprite template definition."""
        debug(f"Handling define_sprite command: '{name}' {width}x{height}", 
              Level.DEBUG, Component.COMMAND)
        self.api.sprite_manager.begin_sprite_definition(name, width, height)

    def _handle_endsprite(self):
        """Handle endsprite command - ends sprite template definition."""
        debug("Handling endsprite command", Level.DEBUG, Component.COMMAND)
        self.api.sprite_manager.end_sprite_definition()

    def _handle_sprite_cel(self, cel_index: Optional[int] = None):
        """
        Handle sprite_cel command - start a new animation cel.
        
        Args:
            cel_index: Explicit cel index, or None for auto-assignment
        """
        debug(f"Handling sprite_cel command: index={cel_index if cel_index is not None else 'auto'}", 
              Level.DEBUG, Component.COMMAND)
        self.api.sprite_manager.start_cel(cel_index)

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
        elif cmd == 'draw_ellipse' and len(args) >= 5:
            x, y, x_radius, y_radius, color = args[:5]
            intensity = int(args[5]) if len(args) > 5 else 100
            fill = args[6] if len(args) > 6 else False
            rotation = float(args[7]) if len(args) > 7 else 0
            self.api.draw_to_sprite(name, cmd, x, y, x_radius, y_radius, color, intensity, fill, rotation)
        elif cmd == 'draw_arc' and len(args) >= 6:
            x1, y1, x2, y2, arc_height, color = args[:6]
            intensity = int(args[6]) if len(args) > 6 else 100
            fill = args[7] if len(args) > 7 else False
            self.api.draw_to_sprite(name, cmd, x1, y1, x2, y2, arc_height, color, intensity, fill)
        elif cmd == 'clear':
            self.api.draw_to_sprite(name, cmd)
        else:
            debug(f"Unsupported sprite command: {cmd}", Level.ERROR, Component.COMMAND)
            raise ValueError(f"Unsupported sprite command: {cmd}")

    def _handle_show_sprite(self, name: str, x: float, y: float, instance_id: int = 0,
                            z_index: int = 0, cel_idx: Optional[int] = None):
        """
        Handle show_sprite command with optional instance ID, z_index, and cel index.
        
        Args:
            name: Sprite template name
            x, y: Position on screen
            instance_id: Instance identifier (default 0)
            z_index: Z-order for layering (default 0)
            cel_idx: Which animation cel to display. None preserves current cel for existing instances.
        """
        debug(f"Handling show_sprite command: '{name}' instance {instance_id} at ({x}, {y}) z={z_index}" +
              (f" cel={cel_idx}" if cel_idx is not None else " (preserve cel)"), 
            Level.DEBUG, Component.COMMAND)
        self.api.show_sprite(name, x, y, instance_id, z_index, cel_idx)

    def _handle_hide_sprite(self, name: str, instance_id: int = 0):
        """Handle hide_sprite command with optional instance ID."""
        debug(f"Handling hide_sprite command: '{name}' instance {instance_id}", 
            Level.DEBUG, Component.COMMAND)
        self.api.hide_sprite(name, instance_id)

    def _handle_move_sprite(self, name: str, x: float, y: float, instance_id: int = 0,
                            cel_idx: Optional[int] = None):
        """
        Handle move_sprite command with optional cel index.
        
        Args:
            name: Sprite template name
            x, y: New position on screen
            instance_id: Instance identifier (default 0)
            cel_idx: If specified, set to this cel. If None, auto-advance to next cel.
        """
        debug(f"Handling move_sprite command: '{name}' to ({x}, {y}) instance {instance_id}" +
              (f" cel={cel_idx}" if cel_idx is not None else " (auto-advance)"), 
            Level.DEBUG, Component.COMMAND)
        self.api.move_sprite(name, x, y, instance_id, cel_idx)

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
                            modifier: Optional[str] = None):
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

    # Background Command Handlers
    def _handle_set_background(self, sprite_name: str, cel_index: int = 0):
        """Handle set_background command."""
        debug(f"Setting background to sprite '{sprite_name}' cel {cel_index}",
              Level.DEBUG, Component.COMMAND)
        self.api.set_background(sprite_name, cel_index)

    def _handle_hide_background(self):
        """Handle hide_background command."""
        debug("Hiding background", Level.DEBUG, Component.COMMAND)
        self.api.hide_background()

    def _handle_nudge_background(self, dx: int, dy: int, cel_index: Optional[int] = None):
        """Handle nudge_background command."""
        debug(f"Nudging background by ({dx}, {dy})" +
              (f" to cel {cel_index}" if cel_index is not None else " (auto-advance)"),
              Level.DEBUG, Component.COMMAND)
        self.api.nudge_background(dx, dy, cel_index)

    def _handle_set_background_offset(self, x: int, y: int, cel_index: Optional[int] = None):
        """Handle set_background_offset command."""
        debug(f"Setting background offset to ({x}, {y})" +
              (f" cel {cel_index}" if cel_index is not None else " (auto-advance)"),
              Level.DEBUG, Component.COMMAND)
        self.api.set_background_offset(x, y, cel_index)

    def _handle_plot_batch(self, encoded_data: str):
        """Handle plot_batch command with multiple packed plots."""
        debug(f"Handling plot_batch command with encoded data length: {len(encoded_data)}", 
            Level.DEBUG, Component.COMMAND)
        
        try:
            # Decode binary data
            binary_data = decode_buffer(encoded_data)
            plots = list(unpack_mplot_batch(binary_data))
            
            # Single atomic operation
            self.api.plot_batch(plots)
            
            debug(f"Successfully executed batch of {len(plots)} plots atomically", 
                Level.DEBUG, Component.COMMAND)
                
        except Exception as e:
            debug(f"Error processing plot_batch: {str(e)}", Level.ERROR, Component.COMMAND)
            raise ValueError(f"plot_batch execution failed: {str(e)}")