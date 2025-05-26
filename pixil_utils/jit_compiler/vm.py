"""
Virtual machine for executing Pixil JIT bytecode.
"""
import math
from typing import Dict, Any, List
from .bytecode import OpCode, CompiledExpression

class PixilVMError(Exception):
    """VM execution errors."""
    pass

class PixilVM:
    """Stack-based virtual machine for executing compiled expressions."""
    
    def __init__(self):
        self.stack: List[float] = []
        
    def execute(self, compiled_expr: CompiledExpression, variables: Dict[str, Any]) -> float:
        """
        Execute compiled bytecode with given variables.
        
        Args:
            compiled_expr: Compiled expression to execute
            variables: Current variable values
            
        Returns:
            Result of expression evaluation
            
        Raises:
            PixilVMError: If execution fails
        """
        self.stack.clear()
        compiled_expr.execution_count += 1
        
        try:
            for instruction in compiled_expr.bytecode:
                self._execute_instruction(instruction, variables)
                
            if len(self.stack) != 1:
                raise PixilVMError(f"Stack should have exactly 1 value, has {len(self.stack)}")
                
            return self.stack[0]
            
        except Exception as e:
            raise PixilVMError(f"VM execution failed: {str(e)}")
    
    def _execute_instruction(self, instruction, variables):
        """Execute a single bytecode instruction."""
        opcode, operand = instruction.opcode, instruction.operand
        
        if opcode == OpCode.LOAD_VAR:
            if operand not in variables:
                raise PixilVMError(f"Variable '{operand}' not found")
            self.stack.append(float(variables[operand]))
            
        elif opcode == OpCode.LOAD_CONST:
            self.stack.append(float(operand))
            
        elif opcode == OpCode.ADD:
            if len(self.stack) < 2:
                raise PixilVMError("ADD requires 2 stack values")
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a + b)
            
        elif opcode == OpCode.SUB:
            if len(self.stack) < 2:
                raise PixilVMError("SUB requires 2 stack values")
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a - b)
            
        elif opcode == OpCode.MUL:
            if len(self.stack) < 2:
                raise PixilVMError("MUL requires 2 stack values")
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a * b)
            
        elif opcode == OpCode.DIV:
            if len(self.stack) < 2:
                raise PixilVMError("DIV requires 2 stack values")
            b, a = self.stack.pop(), self.stack.pop()
            if b == 0:
                raise PixilVMError("Division by zero")
            self.stack.append(a / b)
            
        elif opcode == OpCode.MOD:
            if len(self.stack) < 2:
                raise PixilVMError("MOD requires 2 stack values")
            b, a = self.stack.pop(), self.stack.pop()
            if b == 0:
                raise PixilVMError("Modulo by zero")
            self.stack.append(a % b)
            
        # Math functions (Phase 2 - for now just basic structure)
        elif opcode == OpCode.CALL_COS:
            if len(self.stack) < 1:
                raise PixilVMError("COS requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(math.cos(a))
            
        else:
            raise PixilVMError(f"Unknown opcode: {opcode}")