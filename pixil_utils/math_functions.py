"""
Mathematical functions and utilities for Pixil script interpreter.
Provides safe math operations without variable state dependencies.
"""

import math
import random
import re
from typing import Dict, Any, Union
from .debug import (DEBUG_OFF, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE, DEBUG_LEVEL, set_debug_level, debug_print)
from .array_manager import validate_array_access
from collections import OrderedDict

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
    
    # Cache key and tracking remain the same
    cache_key = None
    
    try:
        # Caching logic remains the same
        if isinstance(expr, str) and "random" not in expr:
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
            
        # Parse remaining variables
        parsed_expr = substitute_variables(expr, variables)
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"After substitution: {parsed_expr}", DEBUG_VERBOSE)
        
        # Try evaluating as math expression
        eval_env = {**MATH_FUNCTIONS, '__builtins__': None}
        result = eval(parsed_expr, {"__builtins__": None}, eval_env)
        if DEBUG_LEVEL >= DEBUG_VERBOSE:
            debug_print(f"Evaluation result: {result}", DEBUG_VERBOSE)
        
        # Cache the result if appropriate
        if cache_key is not None:
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
        return int(round(random_val))
    return round(random_val, precision)

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