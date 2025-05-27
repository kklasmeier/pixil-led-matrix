"""
Mathematical functions and utilities for Pixil script interpreter.
Provides safe math operations without variable state dependencies.
"""

import math
import random
import re
from typing import Dict, Any, Union, Optional, Tuple
from .debug import (DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE, DEBUG_LEVEL, set_debug_level, debug_print)
from .array_manager import validate_array_access
from collections import OrderedDict
from .jit_compiler import JITExpressionCache

# Regex pattern for identifying math expressions
MATH_EXPR_PATTERN = re.compile(r'[\+\-\*/\(\)]|v_\w+|\d+\.?\d*')
ARRAY_ACCESS_PATTERN = re.compile(r'(v_\w+)\[([^[\]]*(?:\[[^[\]]*\][^[\]]*)*)\]')
VARIABLE_PATTERN = re.compile(r'v_\w+')
ARRAY_INDEX_PATTERN = re.compile(r'(v_\w+)\[([^\[\]]+)\]')
CONCAT_ARRAY_PATTERN = re.compile(r'(v_\w+)\[(.+?)\]')

_EXPR_CACHE = OrderedDict()
_EXPR_CACHE_SIZE = 128 # Adjust based on typical script complexity
_EXPR_CACHE_HITS = 0
_EXPR_CACHE_MISSES = 0
_FAST_MATH_HITS = 0
_FAST_MATH_TOTAL = 0
_EXPRESSION_RESULT_CACHE = {}
_CACHE_HITS = 0
_CACHE_MISSES = 0
_CACHE_MAX_SIZE = 500 
_JIT_CACHE = JITExpressionCache(max_size=500)
_JIT_ATTEMPTS = 0
_JIT_HITS = 0
_JIT_COMPILATION_FAILURES = 0
_FAILED_SCRIPT_LINES = set()  # Use set for faster lookups
_JIT_LINE_CACHE_SKIPS = 0
_current_script_line = None  # Store current script line locally

# Phase 2: Pre-compiled regex patterns for fast math expressions
SIMPLE_ADD_PATTERN = re.compile(r'^(v_\w+)\s*\+\s*(-?\d*\.?\d+)$')
SIMPLE_SUB_PATTERN = re.compile(r'^(v_\w+)\s*-\s*(-?\d*\.?\d+)$')  
SIMPLE_MUL_PATTERN = re.compile(r'^(v_\w+)\s*\*\s*(-?\d*\.?\d+)$')
SIMPLE_DIV_PATTERN = re.compile(r'^(v_\w+)\s*/\s*(-?\d*\.?\d+)$')
SIMPLE_MOD_PATTERN = re.compile(r'^(v_\w+)\s*%\s*(-?\d*\.?\d+)$')
SIMPLE_ARRAY_ACCESS_PATTERN = re.compile(r'^(v_\w+)\[(v_\w+)\]$')
NUMBER_PATTERN = re.compile(r'^-?\d*\.?\d+$')
RANDOM_PATTERN = re.compile(r'random\s*\(\s*(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)\s*,\s*(\d+)\s*\)')

# Two variable patterns
VAR_ADD_VAR_PATTERN = re.compile(r'^(v_\w+)\s*\+\s*(v_\w+)$')
VAR_MUL_VAR_PATTERN = re.compile(r'^(v_\w+)\s*\*\s*(v_\w+)$')

def set_current_script_line(line):
    """Set the current script line for JIT failure caching."""
    global _current_script_line
    _current_script_line = line

def try_jit_compilation(expr: str, variables: Dict[str, Any]) -> Optional[Union[int, float, str]]:
    """
    Phase 3: JIT compilation with line-based failure caching.
    """
    global _JIT_ATTEMPTS, _JIT_HITS, _JIT_COMPILATION_FAILURES, _JIT_LINE_CACHE_SKIPS, _current_script_line
    
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"JIT attempt for: {expr}", DEBUG_VERBOSE)
    
    # NEW: Check line-based failure cache first
    if _current_script_line:
        cache_key = hash(_current_script_line)
        if cache_key in _FAILED_SCRIPT_LINES:
            _JIT_LINE_CACHE_SKIPS += 1
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"JIT skipped (known failure): {expr}", DEBUG_VERBOSE)
            return None
    
    _JIT_ATTEMPTS += 1
    
    try:
        result = _JIT_CACHE.evaluate(expr, variables)
        
        if result is not None:
            _JIT_HITS += 1
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"JIT compilation successful: {expr} = {result}", DEBUG_VERBOSE)
            return result
        else:
            # Mark this script line as always failing
            if _current_script_line:
                cache_key = hash(_current_script_line)
                _FAILED_SCRIPT_LINES.add(cache_key)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"JIT failed, caching line: {_current_script_line[:50]}...", DEBUG_VERBOSE)
            
            _JIT_COMPILATION_FAILURES += 1
            return None
            
    except Exception as e:
        # Mark this script line as always failing
        if _current_script_line:
            cache_key = hash(_current_script_line)
            _FAILED_SCRIPT_LINES.add(cache_key)
        
        _JIT_COMPILATION_FAILURES += 1
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"JIT compilation error for '{expr}': {str(e)}", DEBUG_VERBOSE)
        return None
            
    except Exception as e:
        # Mark this script line as always failing
        if current_command:
            cache_key = hash(current_command)
            _FAILED_SCRIPT_LINES.add(cache_key)
        
        _JIT_COMPILATION_FAILURES += 1
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"JIT compilation error for '{expr}': {str(e)}", DEBUG_VERBOSE)
        return None
    
