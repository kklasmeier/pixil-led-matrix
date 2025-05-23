import re
import sys
import gc
import signal  # At top with other imports
import time
from queue import Empty
from shared import QueueManager
from rgb_matrix_lib import execute_command
from pixil_utils.debug import (DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE, DEBUG_LEVEL, set_debug_level, debug_print, current_command)
from pixil_utils.math_functions import (MATH_FUNCTIONS, random_float, has_math_expression, evaluate_math_expression, evaluate_condition)
from pixil_utils.file_manager import PixilFileManager
from pixil_utils.parameter_types import (PARAMETER_TYPES, validate_command_params)
from pixil_utils.expression_parser import format_parameter
from pixil_utils import (ScriptManager, parse_args, 
                        # Timer management
                        initialize_timer, is_time_expired, clear_timer, force_timer_expired,
                        # Debug management 
                        set_debug_level,
                        # Terminal handling
                        initialize_terminal, start_terminal, 
                        stop_terminal, check_spacebar)
from pixil_utils.array_manager import PixilArray
from collections import OrderedDict  # Make sure this is imported

def is_headless():
    """Detect if running in a headless/non-interactive environment"""
    import os
    try:
        # Check if stdin is connected to a terminal
        return not os.isatty(sys.stdin.fileno())
    except:
        # If checking fails, assume headless
        return True
    
# Override terminal functions if in headless mode
if is_headless():
    print("Detected headless mode - disabling terminal interactions")
    # These overrides need to happen before the functions are imported elsewhere
    from pixil_utils import terminal_handler
    # Replace functions with no-op versions
    terminal_handler.initialize_terminal = lambda: None
    terminal_handler.start_terminal = lambda: None
    terminal_handler.stop_terminal = lambda: None
    terminal_handler.check_spacebar = lambda: False

# Performance metrics tracking
_metrics = {
    'commands_processed': 0,      # Total drawing commands processed
    'script_lines_processed': 0,   # Total script lines processed 
    'start_time': 0,              # Script start timestamp
    'active_time': 0,             # Time excluding queue pauses
    'pause_start': None,          # Timestamp when queue pause began (or None)
    'total_pause_time': 0,        # Total time spent waiting on full queue
    'enabled': True               # Toggle for enabling/disabling metrics
}



#Variable cache
_VAR_FORMAT_CACHE = OrderedDict()
_VAR_CACHE_SIZE = 1024
_VAR_CACHE_HITS = 0
_VAR_CACHE_MISSES = 0
_FAST_PATH_HITS = 0
_FAST_PATH_TOTAL = 0
_FAST_PATH_ENABLED = True 

set_debug_level(DEBUG_OFF)  # Default debug level

# Pre-compiled regex patterns for improved performance
ARRAY_CREATE_PATTERN = re.compile(r'create_array\((\w+),\s*(.+?)(?:\s*,\s*(\w+))?\)')
ARRAY_ASSIGN_PATTERN = re.compile(r'(v_\w+)\[(.+?)\]\s*=\s*([^#]+)')
SPRITE_DEF_PATTERN = re.compile(r'define_sprite\((\w+),\s*(.+?),\s*(.+?)\)')
COMMAND_PATTERN = re.compile(r'(\w+)\((.*)\)')
SPRITE_OP_PATTERN = re.compile(r'(show|hide|move|dispose)_sprite\((\w+)(?:,\s*(.+?)(?:,\s*(.+?))?(?:,\s*(.+?))?)?\)')
PROCEDURE_DEF_PATTERN = re.compile(r'def (\w+) {')
PROCEDURE_CALL_PATTERN = re.compile(r'call (\w+)')
FRAME_PARAM_PATTERN = re.compile(r'begin_frame\((.*)\)')
FOR_LOOP_PATTERN = re.compile(r'for (v_\w+) in \((.+?), (.+?), (.+?)\)')
WHILE_LOOP_PATTERN = re.compile(r'while (.+?) then')
IF_PATTERN = re.compile(r'if (.+?) then')
RANDOM_PATTERN = re.compile(r'random\s*\(\s*(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)\s*,\s*(\d+)\s*\)')

# Initialize file manager
file_manager = PixilFileManager()

def reset_fast_path_stats():
    """Reset fast path statistics for new script."""
    global _FAST_PATH_HITS, _FAST_PATH_TOTAL
    _FAST_PATH_HITS = 0
    _FAST_PATH_TOTAL = 0

def initialize_metrics():
    """Reset metrics at start of script."""
    global _metrics
    _metrics['commands_processed'] = 0
    _metrics['script_lines_processed'] = 0
    _metrics['start_time'] = time.time()
    _metrics['active_time'] = 0
    _metrics['pause_start'] = None
    _metrics['total_pause_time'] = 0

