"""
Expression compiler for Pixil JIT system.
Enhanced with array access and advanced math functions.
"""
import re
import math
from typing import List, Tuple, Union, Optional
from .bytecode import CompiledExpression, Instruction, OpCode

class Token:
    """Token from expression parsing."""
    def __init__(self, type_: str, value: str, position: int = 0):
        self.type = type_
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"

class ExpressionTokenizer:
    """Tokenizes Pixil expressions into parseable tokens."""
    
    # Enhanced token patterns (order matters!)
    TOKEN_PATTERNS = [
        (r'\s+', 'WHITESPACE'),           # Whitespace (skip)
        (r'\d+\.?\d*', 'NUMBER'),         # Numbers: 123, 12.34
        (r'v_\w+', 'VARIABLE'),           # Variables: v_x, v_radius
        (r'[a-zA-Z_]\w*', 'FUNCTION'),    # Functions: cos, sin, sqrt, random
        (r'\+', 'PLUS'),                  # +
        (r'-', 'MINUS'),                  # -
        (r'\*', 'MULTIPLY'),              # *
        (r'/', 'DIVIDE'),                 # /
        (r'%', 'MODULO'),                 # %
        (r'\(', 'LPAREN'),                # (
        (r'\)', 'RPAREN'),                # )
        (r'\[', 'LBRACKET'),              # [
        (r'\]', 'RBRACKET'),              # ]
        (r',', 'COMMA'),                  # , (for function arguments)
    ]
    
    def __init__(self):
        self.compiled_patterns = [(re.compile(pattern), token_type) 
                                 for pattern, token_type in self.TOKEN_PATTERNS]
    
    def tokenize(self, expression: str) -> List[Token]:
        """Convert expression string into tokens."""
        tokens = []
        position = 0
        
        while position < len(expression):
            matched = False
            
            for pattern, token_type in self.compiled_patterns:
                match = pattern.match(expression, position)
                if match:
                    value = match.group(0)
                    
                    # Skip whitespace tokens
                    if token_type != 'WHITESPACE':
                        tokens.append(Token(token_type, value, position))
                    
                    position = match.end()
                    matched = True
                    break
            
            if not matched:
                raise ValueError(f"Invalid character '{expression[position]}' at position {position}")
        
        return tokens