def create_cache_key(expr: str, variables: Dict[str, Any]) -> Optional[tuple]:
    """
    Create a cache key for expression + relevant variable values.
    Returns None if expression shouldn't be cached.
    """
    if not isinstance(expr, str) or len(expr) > 100:
        return None  # Don't cache very long expressions
    
    # Find variables used in this expression
    import re
    var_matches = re.findall(r'v_\w+', expr)
    
    if not var_matches:
        return None  # No variables, probably a constant
    
    # Create key with only relevant variable values
    relevant_vars = []
    for var in var_matches:
        if var in variables:
            value = variables[var]
            # Only cache if value is simple (number or short string)
            if isinstance(value, (int, float, str)) and (not isinstance(value, str) or len(str(value)) < 20):
                relevant_vars.append((var, value))
            else:
                return None  # Contains complex values, don't cache
    
    return (expr, tuple(sorted(relevant_vars)))

def get_cached_result(cache_key) -> Optional[Any]:
    """Get cached result if available."""
    global _CACHE_HITS, _CACHE_MISSES
    
    if cache_key in _EXPRESSION_RESULT_CACHE:
        _CACHE_HITS += 1
        return _EXPRESSION_RESULT_CACHE[cache_key]
    else:
        _CACHE_MISSES += 1
        return None

def cache_result(cache_key, result):
    """Cache expression result with size limiting."""
    global _EXPRESSION_RESULT_CACHE
    
    # Limit cache size to prevent memory growth
    if len(_EXPRESSION_RESULT_CACHE) >= _CACHE_MAX_SIZE:
        # Remove oldest entries (simple FIFO eviction)
        keys_to_remove = list(_EXPRESSION_RESULT_CACHE.keys())[:50]
        for key in keys_to_remove:
            del _EXPRESSION_RESULT_CACHE[key]
    
    _EXPRESSION_RESULT_CACHE[cache_key] = result

def report_fast_math_stats():
    """Report fast math path performance statistics."""
    global _FAST_MATH_HITS, _FAST_MATH_TOTAL
    
    if _FAST_MATH_TOTAL > 0:
        hit_rate = (_FAST_MATH_HITS / _FAST_MATH_TOTAL) * 100
        miss_count = _FAST_MATH_TOTAL - _FAST_MATH_HITS
        
        print(f"Phase 2 Fast Math Statistics:")
        print(f"  Math expressions attempted: {_FAST_MATH_TOTAL:,}")
        print(f"  Fast math hits: {_FAST_MATH_HITS:,} ({hit_rate:.1f}%)")
        print(f"  Fast math misses: {miss_count:,} ({100-hit_rate:.1f}%)")
        
        if _FAST_MATH_HITS > 0:
            # Estimate time savings (assuming 8x speedup for fast path vs eval)
            estimated_savings = (_FAST_MATH_HITS * 35) / 1000000  # 35 microseconds saved per hit
            print(f"  Estimated time saved: {estimated_savings:.3f} seconds")
    else:
        print("Phase 2 Fast Math: No math expressions detected")