def report_metrics(reason="complete"):
    """Calculate and display metrics."""
    if not _metrics['enabled']:
        return
    
    # Calculate active time (excluding pauses)
    if _metrics['pause_start'] is not None:
        # Currently paused - add current pause duration
        current_pause = time.time() - _metrics['pause_start']
        total_paused = _metrics['total_pause_time'] + current_pause
    else:
        total_paused = _metrics['total_pause_time']
    
    # Total time minus pauses
    total_time = time.time() - _metrics['start_time']
    active_time = total_time - total_paused
    if active_time <= 0:
        active_time = 0.001  # Avoid division by zero
    
    # Calculate performance metrics
    commands_per_second = _metrics['commands_processed'] / active_time
    lines_per_second = _metrics['script_lines_processed'] / active_time
    
    print(f"\n--- Pixil Performance Metrics ({reason}) ---")
    print(f"Commands executed: {_metrics['commands_processed']:,}")
    print(f"Script lines processed: {_metrics['script_lines_processed']:,}")
    print(f"Total execution time: {total_time:.3f} seconds")
    print(f"Active execution time: {active_time:.3f} seconds")
    if total_paused > 0:
        print(f"Queue wait time: {total_paused:.3f} seconds (excluded from rates)")
        pause_percent = (total_paused / total_time) * 100
        print(f"Wait time percentage: {pause_percent:.1f}%")
    print(f"Performance: {commands_per_second:.2f} commands/second")
    print(f"Script processing: {lines_per_second:.2f} lines/second")
    print("--------------------------------------------")
    print("Fast Path Optimization Statistics")
    global _FAST_PATH_HITS, _FAST_PATH_TOTAL
    
    if _FAST_PATH_TOTAL > 0:
        hit_rate = (_FAST_PATH_HITS / _FAST_PATH_TOTAL) * 100
        miss_count = _FAST_PATH_TOTAL - _FAST_PATH_HITS
        
        print(f"Phase 1 Fast Path Statistics:")
        print(f"  Simple variable lookups attempted: {_FAST_PATH_TOTAL:,}")
        print(f"  Fast path hits: {_FAST_PATH_HITS:,} ({hit_rate:.1f}%)")
        print(f"  Fast path misses: {miss_count:,} ({100-hit_rate:.1f}%)")
        
        if _FAST_PATH_HITS > 0:
            # Estimate time savings (assuming 10x speedup for fast path)
            estimated_savings = (_FAST_PATH_HITS * 30) / 1000000  # 30 microseconds saved per hit
            print(f"  Estimated time saved: {estimated_savings:.3f} seconds")
    else:
        print("Phase 1 Fast Path: No simple variable lookups detected")
    print("--------------------------------------------")

def on_queue_pause():
    """Called when the command queue becomes full."""
    global _metrics
    if _metrics['pause_start'] is None:
        _metrics['pause_start'] = time.time()

def on_queue_resume():
    """Called when the command queue accepts commands again after being full."""
    global _metrics
    if _metrics['pause_start'] is not None:
        pause_duration = time.time() - _metrics['pause_start']
        _metrics['total_pause_time'] += pause_duration
        _metrics['pause_start'] = None

class SpriteContext:
    """Tracks state during sprite definition and commands"""
    def __init__(self):
        self.in_sprite_definition = False
        self.current_sprite = None
        self.sprite_commands = []

