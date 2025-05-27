"""
Virtual machine for executing Pixil JIT bytecode.
Enhanced with array access and advanced math functions.
"""
import math
from typing import Dict, Any, List
from .bytecode import OpCode, CompiledExpression
from ..array_manager import PixilArray

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
        
        # Variable and constant operations
        if opcode == OpCode.LOAD_VAR:
            if operand not in variables:
                raise PixilVMError(f"Variable '{operand}' not found")
            self.stack.append(float(variables[operand]))
            
        elif opcode == OpCode.LOAD_CONST:
            self.stack.append(float(operand))
            
        # NEW: Array access
        elif opcode == OpCode.LOAD_ARRAY:
            array_name, index_var = operand  # operand is (array_name, index_variable)
            
            if array_name not in variables:
                raise PixilVMError(f"Array '{array_name}' not found")
            if index_var not in variables:
                raise PixilVMError(f"Index variable '{index_var}' not found")
                
            array = variables[array_name]
            index = int(variables[index_var])
            
            # Handle PixilArray or regular arrays
            if isinstance(array, PixilArray):
                if 0 <= index < len(array.data):
                    value = array[index]
                else:
                    raise PixilVMError(f"Array index {index} out of bounds")
            elif isinstance(array, (list, tuple)):
                if 0 <= index < len(array):
                    value = array[index]
                else:
                    raise PixilVMError(f"Array index {index} out of bounds")
            else:
                raise PixilVMError(f"'{array_name}' is not an array")
                
            self.stack.append(float(value))
            
        # Arithmetic operations
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
            
        # Single-argument math functions
        elif opcode == OpCode.CALL_COS:
            if len(self.stack) < 1:
                raise PixilVMError("COS requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(math.cos(a))
            
        elif opcode == OpCode.CALL_SIN:
            if len(self.stack) < 1:
                raise PixilVMError("SIN requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(math.sin(a))
            
        elif opcode == OpCode.CALL_TAN:
            if len(self.stack) < 1:
                raise PixilVMError("TAN requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(math.tan(a))
            
        elif opcode == OpCode.CALL_SQRT:
            if len(self.stack) < 1:
                raise PixilVMError("SQRT requires 1 stack value")
            a = self.stack.pop()
            if a < 0:
                raise PixilVMError("Square root of negative number")
            self.stack.append(math.sqrt(a))
            
        elif opcode == OpCode.CALL_ABS:
            if len(self.stack) < 1:
                raise PixilVMError("ABS requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(abs(a))
            
        elif opcode == OpCode.CALL_ROUND:
            if len(self.stack) < 1:
                raise PixilVMError("ROUND requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(round(a))
            
        elif opcode == OpCode.CALL_FLOOR:
            if len(self.stack) < 1:
                raise PixilVMError("FLOOR requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(math.floor(a))
            
        elif opcode == OpCode.CALL_CEIL:
            if len(self.stack) < 1:
                raise PixilVMError("CEIL requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(math.ceil(a))
            
        # Two-argument math functions
        elif opcode == OpCode.CALL_MIN:
            if len(self.stack) < 2:
                raise PixilVMError("MIN requires 2 stack values")
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(min(a, b))
            
        elif opcode == OpCode.CALL_MAX:
            if len(self.stack) < 2:
                raise PixilVMError("MAX requires 2 stack values")
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(max(a, b))
            
        elif opcode == OpCode.CALL_ATAN2:
            if len(self.stack) < 2:
                raise PixilVMError("ATAN2 requires 2 stack values")
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(math.atan2(a, b))

        elif opcode == OpCode.CALL_ACOS:
            if len(self.stack) < 1:
                raise PixilVMError("ACOS requires 1 stack value")
            a = self.stack.pop()
            if a < -1 or a > 1:
                raise PixilVMError("ACOS domain error: value must be between -1 and 1")
            self.stack.append(math.acos(a))

        elif opcode == OpCode.CALL_ASIN:
            if len(self.stack) < 1:
                raise PixilVMError("ASIN requires 1 stack value")
            a = self.stack.pop()
            if a < -1 or a > 1:
                raise PixilVMError("ASIN domain error: value must be between -1 and 1")
            self.stack.append(math.asin(a))

        elif opcode == OpCode.CALL_ATAN:
            if len(self.stack) < 1:
                raise PixilVMError("ATAN requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(math.atan(a))

        elif opcode == OpCode.CALL_LOG:
            if len(self.stack) < 1:
                raise PixilVMError("LOG requires 1 stack value")
            a = self.stack.pop()
            if a <= 0:
                raise PixilVMError("LOG domain error: value must be positive")
            self.stack.append(math.log(a))

        elif opcode == OpCode.CALL_LOG10:
            if len(self.stack) < 1:
                raise PixilVMError("LOG10 requires 1 stack value")
            a = self.stack.pop()
            if a <= 0:
                raise PixilVMError("LOG10 domain error: value must be positive")
            self.stack.append(math.log10(a))

        elif opcode == OpCode.CALL_EXP:
            if len(self.stack) < 1:
                raise PixilVMError("EXP requires 1 stack value")
            a = self.stack.pop()
            self.stack.append(math.exp(a))
            
        # Runtime functions (non-deterministic)
        elif opcode == OpCode.CALL_RUNTIME:
            func_name = operand
            if func_name == "random":
                # For now, we'll implement this in Step 3 with the compiler
                # that handles parsing the arguments
                raise PixilVMError("CALL_RUNTIME not fully implemented yet")
            else:
                raise PixilVMError(f"Unknown runtime function: {func_name}")
                
        else:
            raise PixilVMError(f"Unknown opcode: {opcode}")