def report_jit_stats():
    """Report JIT compilation statistics with line cache efficiency."""
    global _JIT_ATTEMPTS, _JIT_HITS, _JIT_COMPILATION_FAILURES, _JIT_LINE_CACHE_SKIPS
    
    print("JIT Compilation Statistics:")
    
    if _JIT_ATTEMPTS > 0 or _JIT_LINE_CACHE_SKIPS > 0:
        # Basic stats
        hit_rate = (_JIT_HITS / _JIT_ATTEMPTS * 100) if _JIT_ATTEMPTS > 0 else 0
        failure_rate = (_JIT_COMPILATION_FAILURES / _JIT_ATTEMPTS * 100) if _JIT_ATTEMPTS > 0 else 0
        
        print(f"  JIT attempts: {_JIT_ATTEMPTS:,}")
        print(f"  JIT hits: {_JIT_HITS:,} ({hit_rate:.1f}%)")
        print(f"  JIT failures: {_JIT_COMPILATION_FAILURES:,} ({failure_rate:.1f}%)")
        
        # NEW: Line cache efficiency
        print(f"  Line cache skips: {_JIT_LINE_CACHE_SKIPS:,}")
        
        total_expressions = _JIT_ATTEMPTS + _JIT_LINE_CACHE_SKIPS
        if total_expressions > 0:
            skip_rate = (_JIT_LINE_CACHE_SKIPS / total_expressions) * 100
            print(f"  Skip efficiency: {skip_rate:.1f}% of expressions avoided")
            
            # Time savings estimation
            skip_time_saved = (_JIT_LINE_CACHE_SKIPS * 250) / 1000000  # 250 μs per avoided attempt
            print(f"  Time saved by skipping: {skip_time_saved:.3f} seconds")
        
        # Get cache statistics
        cache_stats = _JIT_CACHE.get_stats()
        print(f"  Cache hit rate: {cache_stats.hit_rate:.1f}%")
        print(f"  Cache size: {_JIT_CACHE.cache_size} expressions")
        print(f"  Compilation time: {cache_stats.compilation_time:.4f}s")
        print(f"  Total time saved: {cache_stats.total_time_saved:.4f}s")
        
        # Line cache stats
        print(f"  Failed lines cached: {len(_FAILED_SCRIPT_LINES)} unique lines")
        
    else:
        print("  No JIT compilation attempts")

def reset_jit_stats():
    """Reset JIT compilation statistics for new script."""
    global _JIT_ATTEMPTS, _JIT_HITS, _JIT_COMPILATION_FAILURES, _JIT_LINE_CACHE_SKIPS
    _JIT_ATTEMPTS = 0
    _JIT_HITS = 0
    _JIT_COMPILATION_FAILURES = 0
    _JIT_LINE_CACHE_SKIPS = 0
    # Note: Don't reset _FAILED_SCRIPT_LINES - keep learning across scripts

def reset_fast_math_stats():
    """Reset fast math statistics for new script."""
    global _FAST_MATH_HITS, _FAST_MATH_TOTAL
    _FAST_MATH_HITS = 0
    _FAST_MATH_TOTAL = 0

def report_expression_cache_stats():
    """Report expression caching statistics."""
    global _CACHE_HITS, _CACHE_MISSES, _EXPRESSION_RESULT_CACHE
    
    total_attempts = _CACHE_HITS + _CACHE_MISSES
    if total_attempts > 0:
        hit_rate = (_CACHE_HITS / total_attempts) * 100
        cache_size = len(_EXPRESSION_RESULT_CACHE)
        
        print(f"Expression Cache Statistics:")
        print(f"  Cache attempts: {total_attempts:,}")
        print(f"  Cache hits: {_CACHE_HITS:,} ({hit_rate:.1f}%)")
        print(f"  Cache misses: {_CACHE_MISSES:,}")
        print(f"  Cache size: {cache_size} entries")
        
        if _CACHE_HITS > 0:
            # Estimate time savings (each cache hit saves ~30 microseconds)
            estimated_savings = (_CACHE_HITS * 30) / 1000000
            print(f"  Estimated time saved: {estimated_savings:.3f} seconds")
    else:
        print("Expression Cache: No cacheable expressions found")

def reset_expression_cache_stats():
    """Reset cache statistics."""
    global _CACHE_HITS, _CACHE_MISSES, _EXPRESSION_RESULT_CACHE
    _CACHE_HITS = 0
    _CACHE_MISSES = 0
    _EXPRESSION_RESULT_CACHE.clear()

def try_fast_number(expr: str) -> Optional[Union[int, float]]:
    """
    Handle simple numeric values without any processing.
    """
    if NUMBER_PATTERN.match(expr):
        try:
            # Try integer first, then float
            if '.' in expr:
                result = float(expr)
            else:
                result = int(expr)
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Fast number: {expr} = {result}", DEBUG_VERBOSE)
            return result
        except (ValueError, TypeError):
            pass
    return None

def try_fast_array_access(expr: str, variables: Dict[str, Any]) -> Optional[Union[int, float, str]]:
    """
    Handle simple array access like v_array[v_index] without complex parsing.
    """
    match = SIMPLE_ARRAY_ACCESS_PATTERN.match(expr)
    if match:
        array_name, index_var = match.groups()
        
        if array_name in variables and index_var in variables:
            try:
                array = variables[array_name]
                index_value = variables[index_var]
                
                # Ensure index is numeric
                if isinstance(index_value, (int, float)):
                    index = int(index_value)
                    
                    # Check if it's a PixilArray or regular array
                    if hasattr(array, '__getitem__'):
                        # For PixilArray, use the optimized access
                        if hasattr(array, 'data') and 0 <= index < len(array.data):
                            result = array[index]
                        # For regular Python arrays/lists
                        elif isinstance(array, (list, tuple)) and 0 <= index < len(array):
                            result = array[index]
                        else:
                            return None  # Out of bounds or invalid
                            
                        if DEBUG_LEVEL >= DEBUG_VERBOSE:
                            debug_print(f"Fast array access: {array_name}[{index_var}] = {array_name}[{index}] = {result}", DEBUG_VERBOSE)
                        return result
                        
            except (ValueError, TypeError, IndexError, AttributeError):
                pass
    return None