def process_script(filename, execute_func=None):
    if execute_func is None:
        raise ValueError("execute_func must be provided")
    normal_exit = True

    global current_command, variables, frame_commands, in_frame_mode
    current_command = None  # Reset at script start

    debug_print(f"Opening script file: {filename}", DEBUG_CONCISE)

    # Initialize metrics
    initialize_metrics()
    reset_fast_path_stats()

    # Get queue instance
    queue = QueueManager.get_instance()

    # Set up queue callbacks
    queue.set_pause_callbacks(
        on_pause=on_queue_pause,
        on_resume=on_queue_resume
    )

    # Reset throttle factor at start of script
    queue.reset_throttle()
    
    # Initialize script environment
    global variables, frame_commands, in_frame_mode
    variables = {}
    procedures = {}
    sprite_context = SpriteContext()  # Add sprite context
    frame_commands = []  # Add frame command buffer
    in_frame_mode = False  # Add frame mode tracking

    # Preprocess lines to remove comments
    def preprocess_lines(filename):
        with open(filename, 'r') as f:
            return [line.split('#', 1)[0].strip() for line in f if line.split('#', 1)[0].strip()]
        
    # Define helper functions after variables are initialized
    def execute_command(cmd):
        """Queue command with appropriate timing"""
        if DEBUG_LEVEL >= DEBUG_SUMMARY:
            debug_print(f"Queueing command: {cmd}", DEBUG_SUMMARY)
        
        # Commands that should execute instantly (no delay)
        force_instant = any([
            cmd == 'begin_frame',
            cmd == 'end_frame',
            cmd.startswith('define_sprite'),
            cmd.startswith('sprite_draw'),
            cmd == 'endsprite',
            sprite_context.in_sprite_definition,  # All commands in sprite definition
            in_frame_mode,  # All commands in frame mode
        ])

        if DEBUG_LEVEL >= DEBUG_SUMMARY:
            debug_print(f"Sending to queue: {cmd} (instant: {force_instant})", DEBUG_SUMMARY)
        queue.put_command(cmd, force_instant)

    def store_frame_command(cmd):
        """Store command if in frame mode, execute immediately if not"""
        global _metrics
        _metrics['commands_processed'] += 1  # Add this line
        if in_frame_mode:
            frame_commands.append(cmd)
        else:
            execute_command(cmd)

    def parse_value(value, command_name, param_position):
        """
        Parse and format a parameter value, handling variables and math expressions.
        Uses optimized LRU caching for variable lookups.
        
        Args:
            value: The parameter value to parse
            command_name: Name of the command being processed
            param_position: Position of parameter in command
            
        Returns:
            Formatted value ready for command string
        """
        global _VAR_FORMAT_CACHE, _VAR_CACHE_HITS, _VAR_CACHE_MISSES
        
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Parsing value: {value} ({type(value)})", DEBUG_VERBOSE)
            debug_print(f"Command: {command_name}, Position: {param_position}", DEBUG_VERBOSE)
        
        # Handle direct value types (non-strings)
        if not isinstance(value, str):
            return format_parameter(value, command_name, param_position, variables)
            
        value = value.strip()
        
        # Handle quoted strings directly
        if value.startswith('"') and value.endswith('"'):
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Quoted string detected: {value}", DEBUG_VERBOSE)
            return format_parameter(value, command_name, param_position, variables)

        # ===== PHASE 1 OPTIMIZATION: FAST PATH FOR SIMPLE VARIABLES =====
        if (isinstance(value, str) and 
            value.startswith('v_') and 
            len(value) > 2 and
            not any(c in value for c in '+-*/()[]&')):
            
            # Track that we attempted the fast path
            global _FAST_PATH_HITS, _FAST_PATH_TOTAL, _FAST_PATH_ENABLED
            
            if _FAST_PATH_ENABLED:
                _FAST_PATH_TOTAL += 1
                
                # This is a simple variable reference like "v_x" or "v_color"
                if value in variables:
                    _FAST_PATH_HITS += 1
                    var_value = variables[value]
                    
                    # Use format_parameter for proper type conversion and formatting
                    result = format_parameter(var_value, command_name, param_position, variables)
                    
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Fast path variable lookup: {value} -> {var_value} -> {result}", DEBUG_VERBOSE)
                    
                    return result
                else:
                    # Variable not found - let the normal path handle the error
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Variable {value} not found, falling back to normal path", DEBUG_VERBOSE)
        # ===== END PHASE 1 OPTIMIZATION =====    

        # Fast path for variable references (very common in scripts)
        if value.startswith('v_') and not has_math_expression(value):
            # Create cache key: (variable_name, command, position)
            cache_key = (value, command_name, param_position)
            
            # Check cache first
            if cache_key in _VAR_FORMAT_CACHE:
                _VAR_CACHE_HITS += 1
                # Move to end of OrderedDict (most recently used)
                result = _VAR_FORMAT_CACHE.pop(cache_key)
                _VAR_FORMAT_CACHE[cache_key] = result
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Variable cache hit: {value} -> {result}", DEBUG_VERBOSE)
                return result
            
            _VAR_CACHE_MISSES += 1
            
            # Not in cache, look up and format
            if value in variables:
                var_value = variables[value]
                result = format_parameter(var_value, command_name, param_position, variables)
                
                # Cache the result with LRU eviction
                if len(_VAR_FORMAT_CACHE) >= _VAR_CACHE_SIZE:
                    # Remove oldest item (first in OrderedDict)
                    _VAR_FORMAT_CACHE.popitem(last=False)
                _VAR_FORMAT_CACHE[cache_key] = result
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Variable cache miss: {value} -> {result}", DEBUG_VERBOSE)
                return result
        
        # Special case for draw_text's font_name (position 3)
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Checking font_name condition: command_name={command_name}, position={param_position}", DEBUG_VERBOSE)
        if command_name == 'draw_text' and param_position == 3:
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Inside font_name block for: {value}", DEBUG_VERBOSE)
            starts_with_v = value.startswith('v_')
            has_math_chars = any(c in value for c in '+-*/()')  # Direct check for debugging
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Raw has_math_chars: {has_math_chars}", DEBUG_VERBOSE)
            # Only treat as expression if it's a variable or has clear math context
            if starts_with_v or (has_math_chars and any(c.isdigit() or c in 'v_' for c in value)):
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Font_name is variable or expression: {value}", DEBUG_VERBOSE)
                return format_parameter(value, command_name, param_position, variables)
            else:
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Treating as font name literal: {value}", DEBUG_VERBOSE)
                return f'"{value}"'
        
        # Handle simple variable reference or math expression
        if value.startswith('v_') and not has_math_expression(value):
            val = variables.get(value)
            if val is None:
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Warning: Variable {value} not found, defaulting to 0", DEBUG_VERBOSE)
                val = 0
        else:
            val = value
            
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Passing to format_parameter: {val}", DEBUG_VERBOSE)
        return format_parameter(val, command_name, param_position, variables)

    def safe_eval(expr, vars):
        try:
            # Check for the random function pattern
            random_match = RANDOM_PATTERN.match(expr)
            if random_match:
                min_val = float(random_match.group(1))
                max_val = float(random_match.group(2))
                precision = int(random_match.group(3))
                return random_float(min_val, max_val, precision)
            
            # Add math functions to evaluation environment
            eval_vars = vars.copy()
            eval_vars.update(MATH_FUNCTIONS)
            
            return eval(expr, {"__builtins__": None}, eval_vars)
        except NameError as e:
            debug_print(f"Error: Undefined variable in expression '{expr}': {e}", DEBUG_SUMMARY)
            return 0
        except Exception as e:
            debug_print(f"Error evaluating expression '{expr}': {e}", DEBUG_SUMMARY)
            return 0

    # Add new array helper functions here
    def process_array_creation(line):
        """Process array creation command.
        Handles both standard and typed array creation:
            create_array(v_name, size)           # Default numeric array
            create_array(v_name, size, string)   # String array
            create_array(v_name, size, numeric)  # Explicit numeric array
        """
        # Updated regex to handle optional type parameter
        match = ARRAY_CREATE_PATTERN.match(line)
        if match:
            array_name = match.group(1)
            size_expr = match.group(2).strip()
            array_type = match.group(3)  # Will be None if not specified
            
            debug_print(f"Processing array creation: {array_name} size={size_expr} type={array_type}", DEBUG_VERBOSE)
            
            # Validate array name
            if not array_name.startswith('v_'):
                raise ValueError(f"Array name must start with 'v_', got {array_name}\nCommand: {current_command}")
            
            # Evaluate size expression
            try:
                size = evaluate_math_expression(size_expr, variables)
                if not isinstance(size, (int, float)):
                    raise ValueError(f"Array size must be a number, got {type(size)}\nCommand: {current_command}")
                
                # Handle array type
                if array_type is not None:
                    if array_type not in ('string', 'numeric'):
                        raise ValueError(f"Invalid array type: {array_type}. Must be 'string' or 'numeric'\nCommand: {current_command}")
                else:
                    array_type = 'numeric'  # Default type if not specified
                
                # Create array with specified or default type
                variables[array_name] = PixilArray(int(size), array_type)
                debug_print(f"Created {array_type} array {array_name}[{size}]", DEBUG_VERBOSE)
                return True
                
            except Exception as e:
                raise ValueError(f"Error creating array: {str(e)}\nCommand: {current_command}")
        return False

    def process_array_assignment(line):
        """Process array assignment like v_array[index] = value."""
        # Old pattern: r'(v_\w+)\[(.+?)\]\s*=\s*(.+)'
        # New pattern that handles comments
        match = ARRAY_ASSIGN_PATTERN.match(line)
        if match:
            array_name = match.group(1)
            index_expr = match.group(2)
            value_expr = match.group(3).strip()  # Strip to remove trailing spaces
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Processing array assignment: {array_name}[{index_expr}] = {value_expr}", DEBUG_VERBOSE)
            
            try:
                # Get array
                if array_name not in variables:
                    raise ValueError(f"Array '{array_name}' not found")
                array = variables[array_name]
                if not isinstance(array, PixilArray):
                    raise ValueError(f"Variable '{array_name}' is not an array")
                
                # Evaluate index
                index = evaluate_math_expression(index_expr, variables)
                if not isinstance(index, (int, float)):
                    raise ValueError(f"Array index must be a number, got {type(index)}")
                
                # Handle value based on array type
                if array.get_type() == 'string':
                    # Handle string value
                    if value_expr.startswith('"') and value_expr.endswith('"'):
                        value = value_expr  # Keep quotes for string array assignment
                    elif value_expr.startswith("'") and value_expr.endswith("'"):
                        value = value_expr  # Keep quotes for string array assignment
                    elif value_expr.startswith('v_'):
                        # Handle variable value
                        if value_expr not in variables:
                            raise ValueError(f"Variable '{value_expr}' not found")
                        value = variables[value_expr]
                        if not isinstance(value, str):
                            raise ValueError(f"Cannot assign non-string value to string array")
                    else:
                        raise ValueError(f"String array values must be quoted or reference string variables")
                else:
                    # Handle numeric value
                    value = evaluate_math_expression(value_expr, variables)
                    if not isinstance(value, (int, float)):
                        raise ValueError(f"Numeric array values must be numbers")
                
                # Assign value
                array[int(index)] = value
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Assigned {array_name}[{index}] = {value}", DEBUG_VERBOSE)
                return True
                
            except Exception as e:
                raise ValueError(f"Error in array assignment: {str(e)}")
        return False

    def process_sprite_definition(line):
        """Process sprite definition command."""
        match = SPRITE_DEF_PATTERN.match(line)
        if match:
            name = match.group(1)
            # Parse width and height using our new parameter handling
            width = parse_value(match.group(2), 'define_sprite', 1)  # width is position 1
            height = parse_value(match.group(3), 'define_sprite', 2)  # height is position 2
            
            debug_print(f"Starting sprite definition: {name} ({width}x{height})", DEBUG_VERBOSE)
            sprite_context.in_sprite_definition = True
            sprite_context.current_sprite = name
            sprite_context.sprite_commands = []
            
            # Create and send command
            cmd = f"define_sprite({name}, {width}, {height})"
            debug_print(f"DEBUG: Sending sprite creation command: {cmd}")
            execute_command(cmd)
            debug_print(f"DEBUG: Sprite creation command sent")
            return True
        return False

    def process_sprite_command(line):
        """Convert normal drawing commands to sprite drawing commands."""
        command_match = COMMAND_PATTERN.match(line)
        if command_match:
            cmd_name = command_match.group(1)
            valid_commands = ['plot', 'draw_line', 'draw_rectangle', 'draw_circle', 'draw_polygon', 'draw_text', 'draw_ellipse']
            if cmd_name not in valid_commands:
                debug_print(f"Warning: '{cmd_name}' is not a valid drawing command for sprite definition", DEBUG_CONCISE)
                return
            try:
                args = validate_command_params(cmd_name, command_match.group(2))
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Sprite command: {cmd_name}", DEBUG_VERBOSE)
                    debug_print(f"Parameters: {args}", DEBUG_VERBOSE)

                parsed_args = [
                    parse_value(arg, cmd_name, position) 
                    for position, arg in enumerate(args)
                ]
                
                # Exclude burnout for draw_ellipse in sprites
                if cmd_name == 'draw_ellipse' and len(parsed_args) > 8:
                    parsed_args = parsed_args[:8]  # Keep only x_center to rotation
                
                sprite_cmd = f"sprite_draw({sprite_context.current_sprite}, {cmd_name}, {', '.join(parsed_args)})"
                execute_command(sprite_cmd)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Sprite draw command: {sprite_cmd}", DEBUG_VERBOSE)
            except (ValueError, KeyError) as e:
                debug_print(f"Error processing sprite command '{cmd_name}': {str(e)}", DEBUG_SUMMARY)
                raise
            
    def process_sprite_operation(line):
        """Handle show_sprite, hide_sprite, move_sprite, and dispose_sprite operations."""
        match = SPRITE_OP_PATTERN.match(line)
        if match:
            op = match.group(1)
            name = match.group(2)
            
            if op == 'hide' or op == 'dispose':
                # Check if there's an instance_id parameter
                instance_id = None
                if match.group(3):
                    instance_id = parse_value(match.group(3), f'{op}_sprite', 1)  # instance_id is position 1
                    
                # Create command with or without instance_id
                if instance_id is not None:
                    cmd = f"{op}_sprite({name}, {instance_id})"
                else:
                    cmd = f"{op}_sprite({name})"
            else:
                # show or move with required x,y parameters
                x = parse_value(match.group(3), f'{op}_sprite', 1)  # x is position 1
                y = parse_value(match.group(4), f'{op}_sprite', 2)  # y is position 2
                
                # Check if there's an instance_id parameter
                instance_id = None
                if match.group(5):
                    instance_id = parse_value(match.group(5), f'{op}_sprite', 3)  # instance_id is position 3
                    
                # Create command with or without instance_id
                if instance_id is not None:
                    cmd = f"{op}_sprite({name}, {x}, {y}, {instance_id})"
                else:
                    cmd = f"{op}_sprite({name}, {x}, {y})"
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Sprite operation: {cmd}", DEBUG_VERBOSE)
            store_frame_command(cmd)
            return True
        return False
    
    def handle_print_statement(line, variables):
        """Process print statement with f-string and expression support."""
        content = line[6:-1].strip()  # Remove 'print(' and ')'
        
        if content.startswith('f"') or content.startswith("f'"):
            content = content[2:-1]  # Remove f" or f'
            start = 0
            result = []
            
            while True:
                # Find next expression in curly braces
                start_brace = content.find('{', start)
                if start_brace == -1:
                    result.append(content[start:])
                    break
                    
                # Add text before expression
                result.append(content[start:start_brace])
                
                # Find closing brace
                end_brace = content.find('}', start_brace)
                if end_brace == -1:
                    result.append(content[start_brace:])
                    break
                
                # Extract expression
                expr = content[start_brace+1:end_brace].strip()
                
                try:
                    # Handle array access expressions first
                    if '[' in expr and ']' in expr:
                        value = evaluate_math_expression(expr, variables)
                        result.append(str(value))
                    # Handle math expressions
                    elif any(op in expr for op in '+-*/()'):
                        value = evaluate_math_expression(expr, variables)
                        result.append(str(value))
                    # Handle simple variable reference
                    elif expr.startswith('v_'):
                        if expr not in variables:
                            result.append(f"{{{expr}}}")
                        else:
                            result.append(str(variables[expr]))
                    else:
                        result.append(str(expr))
                        
                except Exception as e:
                    debug_print(f"Error evaluating expression in print: {str(e)}", DEBUG_VERBOSE)
                    result.append(f"{{{expr}}}")
                
                start = end_brace + 1
            
            print(''.join(result))
        else:
            # Handle non-f-string print
            print(content.strip('"\''))

    # Generator-based line processing logic
    def process_lines(line_generator):
        nonlocal normal_exit  # Track script exit status
        global current_command, _metrics
        for line_number, line in enumerate(line_generator, 1):
            # Increment line counter
            
            _metrics['script_lines_processed'] += 1
            current_command = line

            #print("Looping...")
            if check_spacebar():
                print("Spacebar pressed, skipping to next script...")
                force_timer_expired()
                normal_exit = False
                break       
            if is_time_expired():
                debug_print("Script duration expired", DEBUG_CONCISE)
                normal_exit = False
                break            
            debug_print(f"\n--------------------------------------", DEBUG_VERBOSE)
            debug_print(f"Processing line {line_number}: {line}", DEBUG_VERBOSE)

            if not line:
                debug_print("  Skipping empty line or comment", DEBUG_VERBOSE)
                continue

            # Array creation handling
            if process_array_creation(line):
                continue
                
            # Array assignment handling
            if process_array_assignment(line):
                continue

            # Handle sprite definition start
            if process_sprite_definition(line):
                continue

            # Handle sprite definition end
            if line == "endsprite" or line == "endsprite()":
                debug_print(f"Ending sprite definition: {sprite_context.current_sprite}", DEBUG_VERBOSE)
                sprite_context.in_sprite_definition = False
                sprite_context.current_sprite = None
                continue

            # Handle sprite operations (show/hide/move) - MOVED UP
            if process_sprite_operation(line):
                continue

            # Handle commands inside sprite definition
            # Only process as sprite commands if we're inside a sprite definition
            if sprite_context.in_sprite_definition:
                process_sprite_command(line)
                continue

            # Variable assignment logic
            if line.startswith('v_'):
                parts = line.split('=')
                var_name = parts[0].strip()
                expr = parts[1].strip()
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"  Processing expression: {expr}", DEBUG_VERBOSE)
                
                try:
                    if expr.startswith('"') and expr.endswith('"'):
                        var_value = expr[1:-1]  # Remove quotes
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"  String value detected: {var_value}", DEBUG_VERBOSE)
                    elif expr.lower() == 'true':
                        var_value = True
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"  Boolean value detected: {var_value}", DEBUG_VERBOSE)
                    elif expr.lower() == 'false':
                        var_value = False
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"  Boolean value detected: {var_value}", DEBUG_VERBOSE)
                    elif '&' in expr:
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"  Concatenation expression detected: {expr}", DEBUG_VERBOSE)
                        var_value = evaluate_math_expression(expr, variables)
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"  Concatenation result: {var_value}", DEBUG_VERBOSE)
                    else:
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"  Evaluating numeric expression: {expr}", DEBUG_VERBOSE)
                        var_value = safe_eval(expr, variables)
                        
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"  Evaluation result: {var_value}", DEBUG_VERBOSE)
                    variables[var_name] = var_value
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"  Variable assignment: {var_name} = {var_value}", DEBUG_VERBOSE)
                    
                    # Add cache invalidation for the variable lookup cache
                    keys_to_remove = []
                    for key in list(_VAR_FORMAT_CACHE.keys()):
                        if key[0] == var_name:
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        _VAR_FORMAT_CACHE.pop(key)
                        
                except ValueError as e:
                    if DEBUG_LEVEL >= DEBUG_SUMMARY:
                        debug_print(f"  Error in variable assignment: {str(e)}", DEBUG_SUMMARY)
                    raise
                except Exception as e:
                    if DEBUG_LEVEL >= DEBUG_SUMMARY:
                        debug_print(f"  Error: Unexpected error in variable assignment: {str(e)}", DEBUG_SUMMARY)
                    raise ValueError(f"Error processing variable assignment: {str(e)}")
                
            # Procedure definition
            elif PROCEDURE_DEF_PATTERN.match(line):
                proc_name = PROCEDURE_DEF_PATTERN.match(line).group(1)
                proc_commands = []

                for proc_line in line_generator:
                    if proc_line.strip() == '}':
                        break
                    proc_commands.append(proc_line.strip())

                procedures[proc_name] = proc_commands
                debug_print(f"Procedure defined: {proc_name}", DEBUG_SUMMARY)

            # Procedure call
            elif PROCEDURE_CALL_PATTERN.match(line):
                proc_name = PROCEDURE_CALL_PATTERN.match(line).group(1)
                if proc_name in procedures:
                    debug_print(f"Calling procedure: {proc_name}", DEBUG_SUMMARY)
                    process_lines(iter(procedures[proc_name]))
                else:
                    debug_print(f"Error: Procedure {proc_name} not defined", DEBUG_SUMMARY)

            # Frame buffer commands
            elif line.startswith('begin_frame'):
                # Handle different forms of begin_frame command
                if line == 'begin_frame' or line == 'begin_frame()':
                    execute_command('begin_frame(false)')  # Default to non-preserve mode
                    debug_print("Beginning frame buffer mode (standard)", DEBUG_SUMMARY)
                else:
                    # Parse parameter if provided
                    match = FRAME_PARAM_PATTERN.match(line)
                    if match:
                        preserve = match.group(1).strip()
                        # Convert string true/false to lowercase boolean
                        if preserve.lower() == 'true':
                            execute_command('begin_frame(true)')
                            debug_print("Beginning frame buffer mode (preserve)", DEBUG_SUMMARY)
                        else:
                            execute_command('begin_frame(false)')
                            debug_print("Beginning frame buffer mode (standard)", DEBUG_SUMMARY)

            elif line == 'end_frame' or line == 'end_frame()':
                execute_command('end_frame')
                debug_print("Ending frame buffer mode", DEBUG_SUMMARY)

            # For loop logic
            elif FOR_LOOP_PATTERN.match(line):
                match = FOR_LOOP_PATTERN.match(line)
                loop_var = match.group(1)
                
                start = evaluate_math_expression(match.group(2).strip(), variables)
                end = evaluate_math_expression(match.group(3).strip(), variables)
                step = evaluate_math_expression(match.group(4).strip(), variables)
                
                loop_block = []
                for loop_line in line_generator:
                    if loop_line.strip() == f'endfor {loop_var}':
                        break
                    loop_block.append(loop_line.strip())
                
                epsilon = 1e-10 if isinstance(step, float) else 0
                current_value = start
                iteration_count = 0
                while ((step > 0 and current_value <= end + epsilon) or 
                       (step < 0 and current_value >= end - epsilon)):
                    if is_time_expired():
                        print(f"Line {line_number}: Breaking for loop due to timer expiration")
                        break
                    variables[loop_var] = current_value
                    process_lines(iter(loop_block))
                    current_value += step
                    iteration_count += 1
                    if iteration_count > 1000000:
                        print(f"Line {line_number}: WARNING: Loop iteration count exceeded 1,000,000. Breaking loop.")
                        break

            # while looping
            elif WHILE_LOOP_PATTERN.match(line):
                condition = WHILE_LOOP_PATTERN.match(line).group(1)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Processing while loop with condition: {condition}", DEBUG_VERBOSE)
                
                # Collect while loop block
                loop_block = []
                nesting_level = 1  # Track nesting level for nested loops
                
                for loop_line in line_generator:
                    loop_line = loop_line.strip()
                    
                    # Track nested while loops
                    if WHILE_LOOP_PATTERN.match(loop_line):
                        nesting_level += 1
                        
                    if loop_line == 'endwhile':
                        nesting_level -= 1
                        if nesting_level == 0:
                            break
                            
                    if nesting_level > 0:  # Only collect if we're still in our loop
                        loop_block.append(loop_line)
                
                # Execute loop
                while evaluate_condition(condition, variables):
                    if is_time_expired():
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print("Breaking while loop due to timer expiration", DEBUG_VERBOSE)
                        break
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Executing while loop body: {condition}", DEBUG_VERBOSE)
                    process_lines(iter(loop_block))

            elif IF_PATTERN.match(line):
                condition = IF_PATTERN.match(line).group(1)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Processing if condition: {condition}", DEBUG_VERBOSE)
                
                condition_blocks = []
                current_block = {'condition': condition, 'commands': []}
                else_block = None
                nesting_level = 1
                
                try:
                    initial_condition = evaluate_condition(condition, variables)
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Initial condition result: {initial_condition}", DEBUG_VERBOSE)
                    
                    for current_line in line_generator:
                        current_line = current_line.strip()
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"Parsing line: {current_line}, nesting_level: {nesting_level}", DEBUG_VERBOSE)
                        if IF_PATTERN.match(current_line):
                            nesting_level += 1
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Nested if found, level: {nesting_level}", DEBUG_VERBOSE)
                        if current_line == 'endif':
                            nesting_level -= 1
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Found endif, new level: {nesting_level}", DEBUG_VERBOSE)
                            if nesting_level == 0:
                                condition_blocks.append(current_block)
                                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                    debug_print(f"condition_blocks: {condition_blocks}", DEBUG_VERBOSE)
                                if else_block is not None:
                                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                        debug_print(f"else_block before break: {else_block}", DEBUG_VERBOSE)
                                break
                        elif nesting_level == 1:
                            if current_line.startswith('elseif ') and current_line.endswith(' then'):
                                condition_blocks.append(current_block)
                                new_condition = current_line[7:-5].strip()
                                current_block = {'condition': new_condition, 'commands': []}
                            elif current_line == 'else':
                                condition_blocks.append(current_block)
                                else_block = []
                                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                    debug_print(f"Starting else_block: {else_block}", DEBUG_VERBOSE)
                                continue
                        if else_block is not None:
                            else_block.append(current_line)
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Appended to else_block: {else_block}", DEBUG_VERBOSE)
                        else:
                            current_block['commands'].append(current_line)
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Appended to current_block: {current_block['commands']}", DEBUG_VERBOSE)
                    
                    executed = False
                    for block in condition_blocks:
                        if evaluate_condition(block['condition'], variables):
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Executing condition block: {block['condition']}", DEBUG_VERBOSE)
                            process_lines(iter(block['commands']))
                            executed = True
                            break
                    
                    if not executed and else_block is not None:
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print("Executing else block", DEBUG_VERBOSE)
                            debug_print(f"Final else_block contents: {else_block}", DEBUG_VERBOSE)
                        process_lines(iter(else_block))  # Process as a single block
                except Exception as e:
                    raise ValueError(f"Error processing if/elseif condition: {str(e)}\nCommand: {current_command}")



            elif line.lower().startswith('print('):
                handle_print_statement(line, variables)
                continue  # Skip the rest of the loop for print statements

            # Command parsing
            else:
                if line == 'clear' or line == 'clear()':
                    if DEBUG_LEVEL >= DEBUG_SUMMARY:
                        debug_print(f"Found clear command: {line}", DEBUG_SUMMARY)
                    execute_command('clear')
                elif line == 'sync_queue' or line == 'sync_queue()':
                    if DEBUG_LEVEL >= DEBUG_SUMMARY:
                        debug_print(f"Found sync command: {line}", DEBUG_SUMMARY)
                    execute_command('sync_queue')  # Queue the command
                    queue.wait_until_empty()       # Wait for queue to empty
                    queue.last_command_time = time.time() * 1000  # Reset timing after sync
                # Add throttle command handling here
                elif command_match := re.match(r'throttle\((.*)\)', line):
                    try:
                        args = validate_command_params('throttle', command_match.group(1))
                        debug_print(f"Throttle command with args: {args}", DEBUG_VERBOSE)
                        
                        # Parse factor with position information
                        factor = parse_value(args[0], 'throttle', 0)
                        
                        # Update throttle factor in queue
                        queue.set_throttle(float(factor))
                        debug_print(f"Set throttle factor to: {factor}", DEBUG_SUMMARY)
                        
                    except (ValueError, KeyError) as e:
                        debug_print(f"Error processing throttle command: {str(e)}", DEBUG_SUMMARY)
                        raise
                else:   
                    command_match = COMMAND_PATTERN.match(line)
                    if command_match:
                        command_name = command_match.group(1)
                        try:
                            args = validate_command_params(command_name, command_match.group(2))
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Command: {command_name}", DEBUG_VERBOSE)
                                debug_print(f"Parameters: {args}", DEBUG_VERBOSE)
                            
                            parsed_args = [
                                parse_value(arg, command_name, position) 
                                for position, arg in enumerate(args)
                            ]
                            
                            # Filter out empty strings from optional parameters
                            command_args = [arg for arg in parsed_args if arg != '']
                            command = f"{command_name}({', '.join(command_args)})"
                            
                            if DEBUG_LEVEL >= DEBUG_SUMMARY:
                                debug_print(f"Command to execute: {command}", DEBUG_SUMMARY)
                            store_frame_command(command)  # Changed from execute_command for frame consistency
                        except (ValueError, KeyError) as e:
                            debug_print(f"Error processing command '{command_name}': {str(e)}", DEBUG_SUMMARY)
                            raise
                        finally:
                            debug_print(f"Command processing completed: {command_name}", DEBUG_VERBOSE)

                    
    # Call the generator for file reading
    try:
        processed_lines = preprocess_lines(filename)
        process_lines(iter(processed_lines))
        if normal_exit:
            print("Script completed normally - sync queue run")
            debug_print("Script completed normally, adding sync_queue", DEBUG_SUMMARY)
            execute_command('sync_queue')
            queue.wait_until_empty()       # Wait for queue to empty
            queue.last_command_time = time.time() * 1000  # Reset timing after sync
    finally:
        debug_print("\n1. Starting cleanup sequence...", DEBUG_CONCISE)
        
        # Get initial queue size
        initial_queue_size = queue_instance.command_queue.qsize()
        debug_print(f"   Initial queue size: {initial_queue_size}", DEBUG_SUMMARY)
        
        # Drain the queue
        debug_print("3. Draining command queue...", DEBUG_CONCISE)
        drained_commands = 0
        target_drain = initial_queue_size  # We want to drain this many commands
        
        while drained_commands < target_drain:
            try:
                queue_instance.command_queue.get_nowait()
                drained_commands += 1
                
                # Progress update every 500 commands
                if drained_commands % 500 == 0:
                    remaining = queue_instance.command_queue.qsize()
                    debug_print(f"   Progress: {drained_commands} drained, {remaining} remaining", DEBUG_SUMMARY)
                    
            except Empty:
                # If queue reports empty but we haven't hit our target
                current_size = queue_instance.command_queue.qsize()
                if current_size > 0:
                    debug_print(f"   Queue reported empty but still has {current_size} items, retrying...", DEBUG_SUMMARY)
                    time.sleep(0.1)  # Brief pause before retry
                    continue
                else:
                    break

        debug_print(f"   Final drain count: {drained_commands} of {initial_queue_size} commands", DEBUG_SUMMARY)
        time.sleep(.5)  # Brief pause after draining        
        # Do cleanup
        debug_print("4. Executing cleanup commands...", DEBUG_CONCISE)
        execute_command('end_frame')
        execute_command('clear')
        execute_command('dispose_all_sprites()')
        execute_command('sync_queue')   

        # Wait for cleanup
        debug_print("5. Waiting for cleanup completion...", DEBUG_CONCISE)
        queue_instance.wait_for_completion(cooldown=0.5)
        
        debug_print("Cleanup sequence completed", DEBUG_CONCISE)
        gc.collect()
        
    debug_print("Script processing completed", DEBUG_CONCISE)

    report_metrics()
    
