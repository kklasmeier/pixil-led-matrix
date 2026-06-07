import re
import sys
import gc
import signal  # At top with other imports
import time
import datetime
from queue import Empty
from shared import QueueManager
from shared.mplot_protocol import pack_mplot, encode_buffer
from pathlib import Path
from database import PixilMetricsDB
from rgb_matrix_lib import execute_command
from typing import Union, Dict, Optional, List
from pixil_utils.variable_registry import VariableRegistry
from pixil_utils.debug import (DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE, DEBUG_LEVEL, set_debug_level, debug_print, current_command)
from pixil_utils.math_functions import (MATH_FUNCTIONS, random_float, has_math_expression, evaluate_math_expression, evaluate_condition, report_jit_stats, reset_jit_stats, report_condition_template_stats, reset_condition_template_stats, set_script_start_time)
from pixil_utils.file_manager import PixilFileManager
from pixil_utils.parameter_types import (
    PARAMETER_TYPES,
    validate_command_params,
    expand_legacy_shape_params,
)
from pixil_utils.expression_parser import format_parameter
from pixil_utils import (ScriptManager, parse_args,
                        # Timer management
                        announce_script_start, is_time_expired, clear_timer, force_timer_expired,
                        # Debug management 
                        set_debug_level,
                        # Terminal handling
                        initialize_terminal, start_terminal,
                        stop_terminal)
from pixil_utils.shutdown import (
    PixilShutdownRequested,
    request_shutdown,
    shutdown_requested,
    exit_pixil,
)
from pixil_utils.array_manager import PixilArray
from pixil_utils.test_hooks import (
    is_test_mode,
    reset_metrics,
    set_script_name,
    record_command_dispatched,
    set_buffer_hash,
    get_metrics,
    print_summary,
    note_fail_in_line,
)
from collections import OrderedDict  # Make sure this is imported
from pixil_utils.optimization_flags import (
    ENABLE_ULTRA_FAST_PATH, ENABLE_FAST_PATH, ENABLE_PARSE_VALUE_CACHE,
    ENABLE_PHASE1_FAST_PATH, show_status, set_profile)
# Import pre-compiled regex patterns
from pixil_utils.regex_patterns import (
    # Fast Path patterns
    FAST_SIMPLE_ARRAY_PATTERN, FAST_VAR_PLUS_NUM_PATTERN, FAST_VAR_MUL_NUM_PATTERN,
    FAST_VAR_SUB_NUM_PATTERN, FAST_VAR_DIV_NUM_PATTERN, FAST_VAR_MOD_NUM_PATTERN,
    FAST_VAR_ADD_VAR_PATTERN, FAST_VAR_MUL_VAR_PATTERN,
    # Legacy patterns  
    ARRAY_CREATE_PATTERN, ARRAY_ASSIGN_PATTERN, SPRITE_DEF_PATTERN, COMMAND_PATTERN,
    SPRITE_OP_PATTERN, PROCEDURE_DEF_PATTERN, PROCEDURE_CALL_PATTERN, FRAME_PARAM_PATTERN,
    FOR_LOOP_PATTERN, WHILE_LOOP_PATTERN, IF_PATTERN, RANDOM_PATTERN
)

# Multi-plot buffer management (legacy when ENABLE_DRAW_BATCH is off)
mplot_buffer = bytearray()
mplot_count = 0

# Unified frame draw batch (plot + draw_* when ENABLE_DRAW_BATCH)
draw_buffer = bytearray()
draw_count = 0
sprite_buffer = bytearray()
sprite_count = 0


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
    terminal_handler.consume_skip_request = lambda: False

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

current_command = None

#Variable cache
_VAR_FORMAT_CACHE = OrderedDict()
_VAR_CACHE_SIZE = 1024
_VAR_CACHE_HITS = 0
_VAR_CACHE_MISSES = 0
_FAST_PATH_HITS = 0
_FAST_PATH_TOTAL = 0
_PARSE_VALUE_ATTEMPTS = 0
_ULTRA_FAST_HITS = 0
_ULTRA_FAST_TOTAL = 0
_FAST_PATH_PARSE_HITS = 0
_FAST_PATH_PARSE_TOTAL = 0
_PARSE_VALUE_TOTAL_TIME = 0.0  # Total time spent in parse_value() in seconds

set_debug_level(DEBUG_OFF)  # Default debug level

# Initialize file manager
file_manager = PixilFileManager()

def reset_fast_path_stats():
    """Reset fast path statistics for new script."""
    global _FAST_PATH_HITS, _FAST_PATH_TOTAL
    _FAST_PATH_HITS = 0
    _FAST_PATH_TOTAL = 0

def initialize_metrics():
    """Reset metrics at start of script."""
    global _metrics, mplot_buffer, mplot_count, draw_buffer, draw_count, sprite_buffer, sprite_count
    _metrics['commands_processed'] = 0
    _metrics['script_lines_processed'] = 0
    _metrics['start_time'] = time.time()
    _metrics['active_time'] = 0
    _metrics['pause_start'] = None
    _metrics['total_pause_time'] = 0
    
    # Set start time for get_system("runtime")
    set_script_start_time(_metrics['start_time'])

    # Reset plot/draw batch buffers
    mplot_buffer.clear()
    mplot_count = 0
    draw_buffer.clear()
    draw_count = 0
    sprite_buffer.clear()
    sprite_count = 0

def report_parse_value_stats():
    """Report detailed parse value optimization statistics."""
    global _PARSE_VALUE_ATTEMPTS, _VAR_CACHE_HITS, _VAR_CACHE_MISSES
    global _FAST_PATH_HITS, _FAST_PATH_TOTAL
    global _ULTRA_FAST_HITS, _ULTRA_FAST_TOTAL, _FAST_PATH_PARSE_HITS, _FAST_PATH_PARSE_TOTAL
    global _PARSE_VALUE_TOTAL_TIME 

    print("Parse Value Optimization Statistics:")
    
    if _PARSE_VALUE_ATTEMPTS > 0:
        print(f"  Total parameter parsing attempts: {_PARSE_VALUE_ATTEMPTS:,}")
        print(f"  Total time in parse_value: {_PARSE_VALUE_TOTAL_TIME:.6f} seconds")  # Add this line
        avg_time_per_call = _PARSE_VALUE_TOTAL_TIME / _PARSE_VALUE_ATTEMPTS
        print(f"  Average time per parse_value call: {avg_time_per_call:.6f} seconds")  # Add this line
        print()

        # Ultra Fast Path stats (Optimization 1)
        if _ULTRA_FAST_TOTAL > 0:
            ultra_fast_rate = (_ULTRA_FAST_HITS / _ULTRA_FAST_TOTAL) * 100
            ultra_fast_savings = (_ULTRA_FAST_HITS * 15) / 1000000  # 15 microseconds per hit
            print(f"  Ultra Fast Path (PV-UF%):")
            print(f"    Attempts: {_ULTRA_FAST_TOTAL:,}")
            print(f"    Hits: {_ULTRA_FAST_HITS:,} ({ultra_fast_rate:.1f}%)")
            print(f"    Time saved: {ultra_fast_savings:.3f} seconds")
        else:
            print(f"  Ultra Fast Path (PV-UF%): No attempts")
        
        # Fast Path Parse stats (Optimization 2) 
        if _FAST_PATH_PARSE_TOTAL > 0:
            fast_parse_rate = (_FAST_PATH_PARSE_HITS / _FAST_PATH_PARSE_TOTAL) * 100
            fast_parse_savings = (_FAST_PATH_PARSE_HITS * 25) / 1000000  # 25 microseconds per hit
            print(f"  Fast Path Parse (PV-F%):")
            print(f"    Attempts: {_FAST_PATH_PARSE_TOTAL:,}")
            print(f"    Hits: {_FAST_PATH_PARSE_HITS:,} ({fast_parse_rate:.1f}%)")
            print(f"    Time saved: {fast_parse_savings:.3f} seconds")
        else:
            print(f"  Fast Path Parse (PV-F%): No attempts")
        
        # Phase 1 Fast Path stats (Optimization 3) - Keep existing
        if _FAST_PATH_TOTAL > 0:
            phase1_rate = (_FAST_PATH_HITS / _FAST_PATH_TOTAL) * 100
            phase1_savings = (_FAST_PATH_HITS * 30) / 1000000  # 30 microseconds per hit
            print(f"  Phase 1 Fast Path (FP%):")
            print(f"    Attempts: {_FAST_PATH_TOTAL:,}")
            print(f"    Hits: {_FAST_PATH_HITS:,} ({phase1_rate:.1f}%)")
            print(f"    Time saved: {phase1_savings:.3f} seconds")
        else:
            print(f"  Phase 1 Fast Path (FP%): No attempts")
        
        # Variable cache stats (Optimization 4)
        cache_attempts = _VAR_CACHE_HITS + _VAR_CACHE_MISSES
        if cache_attempts > 0:
            cache_rate = (_VAR_CACHE_HITS / cache_attempts) * 100
            cache_savings = (_VAR_CACHE_HITS * 20) / 1000000  # 20 microseconds per hit
            print(f"  Variable Cache (PV-Cache%):")
            print(f"    Attempts: {cache_attempts:,}")
            print(f"    Hits: {_VAR_CACHE_HITS:,} ({cache_rate:.1f}%)")
            print(f"    Time saved: {cache_savings:.3f} seconds")
        else:
            print(f"  Variable Cache (PV-Cache%): No attempts")
        
        print()
        
        # Summary statistics
        total_optimization_hits = _ULTRA_FAST_HITS + _FAST_PATH_PARSE_HITS + _FAST_PATH_HITS + _VAR_CACHE_HITS
        if total_optimization_hits > 0:
            total_rate = (total_optimization_hits / _PARSE_VALUE_ATTEMPTS) * 100
            print(f"  Total Optimized Parameters: {total_optimization_hits:,} of {_PARSE_VALUE_ATTEMPTS:,} ({total_rate:.1f}%)")
            
            # Individual contribution breakdown
            uf_contribution = (_ULTRA_FAST_HITS / total_optimization_hits) * 100 if total_optimization_hits > 0 else 0
            fp_contribution = (_FAST_PATH_PARSE_HITS / total_optimization_hits) * 100 if total_optimization_hits > 0 else 0
            p1_contribution = (_FAST_PATH_HITS / total_optimization_hits) * 100 if total_optimization_hits > 0 else 0
            cache_contribution = (_VAR_CACHE_HITS / total_optimization_hits) * 100 if total_optimization_hits > 0 else 0
            
            print(f"  Optimization Breakdown:")
            print(f"    Ultra Fast: {uf_contribution:.1f}% | Fast Path: {fp_contribution:.1f}% | Phase 1: {p1_contribution:.1f}% | Cache: {cache_contribution:.1f}%")
    else:
        print("  No parameter parsing attempts detected")

