#!/usr/bin/env python3
"""Test the enhanced JIT system with complete math function coverage."""

import math
from pixil_utils.jit_compiler import JITExpressionCache
from pixil_utils.array_manager import PixilArray

def test_enhanced_jit():
    """Test enhanced JIT with arrays and all math functions."""
    cache = JITExpressionCache(max_size=100)
    
    # Create test arrays
    px_array = PixilArray(5, 'numeric')
    px_array[0] = 10.0
    px_array[1] = 20.0
    px_array[2] = 30.0
    
    py_array = PixilArray(5, 'numeric')  
    py_array[0] = 5.0
    py_array[1] = 15.0
    py_array[2] = 25.0
    
    variables = {
        "v_i": 1,
        "v_px": px_array,
        "v_py": py_array,
        "v_angle": 1.5,
        "v_small_angle": 0.5,  # For acos/asin (domain -1 to 1)
        "v_radius": 10.0,
        "v_x": 5.0,
        "v_y": 8.0,
        "v_positive": 2.718,  # For log functions
        "v_power": 2.0,       # For exp function
    }
    
    # Test cases - organized by function type
    test_cases = [
        # === Array Access ===
        ("v_px[v_i]", 20.0),
        ("v_py[v_i]", 15.0),
        
        # === Basic Trigonometry ===
        ("cos(v_angle)", 0.0707),     # cos(1.5) ≈ 0.0707
        ("sin(v_angle)", 0.9975),     # sin(1.5) ≈ 0.9975  
        ("tan(v_angle)", 14.1014),    # tan(1.5) ≈ 14.1014
        
        # === Inverse Trigonometry (NEW - previously missing) ===
        ("acos(v_small_angle)", 1.0472), # acos(0.5) ≈ 1.0472 (60°)
        ("asin(v_small_angle)", 0.5236), # asin(0.5) ≈ 0.5236 (30°)
        ("atan(v_angle)", 0.9828),       # atan(1.5) ≈ 0.9828
        
        # === Logarithmic Functions (NEW - previously missing) ===
        ("log(v_positive)", 1.0),        # log(2.718) ≈ 1.0 (natural log of e)
        ("log10(v_radius)", 1.0),        # log10(10) = 1.0
        ("exp(v_power)", 7.3891),        # exp(2) ≈ 7.3891
        
        # === Basic Math ===
        ("sqrt(v_radius)", 3.1623),
        ("abs(v_x - v_y)", 3.0),
        ("round(v_angle)", 2.0),
        
        # === Min/Max ===
        ("min(v_x, v_y)", 5.0),
        ("max(v_x, v_y)", 8.0),
        
        # === Rounding Functions ===
        ("floor(v_angle)", 1.0),         # floor(1.5) = 1
        ("ceil(v_angle)", 2.0),          # ceil(1.5) = 2
        
        # === Two-argument Functions ===
        ("atan2(v_y, v_x)", 1.0122),     # atan2(8, 5) ≈ 1.0122
    ]
    
    print("=== Enhanced JIT Test - Complete Function Coverage ===")
    
    successful_tests = 0
    failed_tests = 0
    unsupported_tests = 0
    
    for expression, expected in test_cases:
        print(f"\nTesting: {expression}")
        
        # First execution (compilation + execution)
        result1 = cache.evaluate(expression, variables)
        
        if result1 is None:
            print(f"  ⚠️  JIT compilation not supported: {expression}")
            print(f"  (Will fall back to eval() in main system)")
            unsupported_tests += 1
            continue
            
        print(f"  First result: {result1:.4f} (expected: {expected:.4f})")
        
        # Second execution (cached execution)
        result2 = cache.evaluate(expression, variables)
        print(f"  Cached result: {result2:.4f}")
        
        # Verify results match and are consistent
        if abs(result1 - expected) < 0.01 and abs(result1 - result2) < 0.0001:
            print("  ✅ Passed")
            successful_tests += 1
        else:
            print(f"  ❌ Failed")
            if abs(result1 - expected) >= 0.01:
                print(f"     Expected {expected:.4f}, got {result1:.4f}")
            if abs(result1 - result2) >= 0.0001:
                print(f"     Inconsistent results: {result1:.4f} vs {result2:.4f}")
            failed_tests += 1
    
    # Test with different variables (cache validation)
    print(f"\n=== Testing with Different Variables (Cache Validation) ===")
    variables["v_i"] = 2          # Change array index
    variables["v_angle"] = 0.0    # Change angle
    variables["v_small_angle"] = 0.8660  # cos(30°) for acos test
    
    validation_tests = [
        ("v_px[v_i]", 30.0),        # px_array[2] = 30.0
        ("cos(v_angle)", 1.0),      # cos(0) = 1.0
        ("acos(v_small_angle)", 0.5236),  # acos(sqrt(3)/2) ≈ 30° ≈ 0.5236
    ]
    
    for expression, expected in validation_tests:
        result = cache.evaluate(expression, variables)
        if result is not None:
            print(f"  {expression} = {result:.4f} (expected: {expected:.4f})")
            if abs(result - expected) < 0.01:
                print("    ✅ Variable change handled correctly")
            else:
                print("    ❌ Variable change not handled correctly")
    
    # Show final statistics
    stats = cache.get_stats()
    print(f"\n=== Enhanced JIT Statistics ===")
    print(f"Cache attempts: {stats.cache_attempts}")
    print(f"Cache hit rate: {stats.hit_rate:.1f}%")
    print(f"Cache size: {cache.cache_size}")
    print(f"Compilation time: {stats.compilation_time:.4f}s")
    print(f"Total time saved: {stats.total_time_saved:.4f}s")
    
    # Summary
    total_tests = successful_tests + failed_tests + unsupported_tests
    print(f"\n=== Test Summary ===")
    print(f"Total tests: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")  
    print(f"⚠️  Unsupported: {unsupported_tests}")
    
    if failed_tests == 0:
        success_rate = (successful_tests / (successful_tests + unsupported_tests)) * 100
        print(f"🎉 JIT Success Rate: {success_rate:.1f}% of supported expressions")
        
        if unsupported_tests == 0:
            print("🚀 Perfect! All expressions supported by JIT!")
        else:
            print(f"📝 {unsupported_tests} expressions need Phase 2 (complex expressions)")
    else:
        print(f"⚠️  {failed_tests} tests failed - check implementations")