class ExpressionCompiler:
    """Compiles tokenized expressions to bytecode using enhanced Shunting Yard algorithm."""
    
    def __init__(self):
        self.tokenizer = ExpressionTokenizer()
        
        # Operator precedence and associativity
        self.operators = {
            'PLUS': (1, 'LEFT'),
            'MINUS': (1, 'LEFT'),
            'MULTIPLY': (2, 'LEFT'),
            'DIVIDE': (2, 'LEFT'),
            'MODULO': (2, 'LEFT'),
        }
        
        # Pure mathematical functions (deterministic - can be cached)
        self.pure_functions = {
            'cos': OpCode.CALL_COS,
            'sin': OpCode.CALL_SIN,
            'tan': OpCode.CALL_TAN,
            'acos': OpCode.CALL_ACOS,
            'asin': OpCode.CALL_ASIN,
            'atan': OpCode.CALL_ATAN,
            'atan2': OpCode.CALL_ATAN2,
            'sqrt': OpCode.CALL_SQRT,
            'abs': OpCode.CALL_ABS,
            'round': OpCode.CALL_ROUND,
            'floor': OpCode.CALL_FLOOR,
            'ceil': OpCode.CALL_CEIL,
            'log': OpCode.CALL_LOG,
            'log10': OpCode.CALL_LOG10,
            'exp': OpCode.CALL_EXP,
            'min': OpCode.CALL_MIN,
            'max': OpCode.CALL_MAX,
        }
        
        # Runtime functions (non-deterministic - execute fresh each time)
        self.runtime_functions = {
            'random': OpCode.CALL_RUNTIME,
            # Future runtime functions can be added here
        }
    
    def compile(self, expression: str) -> CompiledExpression:
        """
        Compile expression string to bytecode.
        
        Args:
            expression: Mathematical expression string
            
        Returns:
            Compiled expression with bytecode
            
        Raises:
            ValueError: If expression cannot be compiled
        """
        try:
            # Handle array access patterns first
            if self._is_simple_array_access(expression):
                return self._compile_array_access(expression)
            
            tokens = self.tokenizer.tokenize(expression)
            postfix_tokens = self._infix_to_postfix(tokens)
            bytecode = self._postfix_to_bytecode(postfix_tokens)
            return CompiledExpression(bytecode, expression)
            
        except Exception as e:
            raise ValueError(f"Cannot compile expression '{expression}': {str(e)}")
    
    def _is_simple_array_access(self, expression: str) -> bool:
        """Check if expression is a simple array access like v_array[v_index]."""
        pattern = re.compile(r'^v_\w+\[v_\w+\]$')
        return bool(pattern.match(expression.strip()))
    
    def _compile_array_access(self, expression: str) -> CompiledExpression:
        """Compile simple array access to bytecode."""
        # Parse v_array[v_index] pattern
        match = re.match(r'^(v_\w+)\[(v_\w+)\]$', expression.strip())
        if not match:
            raise ValueError(f"Invalid array access pattern: {expression}")
        
        array_name = match.group(1)
        index_var = match.group(2)
        
        # Create bytecode for array access
        bytecode = [Instruction(OpCode.LOAD_ARRAY, (array_name, index_var))]
        return CompiledExpression(bytecode, expression)
    
    def _infix_to_postfix(self, tokens: List[Token]) -> List[Token]:
        """Convert infix tokens to postfix using Shunting Yard algorithm."""
        output = []
        operator_stack = []
        
        for token in tokens:
            if token.type in ('NUMBER', 'VARIABLE'):
                output.append(token)
                
            elif token.type == 'FUNCTION':
                operator_stack.append(token)
                
            elif token.type in self.operators:
                precedence, associativity = self.operators[token.type]
                
                while (operator_stack and 
                       operator_stack[-1].type != 'LPAREN' and
                       (operator_stack[-1].type == 'FUNCTION' or
                        (operator_stack[-1].type in self.operators and
                         (self.operators[operator_stack[-1].type][0] > precedence or
                          (self.operators[operator_stack[-1].type][0] == precedence and 
                           associativity == 'LEFT'))))):
                    output.append(operator_stack.pop())
                
                operator_stack.append(token)
                
            elif token.type == 'LPAREN':
                operator_stack.append(token)
                
            elif token.type == 'RPAREN':
                while operator_stack and operator_stack[-1].type != 'LPAREN':
                    output.append(operator_stack.pop())
                
                if not operator_stack:
                    raise ValueError("Mismatched parentheses")
                
                operator_stack.pop()  # Remove LPAREN
                
                # If there's a function on top of stack, pop it
                if operator_stack and operator_stack[-1].type == 'FUNCTION':
                    output.append(operator_stack.pop())
            
            elif token.type == 'COMMA':
                # Handle function argument separator
                while operator_stack and operator_stack[-1].type != 'LPAREN':
                    output.append(operator_stack.pop())
        
        # Pop remaining operators
        while operator_stack:
            if operator_stack[-1].type in ('LPAREN', 'RPAREN'):
                raise ValueError("Mismatched parentheses")
            output.append(operator_stack.pop())
        
        return output
    
    def _postfix_to_bytecode(self, postfix_tokens: List[Token]) -> List[Instruction]:
        """Convert postfix tokens to bytecode instructions."""
        bytecode = []
        
        for token in postfix_tokens:
            if token.type == 'NUMBER':
                bytecode.append(Instruction(OpCode.LOAD_CONST, float(token.value)))
                
            elif token.type == 'VARIABLE':
                bytecode.append(Instruction(OpCode.LOAD_VAR, token.value))
                
            elif token.type == 'PLUS':
                bytecode.append(Instruction(OpCode.ADD))
                
            elif token.type == 'MINUS':
                bytecode.append(Instruction(OpCode.SUB))
                
            elif token.type == 'MULTIPLY':
                bytecode.append(Instruction(OpCode.MUL))
                
            elif token.type == 'DIVIDE':
                bytecode.append(Instruction(OpCode.DIV))
                
            elif token.type == 'MODULO':
                bytecode.append(Instruction(OpCode.MOD))
                
            elif token.type == 'FUNCTION':
                if token.value in self.pure_functions:
                    bytecode.append(Instruction(self.pure_functions[token.value]))
                elif token.value in self.runtime_functions:
                    bytecode.append(Instruction(OpCode.CALL_RUNTIME, token.value))
                else:
                    raise ValueError(f"Unknown function: {token.value}")
                    
            else:
                raise ValueError(f"Cannot convert token to bytecode: {token}")
        
        return bytecode