def report_detailed_summary():
    """Print a one-line summary with the new detailed format."""
    global _ULTRA_FAST_HITS, _ULTRA_FAST_TOTAL, _FAST_PATH_PARSE_HITS, _FAST_PATH_PARSE_TOTAL
    global _FAST_PATH_HITS, _FAST_PATH_TOTAL, _VAR_CACHE_HITS, _VAR_CACHE_MISSES
    global _PARSE_VALUE_TOTAL_TIME

    # Calculate individual rates
    uf_rate = (_ULTRA_FAST_HITS / _ULTRA_FAST_TOTAL * 100) if _ULTRA_FAST_TOTAL > 0 else 0
    fp_rate = (_FAST_PATH_PARSE_HITS / _FAST_PATH_PARSE_TOTAL * 100) if _FAST_PATH_PARSE_TOTAL > 0 else 0
    p1_rate = (_FAST_PATH_HITS / _FAST_PATH_TOTAL * 100) if _FAST_PATH_TOTAL > 0 else 0
    
    cache_attempts = _VAR_CACHE_HITS + _VAR_CACHE_MISSES
    cache_rate = (_VAR_CACHE_HITS / cache_attempts * 100) if cache_attempts > 0 else 0
    
    print()
    print("=== DETAILED OPTIMIZATION SUMMARY ===")
    print(f"PV-UF%: {uf_rate:.0f}% | PV-F%: {fp_rate:.0f}% | FP%: {p1_rate:.0f}% | PV-Cache%: {cache_rate:.0f}%")
    print(f"Parse Value Total Time: {_PARSE_VALUE_TOTAL_TIME:.6f}s")  # Add this line
    print("=====================================")


def report_metrics(reason="complete", script_name=None, start_time=None):
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
    print("--")
    from pixil_utils.math_functions import report_fast_math_stats, report_expression_cache_stats
    report_fast_math_stats()
    print("--")
    report_expression_cache_stats()
    print("--")
    report_condition_template_stats()    
    print("--")
    report_parse_value_stats()
    report_detailed_summary()
    print("--")
    report_jit_stats()
    print("--------------------------------------------")

    # Save to database if we have script info
    if script_name and start_time:
        try:
            save_performance_metrics(script_name, start_time, reason)
        except Exception as e:
            print(f"Warning: Could not save metrics to database: {e}")
            # Continue without failing - database is optional

# Update the save_performance_metrics function in Pixil.py

def save_performance_metrics(script_name, start_time, reason):
    """Save current performance metrics to database."""
    end_time = datetime.datetime.now()
    
    # Import the cache variables from math_functions
    from pixil_utils.math_functions import (_FAST_MATH_HITS, _FAST_MATH_TOTAL, 
                                        _EXPRESSION_RESULT_CACHE, _CACHE_HITS, _CACHE_MISSES,
                                        _JIT_ATTEMPTS, _JIT_HITS, _JIT_COMPILATION_FAILURES,
                                        _JIT_LINE_CACHE_SKIPS, _FAILED_SCRIPT_LINES, _JIT_CACHE,
                                        _CONDITION_TEMPLATE_HITS, _CONDITION_TEMPLATE_MISSES, _CONDITION_TEMPLATE_TIME_SAVED)
    
    # ADD THIS NEW IMPORT for condition template cache size:
    from pixil_utils.condition_templates import get_condition_template_stats
    
    # Import our detailed parse value stats - ADD NEW IMPORTS
    global _PARSE_VALUE_ATTEMPTS, _VAR_CACHE_HITS, _VAR_CACHE_MISSES
    global _ULTRA_FAST_HITS, _ULTRA_FAST_TOTAL, _FAST_PATH_PARSE_HITS, _FAST_PATH_PARSE_TOTAL
    global _PARSE_VALUE_TOTAL_TIME 

    # Calculate metrics
    total_time = (end_time - start_time).total_seconds()
    active_time = total_time - _metrics.get('total_pause_time', 0)
    if active_time <= 0:
        active_time = 0.001
    
    commands_per_second = _metrics['commands_processed'] / active_time
    lines_per_second = _metrics['script_lines_processed'] / active_time
    
    # Fast path metrics (Phase 1 - this is working well)
    fast_path_hit_rate = (_FAST_PATH_HITS / _FAST_PATH_TOTAL * 100) if _FAST_PATH_TOTAL > 0 else 0
    fast_path_time_saved = (_FAST_PATH_HITS * 30) / 1000000
    
    # Fast math metrics
    fast_math_hit_rate = (_FAST_MATH_HITS / _FAST_MATH_TOTAL * 100) if _FAST_MATH_TOTAL > 0 else 0
    fast_math_time_saved = (_FAST_MATH_HITS * 35) / 1000000
    
    # Cache metrics (expression cache)
    cache_attempts = _CACHE_HITS + _CACHE_MISSES
    cache_hit_rate = (_CACHE_HITS / cache_attempts * 100) if cache_attempts > 0 else 0
    cache_time_saved = (_CACHE_HITS * 30) / 1000000
    cache_size = len(_EXPRESSION_RESULT_CACHE)
    
    # NEW: Detailed parse value metrics
    # Ultra Fast Path metrics
    ultra_fast_hit_rate = (_ULTRA_FAST_HITS / _ULTRA_FAST_TOTAL * 100) if _ULTRA_FAST_TOTAL > 0 else 0
    ultra_fast_time_saved = (_ULTRA_FAST_HITS * 15) / 1000000
    
    # Fast Path Parse metrics  
    fast_path_parse_hit_rate = (_FAST_PATH_PARSE_HITS / _FAST_PATH_PARSE_TOTAL * 100) if _FAST_PATH_PARSE_TOTAL > 0 else 0
    fast_path_parse_time_saved = (_FAST_PATH_PARSE_HITS * 25) / 1000000
    
    # Variable cache metrics
    var_cache_attempts = _VAR_CACHE_HITS + _VAR_CACHE_MISSES
    var_cache_hit_rate = (_VAR_CACHE_HITS / var_cache_attempts * 100) if var_cache_attempts > 0 else 0
    var_cache_time_saved = (_VAR_CACHE_HITS * 20) / 1000000
    
    # Overall parse value optimization rate (keep existing calculation for backward compatibility)
    total_parse_optimized = _FAST_PATH_HITS + _VAR_CACHE_HITS  # Phase1 + Variable cache
    parse_value_hit_rate = (total_parse_optimized / _PARSE_VALUE_ATTEMPTS * 100) if _PARSE_VALUE_ATTEMPTS > 0 else 0
    
    # JIT line caching metrics
    jit_hit_rate = (_JIT_HITS / _JIT_ATTEMPTS * 100) if _JIT_ATTEMPTS > 0 else 0
    jit_cache_stats = _JIT_CACHE.get_stats()
    jit_time_saved = jit_cache_stats.total_time_saved
    
    # JIT line cache efficiency
    total_jit_expressions = _JIT_ATTEMPTS + _JIT_LINE_CACHE_SKIPS
    jit_skip_efficiency = (_JIT_LINE_CACHE_SKIPS / total_jit_expressions * 100) if total_jit_expressions > 0 else 0
    jit_skip_time_saved = (_JIT_LINE_CACHE_SKIPS * 250) / 1000000  # 250 μs per skip
    
    # JIT cache utilization
    jit_cache_utilization = (_JIT_CACHE.cache_size / _JIT_CACHE.max_size * 100) if _JIT_CACHE.max_size > 0 else 0
    
    # FIXED: Get condition template stats including cache size
    ct_stats = get_condition_template_stats()
    
    # Prepare metrics data - ADD NEW FIELDS
    metrics_data = {
        'commands_executed': _metrics['commands_processed'],
        'script_lines_processed': _metrics['script_lines_processed'],
        'total_execution_time': total_time,
        'active_execution_time': active_time,
        'commands_per_second': commands_per_second,
        'lines_per_second': lines_per_second,
        
        # Phase 1 Fast Path (kept - this works well)
        'fast_path_attempts': _FAST_PATH_TOTAL,
        'fast_path_hits': _FAST_PATH_HITS,
        'fast_path_hit_rate': fast_path_hit_rate,
        'fast_path_time_saved': fast_path_time_saved,
        
        # Fast math metrics (kept)
        'fast_math_attempts': _FAST_MATH_TOTAL,
        'fast_math_hits': _FAST_MATH_HITS,
        'fast_math_hit_rate': fast_math_hit_rate,
        'fast_math_time_saved': fast_math_time_saved,
        
        # Expression cache metrics (kept)
        'cache_attempts': cache_attempts,
        'cache_hits': _CACHE_HITS,
        'cache_hit_rate': cache_hit_rate,
        'cache_size': cache_size,
        'cache_time_saved': cache_time_saved,
        
        # Original parse value metrics (kept for backward compatibility)
        'parse_value_attempts': _PARSE_VALUE_ATTEMPTS,
        'parse_value_optimized_total': total_parse_optimized,
        'parse_value_hit_rate': parse_value_hit_rate,
        
        # Variable cache specific metrics (kept)
        'var_cache_attempts': var_cache_attempts,
        'var_cache_hits': _VAR_CACHE_HITS,
        'var_cache_hit_rate': var_cache_hit_rate,
        'var_cache_time_saved': var_cache_time_saved,
        
        # NEW: Detailed optimization metrics
        'ultra_fast_attempts': _ULTRA_FAST_TOTAL,
        'ultra_fast_hits': _ULTRA_FAST_HITS,
        'ultra_fast_hit_rate': ultra_fast_hit_rate,
        'ultra_fast_time_saved': ultra_fast_time_saved,
        
        'fast_path_parse_attempts': _FAST_PATH_PARSE_TOTAL,
        'fast_path_parse_hits': _FAST_PATH_PARSE_HITS,
        'fast_path_parse_hit_rate': fast_path_parse_hit_rate,
        'fast_path_parse_time_saved': fast_path_parse_time_saved,
        
        # JIT line caching metrics (kept)
        'jit_attempts': _JIT_ATTEMPTS,
        'jit_hits': _JIT_HITS,
        'jit_failures': _JIT_COMPILATION_FAILURES,
        'jit_hit_rate': jit_hit_rate,
        'jit_time_saved': jit_time_saved,
        'jit_line_cache_skips': _JIT_LINE_CACHE_SKIPS,
        'failed_lines_cached': len(_FAILED_SCRIPT_LINES),
        'jit_skip_efficiency': jit_skip_efficiency,
        'jit_skip_time_saved': jit_skip_time_saved,
        'jit_cache_size': _JIT_CACHE.cache_size,
        'jit_cache_utilization': jit_cache_utilization,
        'jit_compilation_time': jit_cache_stats.compilation_time,

        # Parse value timing metrics
        'parse_value_total_time': _PARSE_VALUE_TOTAL_TIME,
        'parse_value_avg_time_per_call': (_PARSE_VALUE_TOTAL_TIME / _PARSE_VALUE_ATTEMPTS) if _PARSE_VALUE_ATTEMPTS > 0 else 0.0,

        # FIXED: Condition template metrics with proper cache size
        'condition_template_attempts': _CONDITION_TEMPLATE_HITS + _CONDITION_TEMPLATE_MISSES,
        'condition_template_hits': _CONDITION_TEMPLATE_HITS,
        'condition_template_hit_rate': (_CONDITION_TEMPLATE_HITS / (_CONDITION_TEMPLATE_HITS + _CONDITION_TEMPLATE_MISSES) * 100) if (_CONDITION_TEMPLATE_HITS + _CONDITION_TEMPLATE_MISSES) > 0 else 0.0,
        'condition_template_time_saved': _CONDITION_TEMPLATE_TIME_SAVED,
        'condition_template_cache_size': ct_stats['condition_cache_size'],  # FIXED: Use actual cache size
    }

    # Save to database
    try:
        db = PixilMetricsDB()
        db.save_metrics(script_name, start_time, end_time, metrics_data, reason)
        print(f"✓ Performance metrics saved to database")
    except Exception as e:
        print(f"Database save failed: {e}")
        raise

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
        self.in_sprite_definition: bool = False
        self.current_sprite: Optional[str] = None   # ✅ str or None
        self.sprite_commands: List[str] = []        # ✅ explicit list type

