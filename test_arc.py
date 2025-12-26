#!/usr/bin/env python3
"""
Test script for draw_arc functionality in rgb_matrix_lib.

Tests various arc configurations:
- Positive bulge (port/left curve)
- Negative bulge (starboard/right curve)
- Zero bulge (straight line fallback)
- Filled arcs (chord fill)
- Burnout arcs
- Different sizes and orientations
"""

import time
import sys

# Add the path to rgb_matrix_lib if needed
# sys.path.insert(0, '/path/to/your/project')

from rgb_matrix_lib.api import RGB_Api

def test_basic_arcs(api):
    """Test basic arc drawing with positive and negative bulge."""
    print("\n=== Test 1: Basic Arcs (Positive vs Negative Bulge) ===")
    api.clear()
    
    # Horizontal arc - positive bulge (curves up/port)
    # From (10, 32) to (54, 32), bulge = 15
    print("Drawing horizontal arc with positive bulge (curves up)...")
    api.draw_line(10, 32, 54, 32, "red", intensity=100, burnout=2000)
    api.draw_arc(10, 32, 54, 32, 15, "red", intensity=100, burnout=2000)
    
    # Horizontal arc - negative bulge (curves down/starboard)
    # From (10, 32) to (54, 32), bulge = -15
    print("Drawing horizontal arc with negative bulge (curves down)...")
    api.draw_arc(10, 32, 54, 32, -15, "blue", intensity=100, burnout=2000)
    
    time.sleep(3)

def test_vertical_arcs(api):
    """Test vertical arc orientations."""
    print("\n=== Test 2: Vertical Arcs ===")
    api.clear()
    
    # Vertical arc - positive bulge (curves left/port)
    print("Drawing vertical arc with positive bulge (curves left)...")
    api.draw_arc(32, 10, 32, 54, 15, "green", intensity=100, burnout=2000)
    
    # Vertical arc - negative bulge (curves right/starboard)
    print("Drawing vertical arc with negative bulge (curves right)...")
    api.draw_arc(32, 10, 32, 54, -15, "yellow", intensity=100, burnout=2000)
    
    time.sleep(3)

def test_diagonal_arcs(api):
    """Test diagonal arc orientations."""
    print("\n=== Test 3: Diagonal Arcs ===")
    api.clear()
    
    # Diagonal arc from top-left to bottom-right
    print("Drawing diagonal arc (TL to BR, positive bulge)...")
    api.draw_arc(10, 10, 54, 54, 12, "cyan", intensity=100, burnout=2000)
    
    # Diagonal arc from top-right to bottom-left
    print("Drawing diagonal arc (TR to BL, negative bulge)...")
    api.draw_arc(54, 10, 10, 54, -12, "magenta", intensity=100, burnout=2000)
    
    time.sleep(3)

def test_zero_bulge(api):
    """Test zero bulge (should draw straight line)."""
    print("\n=== Test 4: Zero Bulge (Straight Line) ===")
    api.clear()
    
    print("Drawing arc with zero bulge (should be straight line)...")
    api.draw_arc(10, 10, 54, 54, 0, "white", intensity=100, burnout=2000)
    
    # Compare with actual line
    print("Drawing comparison line in different color...")
    api.draw_line(10, 54, 54, 10, "orange", intensity=50, burnout=2000)
    
    time.sleep(3)

def test_filled_arcs(api):
    """Test filled arc (chord fill)."""
    print("\n=== Test 5: Filled Arcs (Chord Fill) ===")
    api.clear()
    
    # Filled arc - positive bulge
    print("Drawing filled arc with positive bulge...")
    api.draw_arc(5, 32, 30, 32, 12, "red", intensity=100, fill=True, burnout=2000)
    
    # Filled arc - negative bulge
    print("Drawing filled arc with negative bulge...")
    api.draw_arc(34, 32, 59, 32, -12, "blue", intensity=100, fill=True, burnout=2000)
    
    time.sleep(3)

