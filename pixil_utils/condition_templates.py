"""
Condition template system for fast boolean evaluation.
Eliminates expensive string parsing for repetitive condition checks.
"""

import re
from typing import Dict, List, Tuple, Any, Optional, Union
from .debug import debug_print, DEBUG_VERBOSE

# Pre-compiled regex patterns for condition parsing
SIMPLE_CONDITION_PATTERN = re.compile(r'^\s*(v_\w+(?:\[[^\]]+\])?)\s*(>=|<=|==|!=|>|<)\s*(.+)\s*$')
COMPOUND_CONDITION_PATTERN = re.compile(r'\s+(and|or)\s+')

# Operator function lookup table for fast comparisons
OPERATOR_FUNCTIONS = {
    '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b,
    '>': lambda a, b: a > b,
    '<': lambda a, b: a < b,
    '>=': lambda a, b: a >= b,
    '<=': lambda a, b: a <= b,
}

class ConditionTemplate:
    """Pre-parsed condition template for fast evaluation."""
    
    def __init__(self, original_condition: str):
        self.original = original_condition.strip()
        self.template_type = None      # 'simple', 'compound', 'unsupported'
        self.left_var = None           # Variable name (e.g., "v_x")
        self.operator = None           # Comparison operator (e.g., ">=")
        self.right_value = None        # Right side value or variable
        self.is_parsed = False
        self.compound_parts = []       # For compound conditions
        self.compound_operators = []   # ['and', 'or'] for compound conditions
        self.left_var_parsed = None      # Pre-parsed left side info
        self.right_value_parsed = None   # Pre-parsed right value
        self.is_array_access = False     # Pre-determined
        self.array_name = None           # For array access
        self.index_var = None            # For array access

    def parse(self):
        """Parse condition into template format."""
        if self.is_parsed:
            return
            
        # NEW: Try compound condition parsing FIRST
        if self._parse_compound_condition():
            self.template_type = 'compound'
        # THEN try simple condition parsing
        elif self._parse_simple_condition():
            self.template_type = 'simple'
            # Pre-parse operands for optimization
            self._preparse_operands()
        else:
            self.template_type = 'unsupported'
            
        self.is_parsed = True
        
    def _parse_simple_condition(self) -> bool:
        """Parse simple conditions like 'v_x > 5' or 'v_array[v_i] == 0'."""
        match = SIMPLE_CONDITION_PATTERN.match(self.original)
        if match:
            self.left_var = match.group(1).strip()
            self.operator = match.group(2).strip()
            self.right_value = match.group(3).strip()
            
            if debug_print and DEBUG_VERBOSE:
                debug_print(f"Simple condition: {self.left_var} {self.operator} {self.right_value}", DEBUG_VERBOSE)
            return True
        return False
    
    def _parse_compound_condition(self) -> bool:
        """Parse compound conditions with 'and'/'or'."""
        # Split by 'and' and 'or' while preserving the operators
        parts = COMPOUND_CONDITION_PATTERN.split(self.original)
        
        if len(parts) < 3:
            return False  # Not a compound condition
        # Split by 'and' and 'or' while preserving the operators
        parts = COMPOUND_CONDITION_PATTERN.split(self.original)
        
        if len(parts) < 3:
            return False  # Not a compound condition
            
        # Extract conditions and operators
        conditions = []
        operators = []
        
        for i in range(0, len(parts)):
            if i % 2 == 0:  # Even indices are conditions
                condition_text = parts[i].strip()
                if condition_text:
                    # Try to parse each part as a simple condition
                    temp_template = ConditionTemplate(condition_text)
                    if temp_template._parse_simple_condition():
                        conditions.append(temp_template)
                    else:
                        return False  # Can't parse a part
            else:  # Odd indices are operators
                operator = parts[i].strip().lower()
                if operator in ['and', 'or']:
                    operators.append(operator)
                else:
                    return False  # Invalid operator
        
        if len(conditions) >= 2 and len(operators) == len(conditions) - 1:
            self.compound_parts = conditions
            self.compound_operators = operators
            return True
            
        return False

    def _preparse_operands(self):
        """Pre-parse both sides to avoid runtime parsing."""
        # Pre-determine if left side is array access
        if '[' in self.left_var and ']' in self.left_var:
            self.is_array_access = True
            # Parse array components once
            match = re.match(r'(v_\w+)\[(v_\w+)\]', self.left_var)
            if match:
                self.array_name, self.index_var = match.groups()
                if debug_print and DEBUG_VERBOSE:
                    debug_print(f"Pre-parsed array access: {self.array_name}[{self.index_var}]", DEBUG_VERBOSE)
        else:
            self.is_array_access = False
        
        # Pre-parse right side value once
        self.right_value_parsed = self._parse_right_value_once(self.right_value)
        
        if debug_print and DEBUG_VERBOSE:
            debug_print(f"Pre-parsed right value: {self.right_value} → {self.right_value_parsed}", DEBUG_VERBOSE)
        
    def _parse_right_value_once(self, right_expr):
        """Parse right side once during template creation."""
        right_expr = right_expr.strip()
        
        # Try as number first
        try:
            if '.' in right_expr:
                return ('number', float(right_expr))
            else:
                return ('number', int(right_expr))
        except ValueError:
            pass
        
        # Try as variable
        if right_expr.startswith('v_'):
            return ('variable', right_expr)
            
        # Try as quoted string
        if (right_expr.startswith('"') and right_expr.endswith('"')) or \
           (right_expr.startswith("'") and right_expr.endswith("'")):
            return ('string', right_expr[1:-1])
            
        return ('unknown', right_expr)

    def can_fast_evaluate(self) -> bool:
        """Check if this condition can be evaluated using fast path."""
        # Add checks for problematic patterns
        if 'random(' in self.original:
            return False  # Cannot handle function calls
        if self.original.count(' and ') >= 2:
            return False  # Cannot handle triple+ compound conditions reliably
        
        return self.template_type in ['simple', 'compound']
    
    def evaluate_fast(self, variables) -> bool:
        """Fast evaluation without string parsing."""
        if not self.is_parsed:
            self.parse()
            
        if self.template_type == 'simple':
            return self._evaluate_simple(variables)
        elif self.template_type == 'compound':
            return self._evaluate_compound(variables)
        else:
            raise ValueError(f"Cannot fast evaluate condition type: {self.template_type}")
    
    def _evaluate_simple(self, variables) -> bool:
        """Optimized simple evaluation with pre-parsed data."""
        
        # Fast array access path using pre-parsed data
        if self.is_array_access:
            array_obj = variables.get(self.array_name)
            index_val = variables.get(self.index_var)
            left_value = array_obj[int(index_val)]
        else:
            # Simple variable access
            left_value = variables.get(self.left_var)
            if left_value is None:
                raise ValueError(f"Variable '{self.left_var}' not found")
        
        # Fast right side evaluation using pre-parsed data
        value_type, value_data = self.right_value_parsed
        if value_type == 'number':
            right_value = value_data
        elif value_type == 'variable':
            right_value = variables.get(value_data)
            if right_value is None:
                raise ValueError(f"Variable '{value_data}' not found")
        elif value_type == 'string':
            right_value = value_data
        else:
            right_value = value_data
        
        # Fast comparison using lookup table
        return OPERATOR_FUNCTIONS[self.operator](left_value, right_value)
    
    def _evaluate_simple(self, variables) -> bool:
        """Optimized simple evaluation with pre-parsed data."""
        
        # Fast array access path using pre-parsed data
        if self.is_array_access:
            array_obj = variables.get(self.array_name)
            index_val = variables.get(self.index_var)
            left_value = array_obj[int(index_val)]
        else:
            # Simple variable access
            left_value = variables.get(self.left_var)
            if left_value is None:
                raise ValueError(f"Variable '{self.left_var}' not found")
        
        # Fast right side evaluation using pre-parsed data
        value_type, value_data = self.right_value_parsed
        if value_type == 'number':
            right_value = value_data
        elif value_type == 'variable':
            right_value = variables.get(value_data)
            if right_value is None:
                raise ValueError(f"Variable '{value_data}' not found")
        elif value_type == 'string':
            right_value = value_data
        else:
            right_value = value_data
        
        # Fast comparison using lookup table
        return OPERATOR_FUNCTIONS[self.operator](left_value, right_value)
    
    def _evaluate_array_access(self, array_expr: str, variables) -> Any:
        """Evaluate array access like v_array[v_i]."""
        # LEGACY - kept for fallback, should not be called in optimized path
        # # Simple parsing for v_array[v_index] format
        match = re.match(r'(v_\w+)\[(v_\w+)\]', array_expr)
        if match:
            array_name, index_var = match.groups()
            if array_name in variables and index_var in variables:
                array_obj = variables.get(array_name)
                index_val = variables.get(index_var)
                return array_obj[int(index_val)]
        
        raise ValueError(f"Cannot evaluate array access: {array_expr}")
    
    def _evaluate_right_side(self, right_expr: str, variables) -> Any:
        """Evaluate right side of condition (number, variable, etc.)."""
        # LEGACY - kept for fallback, should not be called in optimized path
        right_expr = right_expr.strip()
        
        # Try as number first
        try:
            if '.' in right_expr:
                return float(right_expr)
            else:
                return int(right_expr)
        except ValueError:
            pass
        
        # Try as variable
        if right_expr.startswith('v_') and right_expr in variables:
            return variables.get(right_expr)
        
        # Try as quoted string
        if (right_expr.startswith('"') and right_expr.endswith('"')) or \
           (right_expr.startswith("'") and right_expr.endswith("'")):
            return right_expr[1:-1]
        
        raise ValueError(f"Cannot evaluate right side: {right_expr}")
    
    def _compare_values(self, left: Any, operator: str, right: Any) -> bool:
        """Perform the actual comparison."""
        # LEGACY - kept for fallback, should not be called in optimized path
        try:
            if operator == '==':
                return left == right
            elif operator == '!=':
                return left != right
            elif operator == '>':
                return left > right
            elif operator == '<':
                return left < right
            elif operator == '>=':
                return left >= right
            elif operator == '<=':
                return left <= right
            else:
                raise ValueError(f"Unsupported operator: {operator}")
        except Exception as e:
            raise ValueError(f"Comparison error: {left} {operator} {right} - {str(e)}")