def test_domain_errors():
    """Test that JIT handles math domain errors correctly."""
    print(f"\n=== Testing Domain Error Handling ===")
    
    cache = JITExpressionCache(max_size=10)
    
    # Test cases that should fail with domain errors
    error_tests = [
        ("acos(v_invalid)", {"v_invalid": 2.0}),     # acos domain: [-1, 1]
        ("asin(v_invalid)", {"v_invalid": -2.0}),    # asin domain: [-1, 1]  
        ("log(v_invalid)", {"v_invalid": -1.0}),     # log domain: (0, ∞)
        ("log10(v_invalid)", {"v_invalid": 0.0}),    # log10 domain: (0, ∞)
        ("sqrt(v_invalid)", {"v_invalid": -1.0}),    # sqrt domain: [0, ∞)
    ]
    
    for expression, variables in error_tests:
        print(f"Testing domain error: {expression} with {list(variables.values())[0]}")
        try:
            result = cache.evaluate(expression, variables)
            if result is None:
                print("  ⚠️  JIT compilation failed (expected for domain errors)")
            else:
                print(f"  ❌ Expected domain error, got result: {result}")
        except Exception as e:
            print(f"  ✅ Correctly caught domain error: {type(e).__name__}")

if __name__ == "__main__":
    test_enhanced_jit()
    test_domain_errors()
    print("\n🎯 Enhanced JIT testing completed!")