def test_small_arcs(api):
    """Test small arcs with various bulge values."""
    print("\n=== Test 6: Small Arcs ===")
    api.clear()
    
    # Small arc with small bulge
    print("Drawing small arc (10px chord, bulge=3)...")
    api.draw_arc(27, 20, 37, 20, 3, "green", intensity=100, burnout=2000)
    
    # Small arc with larger bulge (more curved)
    print("Drawing small arc (10px chord, bulge=8)...")
    api.draw_arc(27, 40, 37, 40, 8, "yellow", intensity=100, burnout=2000)
    
    # Very small arc
    print("Drawing very small arc (5px chord, bulge=3)...")
    api.draw_arc(29, 55, 34, 55, 3, "cyan", intensity=100, burnout=2000)
    
    time.sleep(3)

def test_large_bulge(api):
    """Test arcs with large bulge values (more than semicircle)."""
    print("\n=== Test 7: Large Bulge Values ===")
    api.clear()
    
    # Arc with bulge equal to half chord length (semicircle-ish)
    print("Drawing arc with large bulge...")
    api.draw_arc(16, 32, 48, 32, 20, "purple", intensity=100, burnout=2000)
    
    # Arc with very large bulge
    print("Drawing arc with very large bulge...")
    api.draw_arc(16, 32, 48, 32, -25, "orange", intensity=100, burnout=2000)
    
    time.sleep(3)

def test_burnout_arcs(api):
    """Test arcs with burnout."""
    print("\n=== Test 8: Burnout Arcs ===")
    api.clear()
    
    print("Drawing arc with 2000ms burnout...")
    api.draw_arc(10, 32, 54, 32, 15, "white", intensity=100, burnout=2000)
    
    print("Waiting for burnout...")
    time.sleep(13)
    
    print("Arc should have burned out.")
    time.sleep(1)

def test_intensity_variations(api):
    """Test arcs with different intensity values."""
    print("\n=== Test 9: Intensity Variations ===")
    api.clear()
    
    # Draw multiple arcs with varying intensity
    intensities = [100, 75, 50, 25]
    y_positions = [12, 26, 40, 54]
    
    for intensity, y in zip(intensities, y_positions):
        print(f"Drawing arc at y={y} with intensity={intensity}%...")
        api.draw_arc(10, y, 54, y, 8, "white", intensity=intensity, burnout=2000)
    
    time.sleep(3)

def test_rainbow_arcs(api):
    """Test multiple colored arcs in a rainbow pattern."""
    print("\n=== Test 10: Rainbow Arcs ===")
    api.clear()
    
    colors = ["red", "orange", "yellow", "green", "cyan", "blue", "purple"]
    bulge_values = [5, 10, 15, 20, 25, 30, 35]
    
    for color, bulge in zip(colors, bulge_values):
        print(f"Drawing {color} arc with bulge={bulge}...")
        api.draw_arc(10, 50, 54, 50, -bulge, color, intensity=100)
    
    time.sleep(3)

def run_all_tests():
    """Run all arc tests."""
    print("=" * 60)
    print("RGB Matrix Library - Arc Drawing Test Suite")
    print("=" * 60)
    
    try:
        api = RGB_Api()
        print("API initialized successfully.")
        
        test_basic_arcs(api)
        test_vertical_arcs(api)
        test_diagonal_arcs(api)
        test_zero_bulge(api)
        test_filled_arcs(api)
        test_small_arcs(api)
        test_large_bulge(api)
        test_burnout_arcs(api)
        test_intensity_variations(api)
        test_rainbow_arcs(api)
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCleaning up...")
        try:
            api.cleanup()
        except:
            pass

def run_single_test(test_name):
    """Run a single test by name."""
    tests = {
        'basic': test_basic_arcs,
        'vertical': test_vertical_arcs,
        'diagonal': test_diagonal_arcs,
        'zero': test_zero_bulge,
        'filled': test_filled_arcs,
        'small': test_small_arcs,
        'large': test_large_bulge,
        'burnout': test_burnout_arcs,
        'intensity': test_intensity_variations,
        'rainbow': test_rainbow_arcs,
    }
    
    if test_name not in tests:
        print(f"Unknown test: {test_name}")
        print(f"Available tests: {', '.join(tests.keys())}")
        return
    
    try:
        api = RGB_Api()
        print(f"Running test: {test_name}")
        tests[test_name](api)
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            api.cleanup()
        except:
            pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single_test(sys.argv[1])
    else:
        run_all_tests()