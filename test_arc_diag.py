#!/usr/bin/env python3
"""
Diagnostic test script for arc burnout issue.
Compares arc burnout with circle burnout to isolate the problem.
"""

import time
import sys

from rgb_matrix_lib.api import RGB_Api
from rgb_matrix_lib.utils import arc_points

def test_arc_points_generation():
    """Test that arc_points is generating points correctly."""
    print("\n=== Diagnostic 1: arc_points() output ===")
    
    # Test basic arc
    points = arc_points(10, 32, 54, 32, 15, filled=False)
    print(f"Unfilled arc (10,32) to (54,32) bulge=15: {len(points)} points")
    if len(points) > 0:
        print(f"  First 5 points: {points[:5]}")
        print(f"  Last 5 points: {points[-5:]}")
    else:
        print("  ERROR: No points generated!")
    
    # Test filled arc
    points_filled = arc_points(10, 32, 54, 32, 15, filled=True)
    print(f"Filled arc (10,32) to (54,32) bulge=15: {len(points_filled)} points")
    if len(points_filled) > 0:
        print(f"  Sample points: {list(points_filled)[:10]}")
    else:
        print("  ERROR: No points generated!")
    
    return len(points) > 0 and len(points_filled) > 0

def test_burnout_comparison(api):
    """Compare circle burnout (known working) with arc burnout."""
    print("\n=== Diagnostic 2: Burnout Comparison ===")
    api.clear()
    
    # Draw a circle with burnout on the left
    print("Drawing CIRCLE with 3000ms burnout at (16, 32)...")
    api.draw_circle(16, 32, 10, "red", intensity=100, fill=True, burnout=3000)
    
    # Draw an arc with burnout on the right
    print("Drawing ARC with 3000ms burnout from (34,22) to (58,42)...")
    api.draw_arc(34, 22, 58, 42, 10, "blue", intensity=100, fill=True, burnout=3000)
    
    print("Both shapes drawn. Waiting 5 seconds to observe burnout...")
    print("  - Red circle (left) should burn out after 3 seconds")
    print("  - Blue arc (right) should burn out after 3 seconds")
    
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    print("Check: Are both shapes gone?")
    time.sleep(2)

def test_burnout_manager_state(api):
    """Inspect burnout manager state after adding an arc."""
    print("\n=== Diagnostic 3: Burnout Manager State ===")
    api.clear()
    
    # Check initial state
    print(f"Initial burnout queue size: {api.burnout_manager.burnout_queue.qsize()}")
    print(f"Initial pixel index size: {len(api.burnout_manager.pixel_index)}")
    
    # Draw arc with burnout
    print("\nDrawing arc with 5000ms burnout...")
    api.draw_arc(10, 32, 54, 32, 15, "green", intensity=100, fill=True, burnout=5000)
    
    # Check state after
    print(f"After arc - burnout queue size: {api.burnout_manager.burnout_queue.qsize()}")
    print(f"After arc - pixel index size: {len(api.burnout_manager.pixel_index)}")
    
    if api.burnout_manager.burnout_queue.qsize() > 0:
        # Peek at the queue
        obj = api.burnout_manager.burnout_queue.queue[0]
        print(f"Queued object removal_time: {obj.removal_time}")
        print(f"Queued object points count: {len(obj.get_points())}")
        print(f"Current time: {time.time()}")
        print(f"Time until burnout: {obj.removal_time - time.time():.2f}s")
    else:
        print("ERROR: Nothing in burnout queue!")
    
    print("\nWaiting 6 seconds for burnout...")
    time.sleep(6)
    
    print(f"After wait - burnout queue size: {api.burnout_manager.burnout_queue.qsize()}")
    print("Arc should be gone now.")
    time.sleep(2)

def test_drawn_points_verification(api):
    """Verify that drawn_points is being populated correctly."""
    print("\n=== Diagnostic 4: Drawn Points Verification ===")
    api.clear()
    
    # Manually trace what draw_arc does
    from rgb_matrix_lib.utils import arc_points
    
    x1, y1, x2, y2, bulge = 10, 32, 54, 32, 15
    
    # Get points from arc_points
    points = arc_points(x1, y1, x2, y2, bulge, filled=True)
    print(f"arc_points returned {len(points)} points")
    
    # Simulate the filtering in draw_arc
    drawn_points = []
    for px, py in points:
        if 0 <= px < api.matrix.width and 0 <= py < api.matrix.height:
            drawn_points.append((px, py))
    
    print(f"After bounds filtering: {len(drawn_points)} points")
    
    if len(drawn_points) == 0:
        print("ERROR: All points filtered out by bounds check!")
        print(f"Matrix dimensions: {api.matrix.width}x{api.matrix.height}")
        print(f"Sample raw points: {list(points)[:10]}")
    else:
        print(f"Sample drawn points: {drawn_points[:10]}")
    
    # Now actually draw and check burnout
    print("\nActually drawing arc with burnout...")
    api.draw_arc(x1, y1, x2, y2, bulge, "yellow", intensity=100, fill=True, burnout=3000)
    
    print(f"Burnout queue size after draw: {api.burnout_manager.burnout_queue.qsize()}")
    
    time.sleep(4)
    print("Arc should be burned out now.")

def run_diagnostics():
    """Run all diagnostic tests."""
    print("=" * 60)
    print("Arc Burnout Diagnostic Tests")
    print("=" * 60)
    
    # Test 1: Pure Python test (no hardware)
    if not test_arc_points_generation():
        print("\nFAILED: arc_points() is not generating points!")
        return
    
    try:
        api = RGB_Api()
        print("\nAPI initialized successfully.")
        
        test_burnout_manager_state(api)
        test_drawn_points_verification(api)
        test_burnout_comparison(api)
        
        print("\n" + "=" * 60)
        print("Diagnostics complete!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            api.cleanup()
        except:
            pass

if __name__ == "__main__":
    run_diagnostics()