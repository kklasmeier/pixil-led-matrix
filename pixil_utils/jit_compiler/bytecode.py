"""
Bytecode instruction definitions for Pixil JIT compiler.
"""
from enum import Enum
from typing import NamedTuple, Any, List, Union

class OpCode(Enum):
    """Bytecode instruction opcodes."""
    # Stack operations
    LOAD_VAR = "LOAD_VAR"         # Push variable value
    LOAD_CONST = "LOAD_CONST"     # Push constant value
    LOAD_ARRAY = "LOAD_ARRAY"     # Push array[index] value
    
    # Arithmetic operations
    ADD = "ADD"                   # Pop b, a; push a+b
    SUB = "SUB"                   # Pop b, a; push a-b
    MUL = "MUL"                   # Pop b, a; push a*b
    DIV = "DIV"                   # Pop b, a; push a/b
    MOD = "MOD"                   # Pop b, a; push a%b
    
    # Mathematical functions (Phase 2)
    CALL_COS = "CALL_COS"         # Pop a; push cos(a)
    CALL_SIN = "CALL_SIN"         # Pop a; push sin(a)
    CALL_SQRT = "CALL_SQRT"       # Pop a; push sqrt(a)
    CALL_ABS = "CALL_ABS"         # Pop a; push abs(a)

class Instruction(NamedTuple):
    """Single bytecode instruction."""
    opcode: OpCode
    operand: Any = None

# Type alias for bytecode
Bytecode = List[Instruction]

class CompiledExpression:
    """Container for compiled expression bytecode."""
    
    def __init__(self, bytecode: Bytecode, original_expr: str = ""):
        self.bytecode = bytecode
        self.original_expr = original_expr
        self.execution_count = 0  # Performance tracking
        
    def __str__(self):
        return f"CompiledExpression({self.original_expr}, {len(self.bytecode)} instructions)"
    