# Global template cache
_CONDITION_TEMPLATES: Dict[str, ConditionTemplate] = {}
_TEMPLATE_HITS = 0
_TEMPLATE_MISSES = 0

def get_or_create_condition_template(condition: str) -> ConditionTemplate:
    """Get existing template or create new one."""
    global _TEMPLATE_HITS, _TEMPLATE_MISSES
    
    if condition in _CONDITION_TEMPLATES:
        _TEMPLATE_HITS += 1
        return _CONDITION_TEMPLATES[condition]
    
    _TEMPLATE_MISSES += 1
    template = ConditionTemplate(condition)
    template.parse()
    _CONDITION_TEMPLATES[condition] = template
    
    return template

def evaluate_condition_fast(condition: str, variables) -> Optional[bool]:
    """Fast condition evaluation entry point."""
    try:
        template = get_or_create_condition_template(condition)
        if template.can_fast_evaluate():
            result = template.evaluate_fast(variables)
            return result
        else:
            return None  # Fall back to slow path
    except Exception as e:
        return None  # Fall back to slow path

def get_condition_template_stats() -> Dict[str, Any]:
    """Get condition template performance statistics."""
    total_attempts = _TEMPLATE_HITS + _TEMPLATE_MISSES
    hit_rate = (_TEMPLATE_HITS / total_attempts * 100) if total_attempts > 0 else 0
    
    return {
        'condition_template_hits': _TEMPLATE_HITS,
        'condition_template_misses': _TEMPLATE_MISSES,
        'condition_cache_size': len(_CONDITION_TEMPLATES),
        'condition_hit_rate': hit_rate
    }

def reset_condition_template_stats():
    """Reset condition template statistics."""
    global _TEMPLATE_HITS, _TEMPLATE_MISSES
    _TEMPLATE_HITS = 0
    _TEMPLATE_MISSES = 0

# Export main functions
__all__ = [
    'evaluate_condition_fast',
    'get_condition_template_stats',
    'reset_condition_template_stats'
]