def try_fast_arithmetic(expr: str, variables: Dict[str, Any]) -> Optional[Union[int, float]]:
    """
    Try to evaluate simple arithmetic expressions without using eval().
    Returns None if the expression doesn't match supported patterns.
    """
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Trying fast arithmetic for: {expr}", DEBUG_VERBOSE)
    
    # Simple variable + number
    match = SIMPLE_ADD_PATTERN.match(expr)
    if match:
        var_name, number = match.groups()
        if var_name in variables:
            try:
                result = float(variables[var_name]) + float(number)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast add: {var_name} + {number} = {result}", DEBUG_VERBOSE)
                return result
            except (ValueError, TypeError):
                pass
    
    # Simple variable - number  
    match = SIMPLE_SUB_PATTERN.match(expr)
    if match:
        var_name, number = match.groups()
        if var_name in variables:
            try:
                result = float(variables[var_name]) - float(number)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast sub: {var_name} - {number} = {result}", DEBUG_VERBOSE)
                return result
            except (ValueError, TypeError):
                pass
    
    # Simple variable * number
    match = SIMPLE_MUL_PATTERN.match(expr)
    if match:
        var_name, number = match.groups()
        if var_name in variables:
            try:
                result = float(variables[var_name]) * float(number)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast mul: {var_name} * {number} = {result}", DEBUG_VERBOSE)
                return result
            except (ValueError, TypeError):
                pass
    
    # Simple variable / number
    match = SIMPLE_DIV_PATTERN.match(expr)
    if match:
        var_name, number = match.groups()
        if var_name in variables:
            try:
                divisor = float(number)
                if divisor != 0:
                    result = float(variables[var_name]) / divisor
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Fast div: {var_name} / {number} = {result}", DEBUG_VERBOSE)
                    return result
            except (ValueError, TypeError, ZeroDivisionError):
                pass
    
    # Simple variable % number (very common for array indexing)
    match = SIMPLE_MOD_PATTERN.match(expr)
    if match:
        var_name, number = match.groups()
        if var_name in variables:
            try:
                modulus = float(number)
                if modulus != 0:
                    result = float(variables[var_name]) % modulus
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Fast mod: {var_name} % {number} = {result}", DEBUG_VERBOSE)
                    return result
            except (ValueError, TypeError, ZeroDivisionError):
                pass
    
    # Two variables: var1 + var2
    match = VAR_ADD_VAR_PATTERN.match(expr)
    if match:
        var1, var2 = match.groups()
        if var1 in variables and var2 in variables:
            try:
                result = float(variables[var1]) + float(variables[var2])
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast var add: {var1} + {var2} = {result}", DEBUG_VERBOSE)
                return result
            except (ValueError, TypeError):
                pass
    
    # Two variables: var1 * var2
    match = VAR_MUL_VAR_PATTERN.match(expr)
    if match:
        var1, var2 = match.groups()
        if var1 in variables and var2 in variables:
            try:
                result = float(variables[var1]) * float(variables[var2])
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast var mul: {var1} * {var2} = {result}", DEBUG_VERBOSE)
                return result
            except (ValueError, TypeError):
                pass