def process_script(filename, execute_func=None):
    """
    UPDATED: Main script processing with VariableRegistry optimization.
    """
    if execute_func is None:
        raise ValueError("execute_func must be provided")
    normal_exit = True

    # Track script execution timing
    global script_start_time, script_name
    global mplot_buffer, mplot_count  # Add this line
    script_start_time = datetime.datetime.now()
    script_name = Path(filename).name

    global current_command
    current_command = None  # Reset at script start

    debug_print(f"Opening script file: {filename}", DEBUG_CONCISE)

    # Initialize metrics
    initialize_metrics()
    reset_fast_path_stats()
    from pixil_utils.math_functions import reset_fast_math_stats, reset_expression_cache_stats
    reset_fast_math_stats()
    reset_expression_cache_stats()
    reset_parse_value_stats()
    reset_jit_stats()
    reset_condition_template_stats()
    from pixil_utils.loop_compiler import reset_loop_compiler_stats
    reset_loop_compiler_stats()
    show_status()
    
    # Get queue instance
    queue = QueueManager.get_instance()
    queue.set_pause_callbacks(on_pause=on_queue_pause, on_resume=on_queue_resume)
    queue.reset_throttle()

    # Initialize script environment
    global variables

    # Preprocess lines to remove comments
    def preprocess_lines(filename):
        with open(filename, 'r') as f:
            return [line.split('#', 1)[0].strip() for line in f if line.split('#', 1)[0].strip()]

    _orig_print = None
    # Load and scan script for variable optimization
    print("Initializing optimized variable system...")
    if is_test_mode():
        reset_metrics(Path(filename).name)
        set_script_name(Path(filename).name)
        import builtins
        _orig_print = builtins.print

        def _test_aware_print(*args, **kwargs):
            note_fail_in_line(" ".join(str(a) for a in args))
            return _orig_print(*args, **kwargs)

        builtins.print = _test_aware_print

    script_lines = preprocess_lines(filename)  # Use existing preprocessing
    variables = VariableRegistry()
    variables.scan_and_register(script_lines)

    procedures = {}
    compiled_procedures = {}
    sprite_context = SpriteContext()  # Add sprite context
    frame_commands = []  # Add frame command buffer
    in_frame_mode = False  # Add frame mode tracking

    # Define helper functions after variables are initialized
    def execute_command(cmd):
        """Queue command with appropriate timing"""
        if DEBUG_LEVEL >= DEBUG_SUMMARY:
            debug_print(f"Queueing command: {cmd}", DEBUG_SUMMARY)
        
        # Commands that should execute instantly (no delay)
        force_instant = any([
            cmd == 'begin_frame',
            cmd == 'end_frame',
            cmd == 'sync_queue',
            cmd == '__test_snapshot__',
            cmd.startswith('define_sprite'),
            cmd.startswith('sprite_draw'),
            cmd == 'endsprite',
            cmd.startswith('set_background'),
            cmd.startswith('hide_background'),
            cmd.startswith('nudge_background'),
            cmd.startswith('set_background_offset'),
            cmd.startswith('draw_batch'),
            cmd.startswith('sprite_batch'),
            cmd.startswith('fps('),
            sprite_context.in_sprite_definition,  # All commands in sprite definition
            in_frame_mode,  # All commands in frame mode
        ])

        if DEBUG_LEVEL >= DEBUG_SUMMARY:
            debug_print(f"Sending to queue: {cmd} (instant: {force_instant})", DEBUG_SUMMARY)
        queue.put_command(cmd, force_instant)

    execute_command('fps(0)')

    def flush_draw_buffer_commands():
        """Emit draw_batch if unified buffer has records."""
        global draw_buffer, draw_count
        from pixil_utils.optimization_flags import ENABLE_DRAW_BATCH
        if not ENABLE_DRAW_BATCH or not draw_buffer:
            return
        from shared.draw_batch_protocol import encode_buffer

        n_records = draw_count
        encoded = encode_buffer(bytes(draw_buffer))
        cmd = f'draw_batch("{encoded}")'
        if in_frame_mode:
            store_frame_command(cmd)
        else:
            execute_command(cmd)
        draw_buffer.clear()
        draw_count = 0
        if DEBUG_LEVEL >= DEBUG_SUMMARY and n_records:
            debug_print(f"Flushing draw_batch ({n_records} ops)", DEBUG_SUMMARY)

    def flush_sprite_buffer_commands():
        """Emit sprite_batch if buffer has records."""
        global sprite_buffer, sprite_count
        from pixil_utils.optimization_flags import ENABLE_SPRITE_BATCH
        if not ENABLE_SPRITE_BATCH or not sprite_buffer:
            return
        from pixil_utils.sprite_batch_dispatch import flush_sprite_buffer

        n_records = sprite_count
        flush_sprite_buffer(sprite_buffer, store_frame_command)
        sprite_count = 0
        if DEBUG_LEVEL >= DEBUG_SUMMARY and n_records:
            debug_print(f"Flushing sprite_batch ({n_records} ops)", DEBUG_SUMMARY)

    def _append_to_draw_batch(cmd_name, parsed_args):
        global draw_buffer, draw_count
        from pixil_utils.draw_batch_dispatch import append_parsed_draw

        append_parsed_draw(draw_buffer, cmd_name, parsed_args)
        draw_count += 1

    def _use_draw_batch_for(cmd_name: str) -> bool:
        from pixil_utils.optimization_flags import ENABLE_DRAW_BATCH
        from pixil_utils.draw_batch_dispatch import DRAW_BATCH_COMMANDS
        if not ENABLE_DRAW_BATCH or cmd_name not in DRAW_BATCH_COMMANDS:
            return False
        # mplot grids often run without begin_frame — still batch until mflush
        if cmd_name == "mplot":
            return True
        return in_frame_mode

    def _append_to_sprite_batch(cmd_name, parsed_args):
        global sprite_buffer, sprite_count
        from pixil_utils.sprite_batch_dispatch import append_parsed_sprite

        append_parsed_sprite(sprite_buffer, cmd_name, parsed_args)
        sprite_count += 1

    def _use_sprite_batch_for(cmd_name: str) -> bool:
        from pixil_utils.optimization_flags import ENABLE_SPRITE_BATCH
        from pixil_utils.sprite_batch_dispatch import SPRITE_BATCH_COMMANDS
        if not ENABLE_SPRITE_BATCH or cmd_name not in SPRITE_BATCH_COMMANDS:
            return False
        return in_frame_mode

    def _queue_sprite_command(cmd_name: str, parsed_args: List) -> None:
        """Route sprite ops to batch (in frame mode) or immediate queue."""
        if _use_sprite_batch_for(cmd_name):
            _append_to_sprite_batch(cmd_name, parsed_args)
            return
        params = [str(a) for a in parsed_args]
        store_frame_command(f"{cmd_name}({', '.join(params)})")

    def flush_frame_commands():
        """Execute frame commands before end_frame.

        draw_batch/sprite_batch are appended at end_frame flush time, after
        commands like draw_text were already queued in frame_commands — run
        batches first so HUD/text drawn on top of the grid.
        """
        draw_batches: list[str] = []
        sprite_batches: list[str] = []
        plot_batches: list[str] = []
        other: list[str] = []
        for cmd in frame_commands:
            if cmd.startswith("draw_batch("):
                draw_batches.append(cmd)
            elif cmd.startswith("sprite_batch("):
                sprite_batches.append(cmd)
            elif cmd.startswith("plot_batch("):
                plot_batches.append(cmd)
            else:
                other.append(cmd)
        for cmd in draw_batches + sprite_batches + plot_batches + other:
            queue.put_command(cmd, force_instant=True)
        frame_commands.clear()

    def start_frame_buffer(preserve: bool = False):
        """Begin matrix frame and batch draw commands until end_frame."""
        nonlocal in_frame_mode
        global mplot_buffer, mplot_count, draw_buffer, draw_count, sprite_buffer, sprite_count
        frame_commands.clear()
        mplot_buffer.clear()
        mplot_count = 0
        draw_buffer.clear()
        draw_count = 0
        sprite_buffer.clear()
        sprite_count = 0
        execute_command(f'begin_frame({str(preserve).lower()})')
        in_frame_mode = True

    def finish_frame_buffer():
        """Flush batched commands then end the matrix frame."""
        nonlocal in_frame_mode
        flush_draw_buffer_commands()
        flush_sprite_buffer_commands()
        in_frame_mode = False
        flush_frame_commands()
        execute_command('end_frame')

    def store_frame_command(cmd):
        """Store command if in frame mode, execute immediately if not"""
        global _metrics
        _metrics['commands_processed'] += 1
        record_command_dispatched()
        
        if in_frame_mode:
            frame_commands.append(cmd)
        else:
            execute_command(cmd)

    def try_ultra_fast_path(value, command_name, param_position):
        """
        Handle the simplest parameter cases with minimal overhead.
        Returns formatted parameter string or None if not handled.
        """
        # REMOVED: Detailed counter tracking for better performance
        
        if not isinstance(value, str):
            return None
            
        value_stripped = value.strip()
        
        # Ultra-Fast Path #1: Direct integers (e.g., "100", "32", "5")
        if value_stripped.isdigit():
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Ultra-fast integer: {value_stripped}", DEBUG_VERBOSE)
            return value_stripped
        
        # Ultra-Fast Path #2: Direct color names (e.g., "red", "blue", "green")
        # Create a set of known color names from your color list
        KNOWN_COLORS = {
            'black', 'white', 'gray', 'light_gray', 'dark_gray', 'silver',
            'red', 'crimson', 'maroon', 'rose', 'pink', 'salmon', 'coral',
            'brown', 'standard_brown', 'dark_brown', 'wood_brown', 'tan',
            'orange', 'gold', 'peach', 'bronze', 'yellow', 'lime', 'green',
            'olive', 'spring_green', 'forest_green', 'mint', 'teal', 'turquoise',
            'cyan', 'sky_blue', 'azure', 'blue', 'navy', 'royal_blue', 'ocean_blue',
            'indigo', 'purple', 'violet', 'magenta', 'lavender'
        }
        
        if value_stripped in KNOWN_COLORS:
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Ultra-fast color: {value_stripped}", DEBUG_VERBOSE)
            return value_stripped

        # Ultra-Fast Path #2b: burnout_mode literals (fade/instant) for plot/mplot
        if value_stripped in ('fade', 'instant'):
            try:
                param_name = PARAMETER_TYPES[command_name][param_position]['name']
            except (KeyError, IndexError):
                param_name = ''
            if param_name == 'burnout_mode':
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Ultra-fast burnout_mode: {value_stripped}", DEBUG_VERBOSE)
                return value_stripped
        
        # Ultra-Fast Path #3: Direct quoted strings (e.g., "Hello", "piboto-regular")
        if ((value_stripped.startswith('"') and value_stripped.endswith('"')) or
            (value_stripped.startswith("'") and value_stripped.endswith("'"))):
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Ultra-fast quoted string: {value_stripped}", DEBUG_VERBOSE)
            return value_stripped
        
        # Not handled by ultra-fast path
        return None

    def try_fast_path(value, command_name, param_position):
        """
        Handle moderately complex parameter cases efficiently.
        Returns formatted parameter string or None if not handled.
        """
        # REMOVED: Detailed counter tracking for better performance
        
        if not isinstance(value, str):
            return None
            
        value_stripped = value.strip()
        
        # Fast Path #1: Simple array access (e.g., "v_array[v_i]", "v_px[v_i]")
        array_match = FAST_SIMPLE_ARRAY_PATTERN.match(value_stripped)
        if array_match:
            array_name, index_var = array_match.groups()
            
            # Minimal validation then let Python handle the rest
            if array_name in variables and index_var in variables:
                try:
                    array = variables[array_name]
                    index = int(variables[index_var])
                    result = array[index]  # Let Python handle bounds checking and array type
                    
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Fast array access: {array_name}[{index_var}] = {array_name}[{index}] = {result}", DEBUG_VERBOSE)
                    return format_parameter(result, command_name, param_position, variables)
                    
                except (KeyError, IndexError, TypeError, ValueError):
                    pass  # Fall back to normal processing
        
        # Fast Path #2: Simple arithmetic (v_variable + number, v_variable * number, etc.)
        # Variable + number pattern
        plus_match = FAST_VAR_PLUS_NUM_PATTERN.match(value_stripped)
        if plus_match:
            var_name, number_str = plus_match.groups()
            if is_valid_numeric_operation(var_name, number_str, variables):
                var_value = variables[var_name]
                
                # Simplified arithmetic - let Python handle int/float automatically
                if '.' in number_str:
                    result = float(var_value) + float(number_str)
                else:
                    result = var_value + int(number_str)
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast add: {var_name} + {number_str} = {result}", DEBUG_VERBOSE)
                return format_parameter(result, command_name, param_position, variables)
        
        # Variable * number pattern 
        sub_match = FAST_VAR_SUB_NUM_PATTERN.match(value_stripped)
        if sub_match:
            var_name, number_str = sub_match.groups()
            if is_valid_numeric_operation(var_name, number_str, variables):
                var_value = variables[var_name]
                
                # Simplified arithmetic - let Python handle int/float automatically
                if '.' in number_str:
                    result = float(var_value) - float(number_str)
                else:
                    result = var_value - int(number_str)
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast sub: {var_name} - {number_str} = {result}", DEBUG_VERBOSE)
                return format_parameter(result, command_name, param_position, variables)
                
        # Variable - number pattern
        sub_match = FAST_VAR_SUB_NUM_PATTERN.match(value_stripped)
        if sub_match:
            var_name, number_str = sub_match.groups()
            if is_valid_numeric_operation(var_name, number_str, variables):
                var_value = variables[var_name]
                
                # Simplified arithmetic - let Python handle int/float automatically
                if '.' in number_str:
                    result = float(var_value) - float(number_str)
                else:
                    result = var_value - int(number_str)
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast sub: {var_name} - {number_str} = {result}", DEBUG_VERBOSE)
                return format_parameter(result, command_name, param_position, variables)

        # Variable / number pattern
        div_match = FAST_VAR_DIV_NUM_PATTERN.match(value_stripped)
        if div_match:
            var_name, number_str = div_match.groups()
            if is_valid_numeric_operation(var_name, number_str, variables) and float(number_str) != 0:
                var_value = variables[var_name]
                
                # Division always results in float to avoid integer division issues
                result = float(var_value) / float(number_str)
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast div: {var_name} / {number_str} = {result}", DEBUG_VERBOSE)
                return format_parameter(result, command_name, param_position, variables)

        # Variable % number pattern
        mod_match = FAST_VAR_MOD_NUM_PATTERN.match(value_stripped)
        if mod_match:
            var_name, number_str = mod_match.groups()
            if is_valid_numeric_operation(var_name, number_str, variables) and float(number_str) != 0:
                var_value = variables[var_name]
                
                # Modulo operation
                if '.' in number_str:
                    result = float(var_value) % float(number_str)
                else:
                    result = var_value % int(number_str)
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast mod: {var_name} % {number_str} = {result}", DEBUG_VERBOSE)
                return format_parameter(result, command_name, param_position, variables)

        # Variable + variable pattern
        var_add_match = FAST_VAR_ADD_VAR_PATTERN.match(value_stripped)
        if var_add_match:
            var1, var2 = var_add_match.groups()
            if (var1 in variables and var2 in variables and
                isinstance(variables[var1], (int, float)) and
                isinstance(variables[var2], (int, float))):
                
                result = variables[var1] + variables[var2]
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast var add: {var1} + {var2} = {result}", DEBUG_VERBOSE)
                return format_parameter(result, command_name, param_position, variables)

        # Variable * variable pattern
        var_mul_match = FAST_VAR_MUL_VAR_PATTERN.match(value_stripped)
        if var_mul_match:
            var1, var2 = var_mul_match.groups()
            if (var1 in variables and var2 in variables and
                isinstance(variables[var1], (int, float)) and
                isinstance(variables[var2], (int, float))):
                
                result = variables[var1] * variables[var2]
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast var mul: {var1} * {var2} = {result}", DEBUG_VERBOSE)
                return format_parameter(result, command_name, param_position, variables)

        # Not handled by fast path
        return None

    def is_valid_numeric_operation(var_name, number_str, variables):
        """Pre-validate that we can do numeric arithmetic without exceptions."""
        if var_name not in variables:
            return False
        
        var_value = variables[var_name]
        if not isinstance(var_value, (int, float)):
            return False
        
        # Quick check if number_str is valid
        try:
            float(number_str)
            return True
        except ValueError:
            return False

    def parse_value(value, command_name, param_position):
        """
        Parse and format a parameter value, handling variables and math expressions.
        Uses configurable optimization flags to control caching behavior.
        """
        # Start timing
        start_time = time.perf_counter()

        global _VAR_FORMAT_CACHE, _VAR_CACHE_HITS, _VAR_CACHE_MISSES, _PARSE_VALUE_ATTEMPTS
        global _ULTRA_FAST_HITS, _ULTRA_FAST_TOTAL, _FAST_PATH_PARSE_HITS, _FAST_PATH_PARSE_TOTAL
        global _PARSE_VALUE_TOTAL_TIME 
        _PARSE_VALUE_ATTEMPTS += 1

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

        # OPTIMIZATION 1: Ultra-fast path (controlled by flag)
        if ENABLE_ULTRA_FAST_PATH:
            _ULTRA_FAST_TOTAL += 1
            ultra_fast_result = try_ultra_fast_path(value, command_name, param_position)
            if ultra_fast_result is not None:
                _ULTRA_FAST_HITS += 1
                return ultra_fast_result

        # OPTIMIZATION 2: Fast path for arrays and arithmetic (controlled by flag)
        if ENABLE_FAST_PATH:
            _FAST_PATH_PARSE_TOTAL += 1
            fast_result = try_fast_path(value, command_name, param_position)
            if fast_result is not None:
                _FAST_PATH_PARSE_HITS += 1
                return fast_result

        # OPTIMIZATION 3: Phase 1 Fast Path for simple variables (controlled by flag)
        if (ENABLE_PHASE1_FAST_PATH and isinstance(value, str) and 
            value.startswith('v_') and len(value) > 2 and
            not any(c in value for c in '+-*/()[]&')):
            
            global _FAST_PATH_HITS, _FAST_PATH_TOTAL
            _FAST_PATH_TOTAL += 1
            
            if value in variables:
                _FAST_PATH_HITS += 1
                var_value = variables[value]
                
                # Special handling for font_name parameter
                if command_name == 'draw_text' and param_position == 3:
                    if isinstance(var_value, str):
                        if var_value.startswith('"') and var_value.endswith('"'):
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Phase1 fast path font (pre-quoted): {value} -> {var_value}", DEBUG_VERBOSE)
                            return var_value
                        else:
                            result = f'"{var_value}"'
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Phase1 fast path font (quoted): {value} -> {var_value} -> {result}", DEBUG_VERBOSE)
                            return result
                
                result = format_parameter(var_value, command_name, param_position, variables)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Phase1 fast path variable lookup: {value} -> {var_value} -> {result}", DEBUG_VERBOSE)
                return result
            else:
                # Variable not found - continue to normal path for error handling
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Phase1: Variable {value} not found, falling back to normal path", DEBUG_VERBOSE)

        # OPTIMIZATION 4: Variable format cache (controlled by flag)
        if (ENABLE_PARSE_VALUE_CACHE and value.startswith('v_') and 
            not has_math_expression(value) and "random" not in value):
            
            cache_key = f"{value}|{command_name}|{param_position}"
            
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
                
                # Special handling for font_name parameter
                if command_name == 'draw_text' and param_position == 3:
                    if isinstance(var_value, str):
                        # If it's already quoted, return as-is
                        if var_value.startswith('"') and var_value.endswith('"'):
                            result = var_value
                        # Otherwise, quote it as a font name
                        else:
                            result = f'"{var_value}"'
                        
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"Variable cache font handling: {value} -> {var_value} -> {result}", DEBUG_VERBOSE)
                    else:
                        # Non-string variable for font name - use normal formatting
                        result = format_parameter(var_value, command_name, param_position, variables)
                else:
                    # Normal parameter formatting
                    result = format_parameter(var_value, command_name, param_position, variables)
                
                # Cache the result with LRU eviction
                if len(_VAR_FORMAT_CACHE) >= _VAR_CACHE_SIZE:
                    # Remove oldest item (first in OrderedDict)
                    _VAR_FORMAT_CACHE.popitem(last=False)
                _VAR_FORMAT_CACHE[cache_key] = result
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Variable cache miss: {value} -> {result}", DEBUG_VERBOSE)
                return result
            else:
                # Variable not found - continue to normal path for error handling
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Cache: Variable {value} not found, falling back to normal path", DEBUG_VERBOSE)

        # NORMAL PATH: Handle remaining cases without optimizations
        
        # Special case for draw_text's font_name (position 3)
        if command_name == 'draw_text' and param_position == 3:
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Normal path font_name handling for: {value}", DEBUG_VERBOSE)
                
            starts_with_v = value.startswith('v_')
            has_math_chars = any(c in value for c in '+-*/()')
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Font analysis: starts_with_v={starts_with_v}, has_math_chars={has_math_chars}", DEBUG_VERBOSE)
                
            # Only treat as expression if it's a variable or has clear math context
            if starts_with_v or (has_math_chars and any(c.isdigit() or c in 'v_' for c in value)):
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Font_name is variable/expression: {value}", DEBUG_VERBOSE)
                return format_parameter(value, command_name, param_position, variables)
            else:
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Font_name is literal, quoting: {value}", DEBUG_VERBOSE)
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
            debug_print(f"Normal path: passing to format_parameter: {val}", DEBUG_VERBOSE)

        end_time = time.perf_counter()
        _PARSE_VALUE_TOTAL_TIME += (end_time - start_time)

        return format_parameter(val, command_name, param_position, variables)

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
        """OPTIMIZED: Process array assignment with VariableRegistry."""
        match = ARRAY_ASSIGN_PATTERN.match(line)
        if match:
            array_name = match.group(1)
            index_expr = match.group(2)
            value_expr = match.group(3).strip()
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Processing array assignment: {array_name}[{index_expr}] = {value_expr}", DEBUG_VERBOSE)
            
            try:
                # OPTIMIZED: Check if array exists using VariableRegistry
                if array_name not in variables:
                    raise ValueError(f"Array '{array_name}' not found")
                array = variables.get(array_name)
                if not isinstance(array, PixilArray):
                    raise ValueError(f"Variable '{array_name}' is not an array")
                
                # OPTIMIZED: Evaluate index using VariableRegistry
                index = evaluate_math_expression(index_expr, variables)
                if not isinstance(index, (int, float)):
                    raise ValueError(f"Array index must be a number, got {type(index)}")
                
                # Handle value based on array type
                if array.get_type() == 'string':
                    # Handle string value
                    if value_expr.startswith('"') and value_expr.endswith('"'):
                        value = value_expr
                    elif value_expr.startswith("'") and value_expr.endswith("'"):
                        value = value_expr
                    elif value_expr.startswith('v_'):
                        # OPTIMIZED: Use VariableRegistry for variable lookup
                        if value_expr not in variables:
                            raise ValueError(f"Variable '{value_expr}' not found")
                        value = variables.get(value_expr)
                        if not isinstance(value, str):
                            raise ValueError(f"Cannot assign non-string value to string array")
                    else:
                        raise ValueError(f"String array values must be quoted or reference string variables")
                else:
                    # OPTIMIZED: Handle numeric value using VariableRegistry
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
        if not match:
            return False   # ✅ Explicit check makes Pylance happy

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

    def process_sprite_command(line):
        """Convert normal drawing commands to sprite drawing commands, and handle sprite_cel()."""
        # Check for sprite_cel command first
        if line.startswith('sprite_cel'):
            cel_match = re.match(r'sprite_cel\((\d+)?\)', line)
            if cel_match:
                cel_index = cel_match.group(1)
                if cel_index is not None:
                    cmd = f"sprite_cel({cel_index})"
                else:
                    cmd = "sprite_cel()"
                debug_print(f"Sprite cel command: {cmd}", DEBUG_VERBOSE)
                execute_command(cmd)
                return
            else:
                debug_print(f"Warning: Invalid sprite_cel syntax: {line}", DEBUG_CONCISE)
                return
        
        command_match = COMMAND_PATTERN.match(line)
        if command_match:
            cmd_name = command_match.group(1)
            valid_commands = ['plot', 'draw_line', 'draw_rectangle', 'draw_circle', 'draw_polygon', 'draw_text', 'draw_ellipse', 'draw_arc']
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
        if not match:
            return False   # ✅ Pylance knows match is safe after this

        op = match.group(1)
        name = match.group(2)

        if op == 'hide' or op == 'dispose':
            # hide_sprite(name, instance_id?)
            # dispose_sprite(name, instance_id?)
            instance_id = None
            group_3 = match.group(3) if match else None
            if group_3:
                instance_id = parse_value(group_3, f'{op}_sprite', 1)

            if instance_id is not None:
                cmd = f"{op}_sprite({name}, {instance_id})"
            else:
                cmd = f"{op}_sprite({name})"
                
        elif op == 'show':
            # show_sprite(name, x, y, instance_id?, z_index?, cel_idx?)
            x_group = match.group(3)
            y_group = match.group(4)

            if x_group is None or y_group is None:
                return False

            x = parse_value(x_group, 'show_sprite', 1)
            y = parse_value(y_group, 'show_sprite', 2)
            
            # Optional parameters
            instance_id = None
            z_index = None
            cel_idx = None
            
            group_5 = match.group(5) if match else None
            if group_5:
                instance_id = parse_value(group_5, 'show_sprite', 3)
                
            group_6 = match.group(6) if match else None
            if group_6:
                z_index = parse_value(group_6, 'show_sprite', 4)
                
            group_7 = match.group(7) if match else None
            if group_7:
                cel_idx = parse_value(group_7, 'show_sprite', 5)
            
            # Build command with available parameters
            params = [name, x, y]
            if instance_id is not None:
                params.append(str(instance_id))
                if z_index is not None:
                    params.append(str(z_index))
                    if cel_idx is not None:
                        params.append(str(cel_idx))
                elif cel_idx is not None:
                    params.append('0')  # default z_index
                    params.append(str(cel_idx))
            elif z_index is not None or cel_idx is not None:
                params.append('0')  # default instance_id
                if z_index is not None:
                    params.append(str(z_index))
                    if cel_idx is not None:
                        params.append(str(cel_idx))
                elif cel_idx is not None:
                    params.append('0')  # default z_index
                    params.append(str(cel_idx))
                    
            cmd = f"show_sprite({', '.join(str(p) for p in params)})"
            
        else:  # op == 'move'
            # move_sprite(name, x, y, instance_id?, cel_idx?)
            x_group = match.group(3)
            y_group = match.group(4)

            if x_group is None or y_group is None:
                return False

            x = parse_value(x_group, 'move_sprite', 1)
            y = parse_value(y_group, 'move_sprite', 2)
            
            # Optional parameters
            instance_id = None
            cel_idx = None
            
            group_5 = match.group(5) if match else None
            if group_5:
                instance_id = parse_value(group_5, 'move_sprite', 3)
                
            group_6 = match.group(6) if match else None
            if group_6:
                cel_idx = parse_value(group_6, 'move_sprite', 4)
            
            # Build command with available parameters
            params = [name, x, y]
            if instance_id is not None:
                params.append(str(instance_id))
                if cel_idx is not None:
                    params.append(str(cel_idx))
            elif cel_idx is not None:
                params.append('0')  # default instance_id
                params.append(str(cel_idx))
                    
            cmd = f"move_sprite({', '.join(str(p) for p in params)})"
        
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Sprite operation: {cmd}", DEBUG_VERBOSE)
        from pixil_utils.parameter_types import split_command_parameters
        inner = line[line.index("(") + 1 : line.rindex(")")]
        raw_args = split_command_parameters(inner)
        parsed_args = [
            parse_value(arg.strip(), f"{op}_sprite", pos)
            for pos, arg in enumerate(raw_args)
        ]
        _queue_sprite_command(f"{op}_sprite", parsed_args)
        return True

    
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

    def _compiled_plot(x, y, color, intensity, burnout=None, burnout_mode=None):
        """Compiled plot(): batch in frame mode; flush immediately otherwise."""
        global mplot_buffer, mplot_count, draw_buffer, draw_count
        if not (0 <= x <= 63 and 0 <= y <= 63):
            return
        from shared.mplot_protocol import normalize_mplot_color
        final_color = normalize_mplot_color(color)
        if _use_draw_batch_for('plot'):
            _append_to_draw_batch('plot', [x, y, final_color, intensity, burnout, burnout_mode])
            return
        parts = [str(x), str(y), str(final_color), str(intensity)]
        if burnout is not None:
            parts.append(str(burnout))
            if burnout_mode is not None:
                parts.append(str(burnout_mode))
        store_frame_command(f"plot({', '.join(parts)})")

    def _compiled_draw_line(x0, y0, x1, y1, color, intensity=100, burnout=None, burnout_mode=None):
        """Compiled draw_line(): batch in frame mode; flush immediately otherwise."""
        from shared.mplot_protocol import normalize_mplot_color
        final_color = normalize_mplot_color(color)
        if _use_draw_batch_for('draw_line'):
            _append_to_draw_batch('draw_line', [x0, y0, x1, y1, final_color, intensity, burnout, burnout_mode])
            return
        parts = [str(x0), str(y0), str(x1), str(y1), str(final_color), str(intensity)]
        if burnout is not None:
            parts.append(str(burnout))
            if burnout_mode is not None:
                parts.append(str(burnout_mode))
        store_frame_command(f"draw_line({', '.join(parts)})")

    def _compiled_draw_circle(x, y, radius, color, intensity=100, filled=False, burnout=None, burnout_mode=None):
        """Compiled draw_circle(): batch in frame mode; flush immediately otherwise."""
        from shared.mplot_protocol import normalize_mplot_color
        final_color = normalize_mplot_color(color)
        filled_flag = bool(filled)
        if _use_draw_batch_for('draw_circle'):
            _append_to_draw_batch(
                'draw_circle',
                [x, y, radius, final_color, intensity, filled_flag, burnout, burnout_mode],
            )
            return
        parts = [str(x), str(y), str(radius), str(final_color), str(intensity), str(filled_flag).lower()]
        if burnout is not None:
            parts.append(str(burnout))
            if burnout_mode is not None:
                parts.append(str(burnout_mode))
        store_frame_command(f"draw_circle({', '.join(parts)})")

    def _compiled_mplot(x, y, color, intensity, burnout=None, burnout_mode=None):
        global mplot_buffer, mplot_count, draw_buffer, draw_count
        if not (0 <= x <= 63 and 0 <= y <= 63):
            return
        from shared.mplot_protocol import normalize_mplot_color
        final_color = normalize_mplot_color(color)
        if _use_draw_batch_for('mplot'):
            _append_to_draw_batch('mplot', [x, y, final_color, intensity, burnout, burnout_mode])
            return
        record = pack_mplot(x, y, final_color, intensity, burnout, burnout_mode)
        mplot_buffer.extend(record)
        mplot_count += 1

    def _run_compiled_command(cmd_name, arg_exprs):
        global mplot_buffer, mplot_count
        if cmd_name == 'fps':
            from pixil_utils.param_bounds import clamp_fps
            from pixil_utils.test_hooks import effective_fps

            rate = 0.0
            if arg_exprs:
                rate = effective_fps(clamp_fps(parse_value(arg_exprs[0], 'fps', 0)))
            execute_command(f'fps({rate})')
        elif cmd_name == 'begin_frame':
            from pixil_utils.parameter_types import parse_bool_literal

            preserve = False
            if arg_exprs:
                preserve = parse_bool_literal(arg_exprs[0])
            start_frame_buffer(preserve)
        elif cmd_name == 'end_frame':
            finish_frame_buffer()
        elif cmd_name == 'clear':
            execute_command('clear')
        elif cmd_name == 'mflush':
            from pixil_utils.optimization_flags import ENABLE_DRAW_BATCH
            if ENABLE_DRAW_BATCH:
                flush_draw_buffer_commands()
            elif len(mplot_buffer) > 0:
                encoded_data = encode_buffer(mplot_buffer)
                store_frame_command(f'plot_batch("{encoded_data}")')
                mplot_buffer.clear()
                mplot_count = 0
        else:
            arg_str = ','.join(arg_exprs)
            args = validate_command_params(cmd_name, arg_str)
            args = expand_legacy_shape_params(cmd_name, args)
            parsed_args = [
                parse_value(arg, cmd_name, position)
                for position, arg in enumerate(args)
            ]
            if _use_draw_batch_for(cmd_name):
                _append_to_draw_batch(cmd_name, parsed_args)
                return
            if _use_sprite_batch_for(cmd_name):
                _append_to_sprite_batch(cmd_name, parsed_args)
                return
            command_args = []
            for position, arg in enumerate(parsed_args):
                if arg != '':
                    command_args.append(arg)
                else:
                    param_name = PARAMETER_TYPES[cmd_name][position]['name']
                    raise ValueError(
                        f"Command '{cmd_name}': could not resolve "
                        f"parameter '{param_name}' at position {position}"
                    )
            store_frame_command(f"{cmd_name}({', '.join(str(a) for a in command_args)})")

    compiled_ctx_pool = None

    def _get_compiled_ctx():
        nonlocal compiled_ctx_pool
        from pixil_utils.loop_compiler import ReusableLoopContext
        if compiled_ctx_pool is None:
            compiled_ctx_pool = ReusableLoopContext(
                variables,
                _compiled_mplot,
                is_time_expired,
                call_procedure=invoke_procedure,
                run_command=_run_compiled_command,
                plot_fn=_compiled_plot,
                draw_line_fn=_compiled_draw_line,
                draw_circle_fn=_compiled_draw_circle,
            )
        return compiled_ctx_pool.get()

    def invoke_procedure(proc_name):
        from pixil_utils.loop_compiler import run_compiled_block
        from pixil_utils.optimization_flags import ENABLE_COMPILED_PROCEDURES

        if proc_name not in procedures:
            debug_print(f"Error: Procedure {proc_name} not defined", DEBUG_SUMMARY)
            return
        debug_print(f"Calling procedure: {proc_name}", DEBUG_SUMMARY)
        compiled = compiled_procedures.get(proc_name)
        if compiled is not None and ENABLE_COMPILED_PROCEDURES:
            run_compiled_block(compiled, _get_compiled_ctx())
        else:
            from pixil_utils.loop_compiler import LoopBreak
            try:
                process_lines(iter(procedures[proc_name]))
            except LoopBreak:
                pass

    # Generator-based line processing logic
    def process_lines(line_generator):
        nonlocal normal_exit  # Track script exit status
        global current_command, _metrics, _VAR_FORMAT_CACHE
    
        for line_number, line in enumerate(line_generator, 1):
            # Increment line counter
            
            _metrics['script_lines_processed'] += 1
            current_command = line

            from pixil_utils.math_functions import set_current_script_line
            set_current_script_line(current_command)
   
            if shutdown_requested():
                normal_exit = False
                raise PixilShutdownRequested()

            if is_time_expired():
                normal_exit = False
                break
            debug_print(f"\n--------------------------------------", DEBUG_VERBOSE)
            debug_print(f"Processing line {line_number}: {line}", DEBUG_VERBOSE)

            if not line:
                debug_print("  Skipping empty line or comment", DEBUG_VERBOSE)
                continue

            if line.strip().lower() == "break":
                from pixil_utils.loop_compiler import LoopBreak
                raise LoopBreak()

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
                execute_command("endsprite")  # Send endsprite to rgb_matrix_lib
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
                    elif expr.lower() == 'true':
                        var_value = True
                    elif expr.lower() == 'false':
                        var_value = False
                    elif '&' in expr:
                        var_value = evaluate_math_expression(expr, variables)
                    else:
                        var_value = evaluate_math_expression(expr, variables)

                    # OPTIMIZED: Use VariableRegistry.set() instead of dict assignment
                    variables.set(var_name, var_value)
                    
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"  Variable assignment: {var_name} = {var_value}", DEBUG_VERBOSE)
                    
                except ValueError as e:
                    if DEBUG_LEVEL >= DEBUG_SUMMARY:
                        debug_print(f"  Error in variable assignment: {str(e)}", DEBUG_SUMMARY)
                    raise
                except Exception as e:
                    if DEBUG_LEVEL >= DEBUG_SUMMARY:
                        debug_print(f"  Error: Unexpected error in variable assignment: {str(e)}", DEBUG_SUMMARY)
                    raise ValueError(f"Error processing variable assignment: {str(e)}")
                
            # Procedure definition
            elif (proc_def_match := PROCEDURE_DEF_PATTERN.match(line)):
                proc_name = proc_def_match.group(1)   # ✅ safe
                proc_commands = []

                for proc_line in line_generator:
                    if proc_line.strip() == '}':
                        break
                    proc_commands.append(proc_line.strip())

                procedures[proc_name] = proc_commands
                from pixil_utils.loop_compiler import try_compile_procedure_block
                from pixil_utils.optimization_flags import ENABLE_COMPILED_PROCEDURES

                compiled_procedures[proc_name] = (
                    try_compile_procedure_block(proc_commands)
                    if ENABLE_COMPILED_PROCEDURES else None
                )
                if compiled_procedures[proc_name] is not None:
                    debug_print(f"Procedure compiled: {proc_name}", DEBUG_SUMMARY)
                else:
                    debug_print(f"Procedure defined: {proc_name}", DEBUG_SUMMARY)

            # Procedure call
            elif (proc_match := PROCEDURE_CALL_PATTERN.match(line)):
                proc_name = proc_match.group(1)   # ✅ safe, because we already checked proc_match
                invoke_procedure(proc_name)
                if shutdown_requested():
                    raise PixilShutdownRequested()

            # Frame buffer commands
            elif line.startswith('begin_frame'):
                if line == 'begin_frame' or line == 'begin_frame()':
                    start_frame_buffer(False)
                    debug_print("Beginning frame buffer mode (standard)", DEBUG_SUMMARY)
                else:
                    match = FRAME_PARAM_PATTERN.match(line)
                    if match:
                        preserve = match.group(1).strip().lower() == 'true'
                        start_frame_buffer(preserve)
                        mode = "preserve" if preserve else "standard"
                        debug_print(f"Beginning frame buffer mode ({mode})", DEBUG_SUMMARY)

            elif line == 'end_frame' or line == 'end_frame()':
                finish_frame_buffer()
                debug_print("Ending frame buffer mode", DEBUG_SUMMARY)

            # For loop logic
            elif (for_match := FOR_LOOP_PATTERN.match(line)):
                loop_var = for_match.group(1)
                
                start = float(evaluate_math_expression(for_match.group(2).strip(), variables))
                end = float(evaluate_math_expression(for_match.group(3).strip(), variables))
                step = float(evaluate_math_expression(for_match.group(4).strip(), variables))
                
                loop_block = []
                for loop_line in line_generator:
                    if loop_line.strip() == f'endfor {loop_var}':
                        break
                    loop_block.append(loop_line.strip())
                
                from pixil_utils.loop_compiler import (
                    try_compile_loop_block,
                    run_compiled_loop_body,
                    run_compiled_while_body,
                )
                from pixil_utils.optimization_flags import ENABLE_COMPILED_LOOPS

                compiled_loop = try_compile_loop_block(loop_block) if ENABLE_COMPILED_LOOPS else None

                if compiled_loop is not None:
                    run_compiled_loop_body(
                        compiled_loop, loop_var, start, end, step, _get_compiled_ctx(),
                    )
                else:
                    epsilon = 1e-10  # always numeric
                    current_value = start
                    iteration_count = 0
                    while ((step > 0 and current_value <= end + epsilon) or 
                        (step < 0 and current_value >= end - epsilon)):
                        if shutdown_requested() or is_time_expired():
                            if is_time_expired() and not shutdown_requested():
                                print(f"Line {line_number}: Breaking for loop due to timer expiration")
                            break
                        variables[loop_var] = current_value
                        from pixil_utils.loop_compiler import LoopBreak
                        try:
                            process_lines(iter(loop_block))
                        except LoopBreak:
                            break
                        current_value += step
                        iteration_count += 1
                        if iteration_count > 1000000:
                            print(f"Line {line_number}: WARNING: Loop iteration count exceeded 1,000,000. Breaking loop.")
                            break

                if shutdown_requested():
                    raise PixilShutdownRequested()

            # while looping
            elif (while_match := WHILE_LOOP_PATTERN.match(line)):
                condition = while_match.group(1)   # ✅ safe, because while_match is guaranteed not None
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
                
                from pixil_utils.loop_compiler import (
                    try_compile_loop_block,
                    run_compiled_while_body,
                )
                from pixil_utils.optimization_flags import ENABLE_COMPILED_LOOPS

                compiled_while = try_compile_loop_block(loop_block) if ENABLE_COMPILED_LOOPS else None

                if compiled_while is not None:
                    run_compiled_while_body(compiled_while, condition, _get_compiled_ctx())
                else:
                    while evaluate_condition(condition, variables):
                        if shutdown_requested() or is_time_expired():
                            if DEBUG_LEVEL >= DEBUG_VERBOSE and is_time_expired() and not shutdown_requested():
                                debug_print("Breaking while loop due to timer expiration", DEBUG_VERBOSE)
                            break
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"Executing while loop body: {condition}", DEBUG_VERBOSE)
                        from pixil_utils.loop_compiler import LoopBreak
                        try:
                            process_lines(iter(loop_block))
                        except LoopBreak:
                            break

                if shutdown_requested():
                    raise PixilShutdownRequested()

            elif (if_match := IF_PATTERN.match(line)):
                condition = if_match.group(1)   # ✅ safe, Pylance knows if_match isn’t None
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
                    raise ValueError(
                        f"Error in if block: {str(e)}\nCommand: {current_command}"
                    )



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
                elif line == 'hide_background' or line == 'hide_background()':
                    if DEBUG_LEVEL >= DEBUG_SUMMARY:
                        debug_print(f"Found hide_background command: {line}", DEBUG_SUMMARY)
                    store_frame_command('hide_background')
                # Add throttle command handling here
                elif command_match := re.match(r'throttle\((.*)\)', line):
                    try:
                        args = validate_command_params('throttle', command_match.group(1))
                        debug_print(f"Throttle command with args: {args}", DEBUG_VERBOSE)
                        
                        # Parse factor with position information
                        from pixil_utils.test_hooks import effective_throttle

                        factor = effective_throttle(float(parse_value(args[0], 'throttle', 0)))

                        queue.set_throttle(factor)
                        debug_print(f"Set throttle factor to: {factor}", DEBUG_SUMMARY)
                        
                    except (ValueError, KeyError) as e:
                        debug_print(f"Error processing throttle command: {str(e)}", DEBUG_SUMMARY)
                        raise
                elif command_match := re.match(r'fps\((.*)\)', line):
                    try:
                        from pixil_utils.param_bounds import clamp_fps

                        from pixil_utils.test_hooks import effective_fps

                        args = validate_command_params('fps', command_match.group(1))
                        rate = effective_fps(clamp_fps(parse_value(args[0], 'fps', 0)))
                        execute_command(f'fps({rate})')
                        debug_print(f"Set target FPS to: {rate}", DEBUG_SUMMARY)
                    except (ValueError, KeyError) as e:
                        debug_print(f"Error processing fps command: {str(e)}", DEBUG_SUMMARY)
                        raise
                # Handle mplot command
                elif line.startswith('mplot('):
                    global mplot_buffer, mplot_count, draw_buffer, draw_count
                    command_match = COMMAND_PATTERN.match(line)
                    if command_match:
                        try:
                            args = validate_command_params('mplot', command_match.group(2))
                            
                            # Parse parameters and convert to proper types
                            x = int(float(parse_value(args[0], 'mplot', 0)))
                            y = int(float(parse_value(args[1], 'mplot', 1)))
                            
                            # Skip invalid coordinates silently (like plot() does)
                            if not (0 <= x <= 63 and 0 <= y <= 63):
                                # Just skip this mplot - don't add to buffer
                                continue
                            
                            raw_color = parse_value(args[2], 'mplot', 2)
                            
                            # Convert color properly
                            if isinstance(raw_color, str) and raw_color.isdigit():
                                final_color = int(raw_color)
                            else:
                                final_color = raw_color
                            
                            # Convert optional parameters
                            intensity = None
                            if len(args) > 3 and args[3]:
                                intensity = int(float(parse_value(args[3], 'mplot', 3)))
                            
                            burnout = None
                            if len(args) > 4 and args[4]:
                                burnout = int(float(parse_value(args[4], 'mplot', 4)))
                            
                            burnout_mode = None
                            if len(args) > 5 and args[5]:
                                burnout_mode = parse_value(args[5], 'mplot', 5)
                                if isinstance(burnout_mode, str):
                                    burnout_mode = burnout_mode.strip('"').strip("'")

                            if _use_draw_batch_for('mplot'):
                                _append_to_draw_batch(
                                    'mplot',
                                    [x, y, final_color, intensity, burnout, burnout_mode],
                                )
                            else:
                                record = pack_mplot(
                                    x, y, final_color, intensity, burnout, burnout_mode,
                                )
                                mplot_buffer.extend(record)
                                mplot_count += 1

                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(
                                    f"Packed mplot: draw_batch={_use_draw_batch_for('mplot')}",
                                    DEBUG_VERBOSE,
                                )
                                
                        except (ValueError, KeyError) as e:
                            debug_print(f"Error processing mplot command: {str(e)}", DEBUG_SUMMARY)
                            raise

                # Handle mflush command  
                elif line == 'mflush' or line == 'mflush()':
                    from pixil_utils.optimization_flags import ENABLE_DRAW_BATCH
                    if ENABLE_DRAW_BATCH:
                        flush_draw_buffer_commands()
                    elif len(mplot_buffer) > 0:
                        encoded_data = encode_buffer(mplot_buffer)
                        command = f"plot_batch(\"{encoded_data}\")"
                        
                        if DEBUG_LEVEL >= DEBUG_SUMMARY:
                            debug_print(
                                f"Flushing {mplot_count} mplot commands as plot_batch",
                                DEBUG_SUMMARY,
                            )
                        
                        store_frame_command(command)
                        mplot_buffer.clear()
                        mplot_count = 0
                    else:
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print("mflush called with empty buffer", DEBUG_VERBOSE)

                else:   
                    command_match = COMMAND_PATTERN.match(line)
                    if command_match:
                        command_name = command_match.group(1)
                        try:
                            args = validate_command_params(command_name, command_match.group(2))
                            args = expand_legacy_shape_params(command_name, args)
                            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                                debug_print(f"Command: {command_name}", DEBUG_VERBOSE)
                                debug_print(f"Parameters: {args}", DEBUG_VERBOSE)
                            
                            parsed_args = [
                                parse_value(arg, command_name, position)
                                for position, arg in enumerate(args)
                            ]

                            # Preserve positional arity: never drop a supplied argument
                            command_args = []
                            for position, arg in enumerate(parsed_args):
                                if arg != '':
                                    command_args.append(arg)
                                else:
                                    param_name = PARAMETER_TYPES[command_name][position]['name']
                                    raise ValueError(
                                        f"Command '{command_name}': could not resolve "
                                        f"parameter '{param_name}' at position {position}"
                                    )
                            if _use_draw_batch_for(command_name):
                                _append_to_draw_batch(command_name, parsed_args)
                            else:
                                command = f"{command_name}({', '.join(command_args)})"
                                if DEBUG_LEVEL >= DEBUG_SUMMARY:
                                    debug_print(f"Command to execute: {command}", DEBUG_SUMMARY)
                                store_frame_command(command)
                        except (ValueError, KeyError) as e:
                            debug_print(f"Error processing command '{command_name}': {str(e)}", DEBUG_SUMMARY)
                            raise
                        finally:
                            debug_print(f"Command processing completed: {command_name}", DEBUG_VERBOSE)

                    
    def _capture_test_buffer_if_needed() -> None:
        """Fingerprint display buffer for Tier 2 (timer-limited scripts may skip normal_exit path)."""
        if not is_test_mode() or get_metrics().buffer_hash:
            return
        try:
            execute_command('sync_queue')
            queue.wait_until_empty()
            queue.last_command_time = time.time() * 1000
            queue.drain_test_snapshot_reply()
            execute_command('__test_snapshot__')
            queue.wait_for_completion(cooldown=0.2)
            from rgb_matrix_lib.test_inspect import read_buffer_hash_state

            snap_timeout = 2.0 if is_test_mode() else 8.0
            fp = queue.wait_for_test_snapshot(timeout=snap_timeout)
            if not fp:
                fp = read_buffer_hash_state()
            set_buffer_hash(fp if fp else 'empty')
        except Exception:
            set_buffer_hash('empty')

    # Call the generator for file reading
    _test_exit_code = 0
    try:
        from pixil_utils.loop_compiler import LoopBreak
        try:
            process_lines(iter(script_lines))
        except LoopBreak:
            pass
        if shutdown_requested():
            normal_exit = False
            raise PixilShutdownRequested()
        if normal_exit:
            print("Script completed normally - sync queue run")
            debug_print("Script completed normally, adding sync_queue", DEBUG_SUMMARY)
            _capture_test_buffer_if_needed()
    except PixilShutdownRequested:
        normal_exit = False
    except Exception:
        _test_exit_code = 1
        raise
    finally:
        if is_test_mode():
            _capture_test_buffer_if_needed()
            print_summary(_test_exit_code)
        if is_test_mode() and _orig_print is not None:
            import builtins
            builtins.print = _orig_print
        debug_print("\n1. Starting cleanup sequence...", DEBUG_CONCISE)

        if not shutdown_requested():
            cleanup_cooldown = 0.15 if is_test_mode() else 0.3
            flush_draw_buffer_commands()
            flush_sprite_buffer_commands()
            queue_instance.script_transition_cleanup(cooldown=cleanup_cooldown)
            debug_print("Cleanup sequence completed", DEBUG_CONCISE)
        else:
            flush_draw_buffer_commands()
            flush_sprite_buffer_commands()
        gc.collect()
        
    debug_print("Script processing completed", DEBUG_CONCISE)

    if not shutdown_requested():
        execution_reason = "complete" if normal_exit else "interrupted"
        report_metrics(execution_reason, script_name, script_start_time)
    
