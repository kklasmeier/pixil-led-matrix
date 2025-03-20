# File: _test_utils.py (place in /home/pi/Lightshow/current/)
# Test script to verify rgb_matrix_lib/utils.py changes in isolation

import sys
import os

# Directly import utils.py by adding its directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'rgb_matrix_lib')))
import utils

# Mock debug functionality to avoid dependency on rgb_matrix_lib.debug
def debug(message, level, component):
    print(f"[DEBUG] {message}")

Level = type('Level', (), {'DEBUG': 10, 'WARNING': 30})
Component = type('Component', (), {'SYSTEM': "SYSTEM"})

# Test cases
def test_colors():
    print("Testing named colors:")
    print(f"red (full): {utils.get_color_rgb('red')}")
    print(f"red (50%): {utils.get_color_rgb('red', 50)}")
    print(f"blue (75%): {utils.get_color_rgb('blue', 75)}")
    print(f"unknown (full): {utils.get_color_rgb('invalid')}")  # Should default to white

    print("\nTesting spectral colors:")
    print(f"0 (full): {utils.get_color_rgb(0)}")
    print(f"45 (60%): {utils.get_color_rgb(45, 60)}")
    print(f"99 (full): {utils.get_color_rgb(99)}")
    print(f"150 (clamped): {utils.get_color_rgb(150)}")  # Should clamp to 99
    print(f"-1 (clamped): {utils.get_color_rgb(-1)}")    # Should clamp to 0

    print("\nTesting edge cases:")
    print(f"red (0%): {utils.get_color_rgb('red', 0)}")
    print(f"red (150%): {utils.get_color_rgb('red', 150)}")  # Should clamp to 100

if __name__ == "__main__":
    test_colors()