def evaluate_math_expression(expr: str, variables: Dict[str, Any]) -> Union[int, float, str]:
    """
    Evaluate a mathematical or string expression with variable substitution.
    Uses optimized LRU caching for performance.
    """
    global _EXPR_CACHE, _EXPR_CACHE_HITS, _EXPR_CACHE_MISSES
    
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Evaluating expression: {expr}", DEBUG_VERBOSE)
        debug_print(f"Variables state: {variables}", DEBUG_VERBOSE)
    
    # Fast paths for common cases
    if not isinstance(expr, str):
        return expr
    if expr.startswith('v_') and expr in variables:
        return variables[expr]

    # ===== PHASE 2 + 2.5 OPTIMIZATION: EXPANDED FAST PATHS =====
    if isinstance(expr, str) and not ('&' in expr or '"' in expr or "'" in expr):
        global _FAST_MATH_HITS, _FAST_MATH_TOTAL
        _FAST_MATH_TOTAL += 1
        
        # NEW: Try simple numbers first (HUGE opportunity)
        fast_result = try_fast_number(expr)
        if fast_result is not None:
            _FAST_MATH_HITS += 1
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Fast number hit: {expr} = {fast_result}", DEBUG_VERBOSE)
            return fast_result
        
        # NEW: Try simple array access (v_array[v_index])
        if '[' in expr and ']' in expr and expr.count('[') == 1:
            fast_result = try_fast_array_access(expr, variables)
            if fast_result is not None:
                _FAST_MATH_HITS += 1
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Fast array hit: {expr} = {fast_result}", DEBUG_VERBOSE)
                return fast_result
        
        # EXISTING: Try simple arithmetic
        fast_result = try_fast_arithmetic(expr, variables)
        if fast_result is not None:
            _FAST_MATH_HITS += 1
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Fast arithmetic hit: {expr} = {fast_result}", DEBUG_VERBOSE)
            return fast_result
    # ===== END PHASE 2 + 2.5 OPTIMIZATION =====

    # ===== PHASE 3: JIT COMPILATION =====
    jit_result = try_jit_compilation(expr, variables)
    if jit_result is not None:
        return jit_result
    # ===== END PHASE 3 =====
    
    # Parse variables early so we can check for random in both original and parsed expressions
    parsed_expr = substitute_variables(expr, variables)
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"After substitution: {parsed_expr}", DEBUG_VERBOSE)

    # Cache key and tracking remain the same
    cache_key = None
    
    try:
        # Caching logic remains the same
        if isinstance(expr, str) and "random" not in expr and "random" not in parsed_expr:
            # Same caching logic as before...
            # (Code omitted for brevity)
            
            # Try to use cache if we have a valid key
            if cache_key is not None and cache_key in _EXPR_CACHE:
                # Same cache hit logic as before...
                return result
            
            # Cache miss logic remains the same
            if cache_key is not None:
                _EXPR_CACHE_MISSES += 1
        
        # Handle string concatenation
        if '&' in expr:
            result = evaluate_string_concatenation(expr, variables)
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Concatenation result: {result}", DEBUG_VERBOSE)
            return result

        # Process array accesses - THIS IS THE MODIFIED SECTION
        if '[' in expr and ']' in expr:
            # Find the innermost array access
            array_match = ARRAY_INDEX_PATTERN.search(expr)
            if array_match:
                array_name = array_match.group(1)
                index_expr = array_match.group(2)
                full_match = array_match.group(0)
                
                # Get array
                if array_name not in variables:
                    raise ValueError(f"Array '{array_name}' not found")
                array = variables[array_name]
                
                # Evaluate index expression
                index = evaluate_math_expression(index_expr, variables)
                
                # Ensure index is an integer
                if isinstance(index, float):
                    index = int(index)
                elif not isinstance(index, int):
                    raise ValueError(f"Array index must be a number, got {type(index)}")
                    
                # Get array value
                value = array[index]
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Array access {array_name}[{index}] = {value}", DEBUG_VERBOSE)
                
                # Replace array access with its value
                expr_modified = expr.replace(full_match, str(value))
                
                # Check if there are still array accesses to process
                if '[' in expr_modified and ']' in expr_modified:
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Processing nested array access: {expr_modified}", DEBUG_VERBOSE)
                    # Process the modified expression with the inner array access resolved
                    return evaluate_math_expression(expr_modified, variables)
                else:
                    # No more array accesses, treat as normal expression
                    expr = expr_modified
                    
                    # If the result is a direct string (from string array), return it
                    if isinstance(value, str) and expr == str(value):
                        return value
            
        # The rest of the function remains the same
        
        # Handle string literals
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr.strip('"\'')

        # ===== EXPRESSION RESULT CACHING =====
        # Try to get cached result first (but not for random expressions)
        if "random" not in expr and "random" not in parsed_expr:
            cache_key = create_cache_key(expr, variables)
            if cache_key is not None:
                cached_result = get_cached_result(cache_key)
                if cached_result is not None:
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Expression cache hit: {expr}", DEBUG_VERBOSE)
                    return cached_result

        # Try evaluating as math expression (existing code)
        eval_env = {**MATH_FUNCTIONS, '__builtins__': None}
        result = eval(parsed_expr, {"__builtins__": None}, eval_env)

        # Cache the result if we have a cache key (but not for random expressions)
        if "random" not in expr and "random" not in parsed_expr:
            cache_key = create_cache_key(expr, variables)
            if cache_key is not None:
                cache_result(cache_key, result)
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Expression cached: {expr} = {result}", DEBUG_VERBOSE)
        # ===== END EXPRESSION RESULT CACHING =====

        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Evaluation result: {result}", DEBUG_VERBOSE)
        
        # Cache the result if appropriate (but never cache random expressions)
        if cache_key is not None and "random" not in expr and "random" not in parsed_expr:
            # Implement LRU eviction with OrderedDict
            if len(_EXPR_CACHE) >= _EXPR_CACHE_SIZE:
                # Remove oldest item (first in the OrderedDict)
                _EXPR_CACHE.popitem(last=False)
            
            # Add new item to end (most recently used)
            _EXPR_CACHE[cache_key] = result
        
        return result
        
    except Exception as e:
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Error evaluating expression: {str(e)}", DEBUG_VERBOSE)
        if expr.startswith('v_') and expr in variables:
            return variables[expr]
        raise ValueError(f"Error evaluating expression '{expr}': {str(e)}")