def signal_handler(signum, frame):
    """Handle interrupt signal with graceful display cleanup"""
    print("\nInitiating graceful shutdown sequence...")
    # Report metrics with "interrupted" reason
    report_metrics("interrupted")

    # Check if in headless mode
    if is_headless():
        print("\nHeadless mode shutdown initiated...")
        # Simplified, non-interactive cleanup
        report_metrics("interrupted")
        if queue_instance:
            queue_instance.put_command('clear', force_instant=True)
            queue_instance.stop_consumer()
        sys.exit(0)
    else:
        # Your existing interactive cleanup code
        print("\nInitiating graceful shutdown sequence...")
        # Rest of your existing function...

    try:
        if queue_instance:
            print("1. Draining existing command queue...")
            drained_commands = 0
            #while not queue_instance.command_queue.empty():
            #    try:
            #        queue_instance.command_queue.get_nowait()
            #        drained_commands += 1
            #    except Empty:
            #        break
            print(f"   Drained {drained_commands} commands from queue")

            print("2. Sending cleanup commands...")
            print("   - Clearing display")
            queue_instance.put_command('clear', force_instant=True)
            
            print("3. Waiting 2 seconds for cleanup commands to complete...")
            #queue_instance.wait_until_empty()
            time.sleep(.4)
            print("   Less than 2 more seconds...")
            time.sleep(.4)
            print("   Less than 1 more seconds...")
            time.sleep(.4)

            print("   Cleanup commands completed")
            
            print("4. Initiating consumer shutdown...")
            queue_instance.stop_consumer()  # This sends __SHUTDOWN__ command
            print("   Consumer shutdown signal sent")
            
        if queue_monitor:
            print("5. Stopping queue monitor...")
            queue_monitor.stop()
            print("   Queue monitor stopped")
            
    except Exception as e:
        print(f"ERROR during shutdown sequence: {str(e)}")
    finally:
        print("Shutdown sequence complete.")
        sys.exit(0)

