"""
Shared regex patterns for Pixil optimization layers.
Pre-compiled once at module load for maximum performance.

This centralizes all regex patterns to avoid duplicate compilation
across different optimization layers in Pixil and math_functions.
"""
import re

# =============================================================================
# FAST PATH PATTERNS (used in parse_value optimization)
# =============================================================================

# Simple array access: v_array[v_index]
FAST_SIMPLE_ARRAY_PATTERN = re.compile(r'^(v_\w+)\[(v_\w+)\]$')

# Variable + number arithmetic: v_var + 5, v_x + 2.5
FAST_VAR_PLUS_NUM_PATTERN = re.compile(r'^(v_\w+)\s*\+\s*(-?\d*\.?\d+)$')

# Variable * number arithmetic: v_var * 3, v_scale * 1.5  
FAST_VAR_MUL_NUM_PATTERN = re.compile(r'^(v_\w+)\s*\*\s*(-?\d*\.?\d+)$')

# Variable - number arithmetic: v_var - 10, v_pos - 2.3
FAST_VAR_SUB_NUM_PATTERN = re.compile(r'^(v_\w+)\s*-\s*(-?\d*\.?\d+)$')

# Variable / number arithmetic: v_var / 2, v_speed / 3.0
FAST_VAR_DIV_NUM_PATTERN = re.compile(r'^(v_\w+)\s*/\s*(-?\d*\.?\d+)$')

# Variable % number arithmetic: v_index % 64, v_counter % 10
FAST_VAR_MOD_NUM_PATTERN = re.compile(r'^(v_\w+)\s*%\s*(-?\d*\.?\d+)$')

# Variable + variable arithmetic: v_x + v_offset, v_a + v_b
FAST_VAR_ADD_VAR_PATTERN = re.compile(r'^(v_\w+)\s*\+\s*(v_\w+)$')

# Variable * variable arithmetic: v_width * v_scale, v_a * v_b
FAST_VAR_MUL_VAR_PATTERN = re.compile(r'^(v_\w+)\s*\*\s*(v_\w+)$')

# =============================================================================
# MATH FUNCTIONS PATTERNS (used in evaluate_math_expression optimization)
# =============================================================================

# Note: These are the same patterns as Fast Path, but keeping separate
# names for backwards compatibility and clarity of usage

# Simple arithmetic patterns (same as Fast Path but different context)
SIMPLE_ADD_PATTERN = FAST_VAR_PLUS_NUM_PATTERN    # Reuse compiled pattern
SIMPLE_SUB_PATTERN = FAST_VAR_SUB_NUM_PATTERN     # Reuse compiled pattern  
SIMPLE_MUL_PATTERN = FAST_VAR_MUL_NUM_PATTERN     # Reuse compiled pattern
SIMPLE_DIV_PATTERN = FAST_VAR_DIV_NUM_PATTERN     # Reuse compiled pattern
SIMPLE_MOD_PATTERN = FAST_VAR_MOD_NUM_PATTERN     # Reuse compiled pattern

# Array access (same as Fast Path)
SIMPLE_ARRAY_ACCESS_PATTERN = FAST_SIMPLE_ARRAY_PATTERN  # Reuse compiled pattern

# Variable combinations (same as Fast Path)
VAR_ADD_VAR_PATTERN = FAST_VAR_ADD_VAR_PATTERN     # Reuse compiled pattern
VAR_MUL_VAR_PATTERN = FAST_VAR_MUL_VAR_PATTERN     # Reuse compiled pattern

# Number detection pattern
NUMBER_PATTERN = re.compile(r'^-?\d*\.?\d+$')

# =============================================================================
# EXISTING PATTERNS (from original code)
# =============================================================================

# These patterns are used elsewhere and kept for compatibility
ARRAY_CREATE_PATTERN = re.compile(r'create_array\((\w+),\s*(.+?)(?:\s*,\s*(\w+))?\)')
ARRAY_ASSIGN_PATTERN = re.compile(r'(v_\w+)\[(.+?)\]\s*=\s*([^#]+)')
SPRITE_DEF_PATTERN = re.compile(r'define_sprite\((\w+),\s*(.+?),\s*(.+?)\)')
COMMAND_PATTERN = re.compile(r'(\w+)\((.*)\)')
SPRITE_OP_PATTERN = re.compile(r'(show|hide|move|dispose)_sprite\((\w+)(?:,\s*(.+?)(?:,\s*(.+?))?(?:,\s*(.+?))?(?:,\s*(.+?))?(?:,\s*(.+?))?)?\)')
PROCEDURE_DEF_PATTERN = re.compile(r'def (\w+) {')
PROCEDURE_CALL_PATTERN = re.compile(r'call (\w+)')
FRAME_PARAM_PATTERN = re.compile(r'begin_frame\((.*)\)')
FOR_LOOP_PATTERN = re.compile(r'for (v_\w+) in \((.+?), (.+?), (.+?)\)')
WHILE_LOOP_PATTERN = re.compile(r'while (.+?) then')
IF_PATTERN = re.compile(r'if (.+?) then')
RANDOM_PATTERN = re.compile(r'random\s*\(\s*(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)\s*,\s*(\d+)\s*\)')

# =============================================================================
# Other
# =============================================================================

# Math expression detection patterns
MATH_EXPR_PATTERN = re.compile(r'[\+\-\*/\(\)]|v_\w+|\d+\.?\d*')
ARRAY_ACCESS_PATTERN = re.compile(r'(v_\w+)\[([^[\]]*(?:\[[^[\]]*\][^[\]]*)*)\]')
VARIABLE_PATTERN = re.compile(r'v_\w+')
ARRAY_INDEX_PATTERN = re.compile(r'(v_\w+)\[([^\[\]]+)\]')
CONCAT_ARRAY_PATTERN = re.compile(r'(v_\w+)\[(.+?)\]')

# Multi-plot patterns
MPLOT_PATTERN = re.compile(r'mplot\((.*)\)')
MFLUSH_PATTERN = re.compile(r'mflush\(\s*\)')

# =============================================================================
# PATTERN USAGE SUMMARY
# =============================================================================

"""
Fast Path Patterns (parse_value):
- FAST_SIMPLE_ARRAY_PATTERN
- FAST_VAR_PLUS_NUM_PATTERN  
- FAST_VAR_MUL_NUM_PATTERN
- FAST_VAR_SUB_NUM_PATTERN
- FAST_VAR_DIV_NUM_PATTERN
- FAST_VAR_MOD_NUM_PATTERN
- FAST_VAR_ADD_VAR_PATTERN
- FAST_VAR_MUL_VAR_PATTERN

Math Functions Patterns (evaluate_math_expression):
- All SIMPLE_* patterns (aliases to FAST_* patterns)
- VAR_*_VAR_PATTERN (aliases to FAST_* patterns)
- NUMBER_PATTERN

Legacy Patterns (main Pixil.py parsing):
- All other patterns remain unchanged
"""