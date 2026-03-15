"""
Condition template system for fast boolean evaluation.
Eliminates expensive string parsing for repetitive condition checks.

Supports:
- Simple conditions: v_x > 5
- Compound conditions: v_x > 5 and v_y < 10
- Parenthesized conditions (Level 2): 
  - (v_x > 5 or v_y < 10) and v_z == 15
  - (v_x > 5 and v_y < 10) or (v_z == 15)
  - Multiple non-nested parentheses groups
- NOT operator:
  - not v_flag
  - not v_x > 5 (same as not (v_x > 5))
  - not (v_x > 5 and v_y < 10)
  - v_x > 5 and not v_flag
"""

import re
from typing import Dict, List, Tuple, Any, Optional, Union
from .debug import debug_print, DEBUG_VERBOSE

# Pre-compiled regex patterns for condition parsing
SIMPLE_CONDITION_PATTERN = re.compile(r'^\s*(v_\w+(?:\[[^\]]+\])?)\s*(>=|<=|==|!=|>|<)\s*(.+)\s*$')
COMPOUND_CONDITION_PATTERN = re.compile(r'\s+(and|or)\s+')
# Pattern to find top-level parenthesized groups (non-nested)
PAREN_GROUP_PATTERN = re.compile(r'\([^()]+\)')
# Pattern to detect 'not' prefix (must be followed by space)
NOT_PREFIX_PATTERN = re.compile(r'^not\s+(.+)$', re.IGNORECASE)

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
        self.template_type = None      # 'simple', 'compound', 'parenthesized', 'negated', 'boolean', 'unsupported'
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
        # New fields for parenthesized conditions
        self.paren_parts = []            # List of (type, data, negated) tuples
        self.paren_operators = []        # Operators between parenthesized parts
        # New fields for NOT operator
        self.is_negated = False          # Whether this condition is negated
        self.inner_template = None       # For negated conditions, the inner condition
        self.boolean_var = None          # For simple boolean variable conditions (e.g., "v_flag")

    def parse(self):
        """Parse condition into template format."""
        if self.is_parsed:
            return
        
        # Check for NOT prefix FIRST
        if self.original.lower().startswith('not '):
            if self._parse_negated_condition():
                self.template_type = 'negated'
                self.is_parsed = True
                return
        
        # Try parenthesized condition parsing (if has parentheses)
        if '(' in self.original and ')' in self.original:
            if self._parse_parenthesized_condition():
                self.template_type = 'parenthesized'
                self.is_parsed = True
                return
            
        # Try compound condition parsing (check for 'not' within compound)
        if self._parse_compound_condition():
            self.template_type = 'compound'
        # Then try simple condition parsing
        elif self._parse_simple_condition():
            self.template_type = 'simple'
            # Pre-parse operands for optimization
            self._preparse_operands()
        # Try as simple boolean variable (e.g., "v_flag")
        elif self._parse_boolean_variable():
            self.template_type = 'boolean'
        else:
            self.template_type = 'unsupported'
            
        self.is_parsed = True
    
    def _parse_negated_condition(self) -> bool:
        """Parse conditions starting with 'not'."""
        match = NOT_PREFIX_PATTERN.match(self.original)
        if not match:
            return False
        
        inner_condition = match.group(1).strip()
        if not inner_condition:
            return False
        
        if debug_print and DEBUG_VERBOSE:
            debug_print(f"Parsing negated condition: not ({inner_condition})", DEBUG_VERBOSE)
        
        # Create inner template for the condition after 'not'
        self.inner_template = ConditionTemplate(inner_condition)
        self.inner_template.parse()
        
        # Check if inner condition was parsed successfully
        if self.inner_template.template_type == 'unsupported':
            return False
        
        self.is_negated = True
        return True
    
    def _parse_boolean_variable(self) -> bool:
        """Parse simple boolean variable like 'v_flag'."""
        # Must start with v_ and contain only word characters
        if re.match(r'^v_\w+$', self.original):
            self.boolean_var = self.original
            if debug_print and DEBUG_VERBOSE:
                debug_print(f"Parsed boolean variable: {self.boolean_var}", DEBUG_VERBOSE)
            return True
        return False
        
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
    
    def _parse_parenthesized_condition(self) -> bool:
        """
        Parse conditions with parentheses (Level 2 - non-nested).
        
        Supports:
        - (v_x > 5 or v_y < 10) and v_z == 15
        - (v_x > 5 and v_y < 10) or (v_z == 15)
        - v_a == 1 and (v_x > 5 or v_y < 10)
        
        Does NOT support nested parentheses like:
        - ((v_x > 5 or v_y < 10) and v_z == 15) or v_a == 1
        """
        condition = self.original
        
        # Check for nested parentheses - not supported in Level 2
        depth = 0
        for char in condition:
            if char == '(':
                depth += 1
                if depth > 1:
                    if debug_print and DEBUG_VERBOSE:
                        debug_print(f"Nested parentheses detected, not supported: {condition}", DEBUG_VERBOSE)
                    return False  # Nested parentheses not supported
            elif char == ')':
                depth -= 1
        
        # Find all parenthesized groups
        paren_groups = PAREN_GROUP_PATTERN.findall(condition)
        if not paren_groups:
            return False  # No valid parentheses found
        
        if debug_print and DEBUG_VERBOSE:
            debug_print(f"Found parenthesized groups: {paren_groups}", DEBUG_VERBOSE)
        
        # Replace each parenthesized group with a placeholder
        temp_condition = condition
        group_map = {}  # placeholder -> group content
        for i, group in enumerate(paren_groups):
            placeholder = f"__PAREN_GROUP_{i}__"
            group_map[placeholder] = group[1:-1]  # Remove outer parentheses
            temp_condition = temp_condition.replace(group, placeholder, 1)
        
        if debug_print and DEBUG_VERBOSE:
            debug_print(f"Condition with placeholders: {temp_condition}", DEBUG_VERBOSE)
            debug_print(f"Group map: {group_map}", DEBUG_VERBOSE)
        
        # Now split the modified condition by 'and' and 'or'
        parts = COMPOUND_CONDITION_PATTERN.split(temp_condition)
        
        if len(parts) < 3:
            # Could be a single parenthesized group - evaluate as compound
            if len(paren_groups) == 1 and temp_condition.strip().startswith('__PAREN_GROUP_'):
                # Single parenthesized expression - parse its contents
                inner_content = group_map[temp_condition.strip()]
                inner_template = ConditionTemplate(inner_content)
                inner_template.parse()
                if inner_template.template_type in ['simple', 'compound']:
                    self.paren_parts = [('group', inner_template)]
                    self.paren_operators = []
                    return True
            return False
        
        # Extract parts and operators
        parsed_parts = []
        operators = []
        
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Even indices are conditions/placeholders
                part = part.strip()
                if not part:
                    continue
                
                # Check for 'not' prefix on this part
                is_part_negated = False
                if part.lower().startswith('not '):
                    is_part_negated = True
                    part = part[4:].strip()  # Remove 'not ' prefix
                    
                if part.startswith('__PAREN_GROUP_'):
                    # This is a parenthesized group
                    inner_content = group_map.get(part)
                    if inner_content is None:
                        return False
                    
                    inner_template = ConditionTemplate(inner_content)
                    inner_template.parse()
                    
                    if inner_template.template_type == 'unsupported':
                        return False
                    
                    # If negated, wrap in a negated template
                    if is_part_negated:
                        negated_template = ConditionTemplate(f"not ({inner_content})")
                        negated_template.is_negated = True
                        negated_template.inner_template = inner_template
                        negated_template.template_type = 'negated'
                        negated_template.is_parsed = True
                        parsed_parts.append(('group', negated_template))
                    else:
                        parsed_parts.append(('group', inner_template))
                    
                    if debug_print and DEBUG_VERBOSE:
                        debug_print(f"Parsed parenthesized group: {inner_content} -> {inner_template.template_type}, negated={is_part_negated}", DEBUG_VERBOSE)
                else:
                    # This is a simple, boolean, or negated condition without parentheses
                    part_template = ConditionTemplate(part)
                    part_template.parse()
                    
                    if part_template.template_type == 'unsupported':
                        return False
                    
                    # If negated, wrap in a negated template
                    if is_part_negated:
                        negated_template = ConditionTemplate(f"not {part}")
                        negated_template.is_negated = True
                        negated_template.inner_template = part_template
                        negated_template.template_type = 'negated'
                        negated_template.is_parsed = True
                        parsed_parts.append(('simple', negated_template))
                    else:
                        parsed_parts.append(('simple', part_template))
                    
                    if debug_print and DEBUG_VERBOSE:
                        debug_print(f"Parsed non-parenthesized part: {part} -> {part_template.template_type}, negated={is_part_negated}", DEBUG_VERBOSE)
            else:  # Odd indices are operators
                operator = part.strip().lower()
                if operator in ['and', 'or']:
                    operators.append(operator)
                else:
                    return False
        
        if len(parsed_parts) >= 2 and len(operators) == len(parsed_parts) - 1:
            self.paren_parts = parsed_parts
            self.paren_operators = operators
            if debug_print and DEBUG_VERBOSE:
                debug_print(f"Successfully parsed parenthesized condition with {len(parsed_parts)} parts", DEBUG_VERBOSE)
            return True
        
        return False
    
    def _parse_compound_condition(self) -> bool:
        """Parse compound conditions with 'and'/'or', including 'not' support."""
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
                    # Create template for this part (handles 'not', simple conditions, boolean vars)
                    temp_template = ConditionTemplate(condition_text)
                    temp_template.parse()
                    
                    # Accept simple, negated, or boolean types for compound parts
                    if temp_template.template_type in ['simple', 'negated', 'boolean']:
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
        if self.left_var is not None and '[' in self.left_var and ']' in self.left_var:
            self.is_array_access = True
            # Parse array components once
            if isinstance(self.left_var, str):
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
        
        # Parenthesized and negated conditions can handle complex expressions
        if self.template_type in ['parenthesized', 'negated']:
            return True
        
        # For non-parenthesized compound conditions, limit complexity
        if self.template_type == 'compound':
            if self.original.count(' and ') >= 2 and self.original.count(' or ') == 0:
                return False  # Triple+ AND without OR - use parentheses for clarity
        
        return self.template_type in ['simple', 'compound', 'boolean']
    
    def evaluate_fast(self, variables) -> bool:
        """Fast evaluation without string parsing."""
        if not self.is_parsed:
            self.parse()
            
        if self.template_type == 'simple':
            return self._evaluate_simple(variables)
        elif self.template_type == 'compound':
            return self._evaluate_compound(variables)
        elif self.template_type == 'parenthesized':
            return self._evaluate_parenthesized(variables)
        elif self.template_type == 'negated':
            return self._evaluate_negated(variables)
        elif self.template_type == 'boolean':
            return self._evaluate_boolean(variables)
        else:
            raise ValueError(f"Cannot fast evaluate condition type: {self.template_type}")
    
    def _evaluate_negated(self, variables) -> bool:
        """Evaluate negated condition."""
        if self.inner_template is None:
            raise ValueError("Negated condition has no inner template")
        
        inner_result = self.inner_template.evaluate_fast(variables)
        result = not inner_result
        
        if debug_print and DEBUG_VERBOSE:
            debug_print(f"Negated evaluation: not {inner_result} = {result}", DEBUG_VERBOSE)
        
        return result
    
    def _evaluate_boolean(self, variables) -> bool:
        """Evaluate simple boolean variable."""
        if self.boolean_var is None:
            raise ValueError("Boolean variable not set")
        
        value = variables.get(self.boolean_var)
        if value is None:
            raise ValueError(f"Variable '{self.boolean_var}' not found")
        
        result = bool(value)
        
        if debug_print and DEBUG_VERBOSE:
            debug_print(f"Boolean evaluation: {self.boolean_var} = {value} -> {result}", DEBUG_VERBOSE)
        
        return result

    def _evaluate_compound(self, variables) -> bool:
        """Evaluate compound conditions with 'and'/'or'."""
        if not self.compound_parts or not self.compound_operators:
            raise ValueError("Compound condition not properly parsed")
        
        # Evaluate first condition using evaluate_fast (handles all types)
        result = self.compound_parts[0].evaluate_fast(variables)
        
        # Sequentially apply operators and next conditions
        for i, operator in enumerate(self.compound_operators):
            # Short-circuit evaluation
            if operator == 'and' and not result:
                return False  # No need to evaluate further
            if operator == 'or' and result:
                return True  # No need to evaluate further
            
            next_result = self.compound_parts[i + 1].evaluate_fast(variables)
            
            if operator == 'and':
                result = result and next_result
            elif operator == 'or':
                result = result or next_result
            else:
                raise ValueError(f"Unsupported compound operator: {operator}")
        
        return result
    
    def _evaluate_parenthesized(self, variables) -> bool:
        """
        Evaluate parenthesized conditions with proper precedence.
        
        Each part in self.paren_parts is a tuple: ('group', template) or ('simple', template)
        Parts are combined using operators in self.paren_operators.
        
        This respects operator precedence: AND binds tighter than OR.
        """
        if not self.paren_parts:
            raise ValueError("Parenthesized condition not properly parsed")
        
        # If only one part (single parenthesized expression), evaluate it directly
        if len(self.paren_parts) == 1:
            part_type, template = self.paren_parts[0]
            return template.evaluate_fast(variables)
        
        # Evaluate with proper precedence: AND > OR
        # First, evaluate all parts
        part_results = []
        for part_type, template in self.paren_parts:
            result = template.evaluate_fast(variables)
            part_results.append(result)
        
        if debug_print and DEBUG_VERBOSE:
            debug_print(f"Parenthesized part results: {part_results}", DEBUG_VERBOSE)
            debug_print(f"Operators: {self.paren_operators}", DEBUG_VERBOSE)
        
        # Apply precedence: process AND first, then OR
        # Group consecutive ANDs together, then combine with ORs
        
        # Build list of (result, next_operator) pairs for easier processing
        # Then evaluate respecting precedence
        
        # Simple approach: split by OR first (lower precedence), then AND within each group
        # Since we already have flat parts + operators, we process left-to-right
        # but AND takes precedence
        
        # Create groups connected by AND
        or_groups = []  # Each element is a list of (result, and_operator) tuples
        current_group = [part_results[0]]
        
        for i, op in enumerate(self.paren_operators):
            if op == 'and':
                # Continue building current AND group
                current_group.append(part_results[i + 1])
            else:  # op == 'or'
                # Save current group and start new one
                or_groups.append(current_group)
                current_group = [part_results[i + 1]]
        
        # Don't forget the last group
        or_groups.append(current_group)
        
        if debug_print and DEBUG_VERBOSE:
            debug_print(f"OR groups for AND evaluation: {or_groups}", DEBUG_VERBOSE)
        
        # Evaluate each AND group (all must be true), then OR the groups (any must be true)
        for and_group in or_groups:
            group_result = all(and_group)  # AND: all must be true
            if group_result:
                return True  # Short-circuit OR: one true group is enough
        
        return False  # No OR group was true
    
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
        if self.right_value_parsed is None:
            raise ValueError("Right value could not be parsed")
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
        if self.operator is None:
            raise ValueError("Operator is None and cannot be used for comparison")
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

def clear_condition_cache():
    """Clear condition template cache."""
    global _CONDITION_TEMPLATES
    _CONDITION_TEMPLATES.clear()

# Export main functions
__all__ = [
    'evaluate_condition_fast',
    'get_condition_template_stats',
    'reset_condition_template_stats',
    'clear_condition_cache' 
]