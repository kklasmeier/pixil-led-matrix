#!/usr/bin/env python3
"""Quick test of the VM with hand-crafted bytecode."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from pixil_utils.jit_compiler.vm import PixilVM
from pixil_utils.jit_compiler.bytecode import CompiledExpression, Instruction, OpCode

def test_basic_arithmetic():
    """Test basic arithmetic: 5 + 3 * 2 = 11"""
    
    # Hand-craft bytecode for: 5 + 3 * 2
    # In postfix: 5 3 2 * +
    bytecode = [
        Instruction(OpCode.LOAD_CONST, 5),
        Instruction(OpCode.LOAD_CONST, 3), 
        Instruction(OpCode.LOAD_CONST, 2),
        Instruction(OpCode.MUL),
        Instruction(OpCode.ADD)
    ]
    
    compiled_expr = CompiledExpression(bytecode, "5 + 3 * 2")
    vm = PixilVM()
    
    result = vm.execute(compiled_expr, {})
    print(f"5 + 3 * 2 = {result}")
    assert result == 11, f"Expected 11, got {result}"

def test_variables():
    """Test variable access: v_x + v_y"""
    
    bytecode = [
        Instruction(OpCode.LOAD_VAR, "v_x"),
        Instruction(OpCode.LOAD_VAR, "v_y"),
        Instruction(OpCode.ADD)
    ]
    
    compiled_expr = CompiledExpression(bytecode, "v_x + v_y")
    vm = PixilVM()
    
    variables = {"v_x": 10, "v_y": 20}
    result = vm.execute(compiled_expr, variables)
    print(f"v_x + v_y = {result} (with v_x=10, v_y=20)")
    assert result == 30, f"Expected 30, got {result}"

if __name__ == "__main__":
    test_basic_arithmetic()
    test_variables()
    print("✅ All VM tests passed!")