_stopping_message_sent = False

def signal_handler(signum, frame):
    """Request shutdown on Ctrl+C; main thread performs cleanup."""
    global _stopping_message_sent
    request_shutdown()
    if not _stopping_message_sent:
        _stopping_message_sent = True
        sys.stdout.write("\nStopping...\n")
        sys.stdout.flush()

def clear_all_caches_between_scripts():
    """Clear all optimization caches between scripts."""
    global _VAR_FORMAT_CACHE
    
    # Clear local Pixil.py cache
    _VAR_FORMAT_CACHE.clear()
    
    # Clear math_functions caches
    from pixil_utils.math_functions import clear_all_math_caches
    clear_all_math_caches()
    
    # Clear condition template cache
    from pixil_utils.condition_templates import clear_condition_cache
    clear_condition_cache()

def reset_parse_value_stats():
    """Reset parse value optimization statistics for new script."""
    global _PARSE_VALUE_ATTEMPTS, _VAR_CACHE_HITS, _VAR_CACHE_MISSES
    global _FAST_PATH_HITS, _FAST_PATH_TOTAL
    global _ULTRA_FAST_HITS, _ULTRA_FAST_TOTAL
    global _FAST_PATH_PARSE_HITS, _FAST_PATH_PARSE_TOTAL
    global _PARSE_VALUE_TOTAL_TIME 

    _PARSE_VALUE_ATTEMPTS = 0
    _VAR_CACHE_HITS = 0
    _VAR_CACHE_MISSES = 0
    _FAST_PATH_HITS = 0
    _FAST_PATH_TOTAL = 0
    _ULTRA_FAST_HITS = 0
    _ULTRA_FAST_TOTAL = 0
    _FAST_PATH_PARSE_HITS = 0
    _FAST_PATH_PARSE_TOTAL = 0
    _PARSE_VALUE_TOTAL_TIME = 0.0

# Main Execution
if __name__ == '__main__':
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
            if shutdown_requested():
                break

            scripts = script_manager.get_script_queue()
            
            # Single script mode
            if script_manager.is_single_script():
                announce_script_start(scripts[0], args.duration)
                start_time = time.time()
                try:
                    process_script(scripts[0], execute_command)
                except PixilShutdownRequested:
                    pass
                if shutdown_requested():
                    break
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
                    if shutdown_requested():
                        break

                    current_script = scripts.pop()

                    announce_script_start(current_script, args.duration)
                    try:
                        process_script(current_script, execute_command)
                    except PixilShutdownRequested:
                        pass
                    if shutdown_requested():
                        break
                    clear_timer()
                    clear_all_caches_between_scripts() 
            finally:
                stop_terminal()
                
            # Exit if not wildcard, otherwise continue with reshuffled scripts
            if not script_manager.is_wildcard or shutdown_requested():
                break
                
    except PixilShutdownRequested:
        pass
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        if shutdown_requested():
            exit_pixil(queue_instance, queue_monitor)
        try:
            if queue_monitor:
                queue_monitor.stop()
            if queue_instance:
                queue_instance.shutdown_display(timeout=4.0)
            stop_terminal()
        except Exception:
            sys.exit(1)