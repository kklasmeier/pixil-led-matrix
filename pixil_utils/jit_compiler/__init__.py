"""
JIT compiler for Pixil mathematical expressions.
"""
from .vm import PixilVM, PixilVMError
from .bytecode import CompiledExpression, Instruction, OpCode
from .compiler import ExpressionCompiler
from .cache import JITExpressionCache, JITCacheStats

__all__ = [
    'JITExpressionCache',    # Main public interface
    'JITCacheStats',
    'ExpressionCompiler',
    'PixilVM',
    'CompiledExpression', 
    'PixilVMError'
]

__version__ = '0.1.0'