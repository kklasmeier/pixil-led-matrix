#!/usr/bin/env python3
"""Test the complete JIT system with cache."""

from pixil_utils.jit_compiler import JITExpressionCache

def test_jit_cache():
    """Test JIT cache with repeated evaluations."""
    cache = JITExpressionCache(max_size=100)
    
    # Test expressions
    expressions = [
        "v_x + v_y",
        "v_radius * 2", 
        "v_x * v_x + v_y * v_y",
        "v_angle + 1.5"
    ]
    
    variables = {
        "v_x": 10,
        "v_y": 20, 
        "v_radius": 5,
        "v_angle": 0.5
    }
    
    print("=== JIT Cache Test ===")
    
    # First round - should compile everything
    print("\nFirst evaluation (compilation):")
    for expr in expressions:
        result = cache.evaluate(expr, variables)
        print(f"  {expr} = {result}")
    
    # Second round - should all be cache hits
    print("\nSecond evaluation (cached):")
    for expr in expressions:
        result = cache.evaluate(expr, variables)
        print(f"  {expr} = {result}")
    
    # Show statistics
    stats = cache.get_stats()
    print(f"\n=== Performance Stats ===")
    print(f"Cache attempts: {stats.cache_attempts}")
    print(f"Cache hits: {stats.cache_hits}")
    print(f"Cache misses: {stats.cache_misses}")
    print(f"Hit rate: {stats.hit_rate:.1f}%")
    print(f"Compilation time: {stats.compilation_time:.4f}s")
    print(f"Execution time: {stats.execution_time:.4f}s")
    print(f"Cache size: {cache.cache_size}")
    
    # Test with different variables (should use cached bytecode)
    print(f"\n=== Testing with different variables ===")
    new_variables = {"v_x": 100, "v_y": 200, "v_radius": 50, "v_angle": 1.0}
    
    for expr in expressions:
        result = cache.evaluate(expr, new_variables)
        print(f"  {expr} = {result}")
    
    final_stats = cache.get_stats()
    print(f"\nFinal hit rate: {final_stats.hit_rate:.1f}%")

if __name__ == "__main__":
    test_jit_cache()
    print("\n🎉 JIT cache test completed!")