def random_float(min_val, max_val, precision):
    """
    Generate a random float between min_val and max_val with specified precision.
    
    Args:
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        precision: Number of decimal places (0 returns integer)
        
    Returns:
        Random number within specified range and precision
    """
    range_val = max_val - min_val
    random_val = random.random() * range_val + min_val
    if precision == 0:
        result = int(round(random_val))
    else:
        result = round(random_val, precision)
    return result

def has_math_expression(value: str) -> bool:
    """
    Check if a string contains a mathematical expression.
    
    Args:
        value: String to check
        
    Returns:
        True if string contains math operators or variable references
    """
    if not isinstance(value, str):
        return False
        
    return any(c in value for c in '+-*/()') or 'v_' in value

def substitute_variables(expr: str, variables: Dict[str, Any]) -> str:
    """
    Replace variable references with their values in an expression. Handles array access expressions.
    
    Args:
        expr: Expression containing variable references
        variables: Dictionary of current variable values
        
    Returns:
        Expression with variables replaced by their values
        
    Raises:
        ValueError: If variable not found
    """

    """Replace variable references with their values in an expression."""

    debug_print(f"Substituting in expression: {expr}", DEBUG_VERBOSE)

    # Process all array accesses first
    def process_array_accesses(expr: str) -> str:
        """Find and process each array access, replacing with its value"""
        
        # Match array access pattern: v_name[...] allowing nested brackets
        # array_pattern = re.compile(r'(v_\w+)\[([^[\]]*(?:\[[^[\]]*\][^[\]]*)*)\]')
        
        while True:
            match = ARRAY_ACCESS_PATTERN.search(expr)
            if not match:
                break
                
            array_name = match.group(1)
            index_expr = match.group(2)
            full_match = match.group(0)
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Found array access: {array_name}[{index_expr}]", DEBUG_VERBOSE)
            
            try:
                # First recursively process any array accesses in the index expression
                processed_index = process_array_accesses(index_expr)
                
                # Then evaluate the processed index expression
                index_value = evaluate_math_expression(processed_index, variables)
                
                # Get array value using the computed index
                array_value = validate_array_access(array_name, index_value, variables)
                
                # Replace this array access with its value
                expr = expr[:match.start()] + str(array_value) + expr[match.end():]
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Expression after substitution: {expr}", DEBUG_VERBOSE)
                
            except Exception as e:
                raise ValueError(f"Error processing array access '{full_match}': {str(e)}")
        
        return expr

    # First handle all array accesses (including nested ones)
    expr = process_array_accesses(expr)
    
    # Then handle any remaining simple variables
    def replace_var(match):
        var_name = match.group(0)
        if var_name.startswith('v_'):
            if var_name not in variables:
                raise ValueError(f"Variable '{var_name}' not found")
            return str(variables[var_name])
        return var_name

    expr = VARIABLE_PATTERN.sub(replace_var, expr)
    
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Final expression after all substitutions: {expr}", DEBUG_VERBOSE)
    return expr

def split_outside_quotes(text, delimiter):
    """Split string by delimiter only when outside quotes and parentheses."""
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Splitting text: '{text}' by delimiter: '{delimiter}'", DEBUG_VERBOSE)
    
    result = []
    current = ""
    in_quotes = False
    quote_char = None
    paren_level = 0
    
    i = 0
    while i < len(text):
        if text[i] in ('"', "'"):
            # Handle quotes
            if not in_quotes:
                in_quotes = True
                quote_char = text[i]
            elif text[i] == quote_char:
                in_quotes = False
            current += text[i]
        elif text[i] == '(':
            paren_level += 1
            current += text[i]
        elif text[i] == ')':
            paren_level -= 1
            if paren_level < 0:
                raise ValueError(f"Unbalanced parentheses in condition: '{text}'")
            current += text[i]
        elif (not in_quotes and paren_level == 0 and 
              text[i:i+len(delimiter)] == delimiter):
            result.append(current)
            current = ""
            i += len(delimiter) - 1
        else:
            current += text[i]
        i += 1
    
    # Check for unterminated quotes
    if in_quotes:
        raise ValueError(f"Unterminated quotes in condition: '{text}'")
    
    # Check for unbalanced parentheses
    if paren_level > 0:
        raise ValueError(f"Unbalanced parentheses in condition: '{text}'")
        
    if current:
        result.append(current)
    
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Split result: {result}", DEBUG_VERBOSE)
    
    return result