# Main Execution
if __name__ == '__main__':
    queue_instance = None
    queue_monitor = None
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Parse arguments
        args = parse_args()
        
        if args.debug_level is not None:
            set_debug_level(args.debug_level)
            
        # Initialize script manager
        script_manager = ScriptManager(args.script_path)

        # Initialize queue and start consumer
        queue_instance = QueueManager.get_instance()
        queue_instance.start_consumer()

        # Start queue monitor if requested
        if args.queue_monitor:
            from shared.queue_monitor import QueueMonitor
            queue_monitor = QueueMonitor(queue_instance)
            queue_monitor.start()

        # Clear display initially
        queue_instance.put_command('clear')
        queue_instance.put_command('sync_queue')        
        
        # Main execution loop
        while True:
            scripts = script_manager.get_script_queue()
            
            # Single script mode
            if script_manager.is_single_script():
                initialize_timer(args.duration)
                start_time = time.time()
                process_script(scripts[0], execute_command)
                # Wait for queue to empty and cooldown
                queue_instance.wait_for_completion()
                end_time = time.time()
                print(f"\nComplete execution time: {end_time - start_time:.3f} seconds")
                break
                
            # Multiple script mode  
            try:
                from pixil_utils.terminal_handler import initialize_terminal, start_terminal, stop_terminal
                initialize_terminal()
                start_terminal()
                while scripts:
                    current_script = scripts.pop()
                    print(f"Current script: {current_script}...")
                    initialize_timer(args.duration)
                    process_script(current_script, execute_command)
                    queue_instance.wait_for_completion()
                    clear_timer()
            finally:
                stop_terminal()
                
            # Exit if not wildcard, otherwise continue with reshuffled scripts
            if not script_manager.is_wildcard:
                break
                
    except KeyboardInterrupt:
        print("\nForce stopping...")
        if queue_monitor:
            queue_monitor.stop()
        if queue_instance:
            queue_instance.cleanup()
        print("Stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        try:
            if queue_monitor:
                queue_monitor.stop()
            if queue_instance:
                queue_instance.cleanup()
            stop_terminal()
        except:
            sys.exit(1)
