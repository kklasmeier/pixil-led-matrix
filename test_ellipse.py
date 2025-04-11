#!/usr/bin/python3

from rgb_matrix_lib import execute_command, cleanup
import time
import argparse

def run_ellipse_tests():
    """Run a series of tests for the draw_ellipse function"""
    print("Starting ellipse tests...")
    
    # Helper function to execute a command with optional delay
    def run_test(name, command, delay=1):
        print(f"Test: {name}")
        print(f"Command: {command}")
        execute_command(command)
        time.sleep(delay)
    
    # Clear the display before starting
    execute_command("clear()")
    time.sleep(0.5)
    
    # Test 1: Basic ellipse (circle)
    run_test(
        "Circle (equal radii)",
        "draw_ellipse(32, 32, 10, 10, red, 100, false, 0)"
    )
    
    # Test 2: Horizontal ellipse
    run_test(
        "Horizontal ellipse",
        "draw_ellipse(32, 32, 15, 8, blue, 100, false, 0)"
    )
    
    # Test 3: Vertical ellipse
    run_test(
        "Vertical ellipse",
        "draw_ellipse(32, 32, 8, 15, green, 100, false, 0)"
    )
    
    # Test 4: Filled ellipse
    run_test(
        "Filled ellipse",
        "draw_ellipse(32, 32, 10, 7, yellow, 100, true, 0)"
    )
    
    # Test 5: Rotated ellipse (45 degrees)
    run_test(
        "Rotated ellipse (45°)",
        "draw_ellipse(32, 32, 15, 7, purple, 100, false, 45)"
    )
    
    # Test 6: Rotated ellipse (90 degrees)
    run_test(
        "Rotated ellipse (90°)", 
        "draw_ellipse(32, 32, 15, 7, cyan, 100, false, 90)"
    )
    
    # Test 7: Small ellipse
    run_test(
        "Small ellipse",
        "draw_ellipse(32, 32, 4, 3, white, 100, false, 0)"
    )
    
    # Test 8: Edge case - horizontal line
    run_test(
        "Horizontal line (y_radius=0)",
        "draw_ellipse(32, 32, 15, 0, red, 100, false, 0)"
    )
    
    # Test 9: Edge case - vertical line
    run_test(
        "Vertical line (x_radius=0)",
        "draw_ellipse(32, 32, 0, 15, green, 100, false, 0)"
    )
    
    # Test 10: Edge case - single point
    run_test(
        "Single point (both radii=0)",
        "draw_ellipse(32, 32, 0, 0, blue, 100, false, 0)"
    )
    
    # Test 11: Off-center ellipse
    run_test(
        "Off-center ellipse",
        "draw_ellipse(16, 48, 10, 7, orange, 100, false, 0)"
    )
    
    # Test 12: Filled rotated ellipse
    run_test(
        "Filled rotated ellipse",
        "draw_ellipse(32, 32, 15, 8, pink, 100, true, 30)"
    )
    
    # Test 13: Burnout test
    print("Test: Burnout test")
    execute_command("clear()")
    time.sleep(0.5)
    execute_command("draw_ellipse(32, 32, 15, 8, red, 100, false, 0, 2000)")
    print("Ellipse should disappear after 2 seconds...")
    time.sleep(3)
    
    # Test 14: Test with sprites
    print("Test: Drawing ellipses on sprites")
    execute_command("clear()")
    time.sleep(0.5)
    execute_command("define_sprite(ellipse_sprite, 20, 20)")
    # Skip the sprite draw test for now
    print("Skipping sprite_draw for ellipse - implement in commands.py/api.py first")
    execute_command("show_sprite(ellipse_sprite, 20, 20)")
    time.sleep(2)
    
    # Test 15: Frame buffering with ellipses
    print("Test: Frame buffering with ellipses")
    execute_command("clear()")
    time.sleep(0.5)
    # Use parentheses for begin_frame
    execute_command("begin_frame()")
    execute_command("draw_ellipse(20, 20, 10, 6, red, 100, false, 0)")
    execute_command("draw_ellipse(40, 40, 10, 6, blue, 100, false, 90)")
    execute_command("end_frame()")
    time.sleep(2)
    
    # Test 16: 3D effect with multiple ellipses
    print("Test: 3D perspective effect with multiple ellipses")
    execute_command("clear()")
    time.sleep(0.5)
    execute_command("draw_ellipse(32, 32, 20, 6, red, 100, false, 0)")
    execute_command("draw_ellipse(32, 32, 16, 5, orange, 100, false, 0)")
    execute_command("draw_ellipse(32, 32, 12, 4, yellow, 100, false, 0)")
    execute_command("draw_ellipse(32, 32, 8, 3, green, 100, false, 0)")
    execute_command("draw_ellipse(32, 32, 4, 2, blue, 100, false, 0)")
    time.sleep(3)
    
    # Test 17: Animated rotation
    print("Test: Animated rotating ellipse")
    execute_command("clear()")
    time.sleep(0.5)
    
    for angle in range(0, 360, 15):
        execute_command("begin_frame()")
        execute_command(f"draw_ellipse(32, 32, 18, 8, cyan, 100, false, {angle})")
        execute_command("end_frame()")
        time.sleep(0.1)
    
    time.sleep(1)
    
    # Test 18: 3D animation
    print("Test: Animated 3D cylinder using ellipses")
    execute_command("clear()")
    time.sleep(0.5)
    
    heights = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
    radius = 15
    minor_axis = 6
    
    for height in heights + list(reversed(heights)):
        execute_command("begin_frame()")
        # Draw vertical cylinder with ellipses
        for h in range(0, height, 5):
            y_pos = 32 - h
            intensity = 100 - (h * 2)
            if intensity < 20:
                intensity = 20
            execute_command(f"draw_ellipse(32, {y_pos}, {radius}, {minor_axis}, blue, {intensity}, false, 0)")
        # Top cap
        execute_command(f"draw_ellipse(32, {32 - height}, {radius}, {minor_axis}, light_blue, 100, true, 0)")
        execute_command("end_frame()")
        time.sleep(0.1)
        
    time.sleep(1)
    
    # Final clear
    execute_command("clear()")
    
    print("Ellipse tests completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test the draw_ellipse function')
    args = parser.parse_args()
    
    try:
        run_ellipse_tests()
    except KeyboardInterrupt:
        print("Tests interrupted by user")
    finally:
        cleanup()
        print("Test script finished")