#!/usr/bin/env python3
"""Test the expression compiler."""

from pixil_utils.jit_compiler.compiler import ExpressionCompiler
from pixil_utils.jit_compiler.vm import PixilVM

def test_simple_expressions():
    """Test basic expression compilation and execution."""
    compiler = ExpressionCompiler()
    vm = PixilVM()
    
    test_cases = [
        ("5 + 3", {}, 8.0),
        ("10 - 4", {}, 6.0),
        ("6 * 7", {}, 42.0),
        ("15 / 3", {}, 5.0),
        ("v_x + v_y", {"v_x": 10, "v_y": 20}, 30.0),
        ("v_x * 2 + v_y", {"v_x": 5, "v_y": 7}, 17.0),
        ("v_radius * 1.5", {"v_radius": 10}, 15.0),
    ]
    
    for expression, variables, expected in test_cases:
        print(f"Testing: {expression}")
        
        # Compile expression
        compiled = compiler.compile(expression)
        print(f"  Bytecode: {len(compiled.bytecode)} instructions")
        
        # Execute
        result = vm.execute(compiled, variables)
        print(f"  Result: {result} (expected: {expected})")
        
        assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
        print("  ✅ Passed")
        print()

if __name__ == "__main__":
    test_simple_expressions()
    print("🎉 All compiler tests passed!")