def evaluate_simple_condition(condition, variables):
    """Evaluate a simple condition with a single comparison operator."""
    condition = condition.strip()
    
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Evaluating simple condition: '{condition}'", DEBUG_VERBOSE)
    
    # Check if the condition is empty
    if not condition:
        raise ValueError("Empty condition found in compound expression")
    
    # Handle literal boolean values
    condition_lower = condition.lower()
    if condition_lower == 'true':
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Simple condition is literal 'true'", DEBUG_VERBOSE)
        return True
    if condition_lower == 'false':
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Simple condition is literal 'false'", DEBUG_VERBOSE)
        return False
    
    # Handle single variable
    if condition.startswith('v_') and condition in variables:
        result = bool(variables[condition])
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Simple condition is variable '{condition}' = {result}", DEBUG_VERBOSE)
        return result
    
    # Check for common comparison operators
    operators = ['>=', '<=', '==', '!=', '>', '<']  # Order matters for parsing
    for op in operators:
        if op in condition:
            parts = condition.split(op, 1)  # Split on first occurrence only
            if len(parts) != 2:
                raise ValueError(f"Invalid condition format: '{condition}'")
                
            left, right = parts
            left = left.strip()
            right = right.strip()
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Found operator '{op}' in condition", DEBUG_VERBOSE)
                debug_print(f"Left side: '{left}', Right side: '{right}'", DEBUG_VERBOSE)
            
            try:
                # Evaluate left and right sides
                left_value = evaluate_math_expression(left, variables)
                right_value = evaluate_math_expression(right, variables)
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Left value: {left_value}, Right value: {right_value}", DEBUG_VERBOSE)
                
                # String comparison if either side is a string
                if isinstance(left_value, str) or isinstance(right_value, str):
                    left_str = str(left_value).strip('"\'')
                    right_str = str(right_value).strip('"\'')
                    
                    if op == '==': 
                        result = left_str == right_str
                    elif op == '!=': 
                        result = left_str != right_str
                    elif op in ['>', '<', '>=', '<=']: 
                        raise ValueError(f"Operator {op} not supported for string comparison")
                    
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"String comparison result: {result}", DEBUG_VERBOSE)
                    return result
                
                # Numeric comparison
                if op == '>=': result = left_value >= right_value
                elif op == '<=': result = left_value <= right_value
                elif op == '>': result = left_value > right_value
                elif op == '<': result = left_value < right_value
                elif op == '==': result = left_value == right_value
                elif op == '!=': result = left_value != right_value
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Numeric comparison result: {result}", DEBUG_VERBOSE)
                return result
                
            except Exception as e:
                raise ValueError(f"Error evaluating condition '{condition}': {str(e)}")
    
    # No comparison operator found, evaluate as boolean
    try:
        result = evaluate_math_expression(condition, variables)
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Boolean expression result: {bool(result)}", DEBUG_VERBOSE)
        return bool(result)
    except Exception as e:
        raise ValueError(f"Error evaluating boolean expression '{condition}': {str(e)}")
    
def evaluate_condition(condition, variables):
    """
    Evaluate a condition that may contain logical operators (and, or).
    Args:
        condition: Condition string (e.g., "v_x > 5 and v_y < 10 or v_z == 15")
        variables: Dictionary of current variable values
        
    Returns:
        Boolean result of condition evaluation
    """
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Evaluating condition: '{condition}'", DEBUG_VERBOSE)
    
    # Validate condition format
    condition = condition.strip()
    if not condition:
        raise ValueError("Empty condition")
    
    # Check for common syntax errors
    if condition.endswith(" and") or condition.endswith(" or"):
        raise ValueError(f"Incomplete compound condition: '{condition}'")
    
    # Handle simple cases first
    condition_lower = condition.lower()
    if condition_lower == 'true':
        return True
    if condition_lower == 'false':
        return False
    if condition.startswith('v_') and condition in variables:
        return bool(variables[condition])
    
    # Check if this is a compound condition
    has_and = " and " in condition
    has_or = " or " in condition
    
    if not (has_and or has_or):
        # Simple condition (no compound operators)
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"No compound operators found, evaluating as simple condition", DEBUG_VERBOSE)
        return evaluate_simple_condition(condition, variables)
    
    # TODO: Future enhancement - Support for explicit parentheses
    
    try:
        # Split by 'or' operators first (lower precedence)
        or_parts = split_outside_quotes(condition, " or ")
        
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"OR parts: {or_parts}", DEBUG_VERBOSE)
        
        # Evaluate 'or' parts (true if any part is true)
        for i, or_part in enumerate(or_parts):
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Evaluating OR part {i+1}/{len(or_parts)}: '{or_part}'", DEBUG_VERBOSE)
            
            # Split by 'and' operators (higher precedence)
            and_parts = split_outside_quotes(or_part, " and ")
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"AND parts: {and_parts}", DEBUG_VERBOSE)
            
            # Evaluate 'and' parts (true if all parts are true)
            and_result = True
            for j, and_part in enumerate(and_parts):
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Evaluating AND part {j+1}/{len(and_parts)}: '{and_part}'", DEBUG_VERBOSE)
                
                part_result = evaluate_simple_condition(and_part.strip(), variables)
                
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"AND part result: {part_result}", DEBUG_VERBOSE)
                
                and_result = and_result and part_result
                if not and_result:
                    if DEBUG_LEVEL >= DEBUG_VERBOSE:
                        debug_print(f"Short-circuit: AND part {j+1} is false, skipping remaining parts", DEBUG_VERBOSE)
                    break  # Short-circuit: no need to evaluate further parts
            
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"OR part {i+1} result: {and_result}", DEBUG_VERBOSE)
            
            # If any 'or' part is true, the whole condition is true
            if and_result:
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Short-circuit: OR part {i+1} is true, whole condition is true", DEBUG_VERBOSE)
                return True
        
        # If no 'or' part is true, the whole condition is false
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"All OR parts are false, whole condition is false", DEBUG_VERBOSE)
        return False
        
    except Exception as e:
        raise ValueError(f"Error evaluating compound condition '{condition}': {str(e)}")

