"""
Bytecode instruction definitions for Pixil JIT compiler.
Enhanced with array access and advanced math functions.
"""
from enum import Enum
from typing import NamedTuple, Any, List, Union

class OpCode(Enum):
    """Bytecode instruction opcodes."""
    # Stack operations
    LOAD_VAR = "LOAD_VAR"         # Push variable value
    LOAD_CONST = "LOAD_CONST"     # Push constant value
    LOAD_ARRAY = "LOAD_ARRAY"     # Push array[index] value (NEW)
    
    # Arithmetic operations
    ADD = "ADD"                   # Pop b, a; push a+b
    SUB = "SUB"                   # Pop b, a; push a-b
    MUL = "MUL"                   # Pop b, a; push a*b
    DIV = "DIV"                   # Pop b, a; push a/b
    MOD = "MOD"                   # Pop b, a; push a%b
    
    # Pure mathematical functions (deterministic)
    CALL_COS = "CALL_COS"         # Pop a; push cos(a)
    CALL_SIN = "CALL_SIN"         # Pop a; push sin(a)
    CALL_TAN = "CALL_TAN"         # Pop a; push tan(a)
    CALL_ACOS = "CALL_ACOS"       # Pop a; push acos(a)
    CALL_ASIN = "CALL_ASIN"       # Pop a; push asin(a)
    CALL_ATAN = "CALL_ATAN"       # Pop a; push atan(a)
    CALL_ATAN2 = "CALL_ATAN2"     # Pop b, a; push atan2(a, b)
    CALL_SQRT = "CALL_SQRT"       # Pop a; push sqrt(a)
    CALL_ABS = "CALL_ABS"         # Pop a; push abs(a)
    CALL_ROUND = "CALL_ROUND"     # Pop a; push round(a)
    CALL_FLOOR = "CALL_FLOOR"     # Pop a; push floor(a)
    CALL_CEIL = "CALL_CEIL"       # Pop a; push ceil(a)
    CALL_LOG = "CALL_LOG"         # Pop a; push log(a)
    CALL_LOG10 = "CALL_LOG10"     # Pop a; push log10(a)
    CALL_EXP = "CALL_EXP"         # Pop a; push exp(a)
    CALL_MIN = "CALL_MIN"         # Pop b, a; push min(a, b)
    CALL_MAX = "CALL_MAX"         # Pop b, a; push max(a, b)
    
    # Runtime functions (non-deterministic, always execute fresh)
    CALL_RUNTIME = "CALL_RUNTIME" # Pop args; call runtime function; push result

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