def evaluate_string_concatenation(expr: str, variables: Dict[str, Any]) -> str:
    """
    Evaluate a string expression containing concatenation operators.
    Handles array access, variables, and string literals.
    """
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Starting string concatenation for: {expr}", DEBUG_VERBOSE)
    
    # Split into parts by &
    parts = [p.strip() for p in expr.split('&')]
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Split into parts: {parts}", DEBUG_VERBOSE)
    
    # Process each part
    results = []
    for part in parts:
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Processing part: {part}", DEBUG_VERBOSE)
        
        # Handle array access first
        array_match = CONCAT_ARRAY_PATTERN.match(part)
        if array_match:
            array_name = array_match.group(1)
            index_expr = array_match.group(2)
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Found array access: {array_name}[{index_expr}]", DEBUG_VERBOSE)
            
            try:
                if array_name not in variables:
                    raise ValueError(f"Array '{array_name}' not found")
                array = variables[array_name]
                
                # Evaluate index
                index = evaluate_math_expression(index_expr, variables)
                value = array[int(index)]
                if DEBUG_LEVEL >= DEBUG_VERBOSE:
                    debug_print(f"Array access result: {value}", DEBUG_VERBOSE)
                results.append(str(value))
                continue
            except Exception as e:
                raise ValueError(f"Error in array access: {str(e)}")
        
        # Handle quoted strings
        if (part.startswith('"') and part.endswith('"')) or \
           (part.startswith("'") and part.endswith("'")):
            value = part[1:-1]
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"String literal: {value}", DEBUG_VERBOSE)
            results.append(value)
            continue
        
        # Handle variables
        if part.startswith('v_'):
            if part not in variables:
                raise ValueError(f"Variable '{part}' not found")
            value = variables[part]
            if DEBUG_LEVEL >= DEBUG_VERBOSE:
                debug_print(f"Variable value: {value}", DEBUG_VERBOSE)
            results.append(str(value))
            continue
        
        # Handle direct values
        results.append(part)
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Direct value: {part}", DEBUG_VERBOSE)
    
    # Join results
    result = ''.join(results)
    if DEBUG_LEVEL >= DEBUG_VERBOSE:
        debug_print(f"Final concatenated result: {result}", DEBUG_VERBOSE)
    return result

# Math function dictionary containing all allowed mathematical operations
MATH_FUNCTIONS = {
    # Basic Math
    'cos': math.cos,
    'sin': math.sin,
    'tan': math.tan,
    'abs': abs,
    'pow': pow,
    'sqrt': math.sqrt,
    'exp': math.exp,
    'log': math.log,
    'log10': math.log10,
    
    # Rounding Functions
    'round': round,
    'floor': math.floor,
    'ceil': math.ceil,
    'trunc': math.trunc,
    'int': int,
    
    # Additional Trigonometry
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'atan2': math.atan2,
    'degrees': math.degrees,
    'radians': math.radians,
    
    # Min/Max Operations
    'min': min,
    'max': max,
    
    # Constants
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
    
    # Physics-friendly Functions
    'copysign': math.copysign,
    'fabs': math.fabs,
    'remainder': math.remainder,
    'fmod': math.fmod,

    # Custom built funtion
    'random': random_float
}

# Export symbols
__all__ = [
    'MATH_FUNCTIONS',
    'random_float',
    'has_math_expression',
    'substitute_variables',
    'evaluate_math_expression',
    'evaluate_condition'
]