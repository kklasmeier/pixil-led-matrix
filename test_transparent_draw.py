#!/usr/bin/env python3
"""
Test: Drawing with the 'transparent' color to punch holes through the
drawing buffer and reveal the background beneath.

Run on the Raspberry Pi:
    sudo python3 test_transparent_draw.py

Three subtests, each with the same setup:
    - Background: solid blue
    - Draw a large yellow filled rectangle over it
    - Draw a smaller 'transparent' filled rectangle on top of the yellow

Expected: The transparent rectangle should "erase" the yellow in that
region, letting the blue background show through.

Subtests:
    A. Immediate mode (no framing)
    B. begin_frame(false)
    C. begin_frame(true)
"""

import sys
import time

sys.path.insert(0, '/home/pi/led_matrix')

from rgb_matrix_lib.api import RGB_Api
from rgb_matrix_lib.utils import TRANSPARENT_COLOR


def wait(msg=None):
    prompt = msg or "Press ENTER to continue..."
    input(f"  >> {prompt}")


def setup_background(api):
    """Create and activate a solid blue background."""
    api.dispose_all_sprites()

    api.sprite_manager.begin_sprite_definition('blue_bg', 64, 64)
    sprite = api.sprite_manager.get_drawing_target()
    sprite.draw_rectangle(0, 0, 64, 64, 'blue', 100, True)
    api.sprite_manager.end_sprite_definition()

    api.set_background('blue_bg')


def main():
    print("=" * 60)
    print("  Transparent Color Draw-Through Test")
    print("=" * 60)
    print(f"  TRANSPARENT_COLOR = {TRANSPARENT_COLOR}")
    print()

    api = RGB_Api()

    # ------------------------------------------------------------------
    # Subtest A: Immediate mode (no framing)
    # ------------------------------------------------------------------
    print("=" * 60)
    print("  SUBTEST A: Immediate mode (no framing)")
    print("=" * 60)

    setup_background(api)

    # Draw yellow rectangle covering most of the display
    api.draw_rectangle(10, 10, 44, 44, 'yellow', 100, True)

    # Draw white border around where the transparent hole will be
    api.draw_rectangle(21, 21, 22, 22, 'white', 100, False)

    # Now draw a transparent rectangle to punch a hole through the yellow
    api.draw_rectangle(22, 22, 20, 20, (0, 0, 1), 100, True)

    print("  Drew: blue background -> yellow rect -> transparent rect (center)")
    print("  EXPECTED: Blue bg, yellow rect with a BLUE hole in the center")
    print("            (white border marks the hole)")
    print("  FAIL if:  The center is yellow (transparent didn't erase)")
    print("            or black (transparent mapped to black instead of pass-through)")
    wait("Verify, then press ENTER...")
    api.clear()

    # ------------------------------------------------------------------
    # Subtest B: begin_frame(false)
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("  SUBTEST B: begin_frame(false)")
    print("=" * 60)

    setup_background(api)

    api.begin_frame(False)
    # Draw yellow rectangle
    api.draw_rectangle(10, 10, 44, 44, 'yellow', 100, True)
    # White border
    api.draw_rectangle(21, 21, 22, 22, 'white', 100, False)
    # Transparent hole
    api.draw_rectangle(22, 22, 20, 20, (0, 0, 1), 100, True)
    api.end_frame()

    print("  Drew inside begin_frame(false): yellow rect -> transparent rect")
    print("  EXPECTED: Blue bg, yellow rect with a BLUE hole in the center")
    print("            (white border marks the hole)")
    wait("Verify, then press ENTER...")
    api.clear()

    # ------------------------------------------------------------------
    # Subtest C: begin_frame(true)
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("  SUBTEST C: begin_frame(true)")
    print("=" * 60)

    setup_background(api)

    # First frame: draw the yellow rectangle
    api.begin_frame(False)
    api.draw_rectangle(10, 10, 44, 44, 'yellow', 100, True)
    api.end_frame()

    # Second frame with preserve: punch the transparent hole
    api.begin_frame(True)
    # White border
    api.draw_rectangle(21, 21, 22, 22, 'white', 100, False)
    # Transparent hole over the preserved yellow
    api.draw_rectangle(22, 22, 20, 20, (0, 0, 1), 100, True)
    api.end_frame()

    print("  Frame 1: begin_frame(false) drew yellow rect")
    print("  Frame 2: begin_frame(true) drew transparent rect over preserved yellow")
    print("  EXPECTED: Blue bg, yellow rect with a BLUE hole in the center")
    print("            (white border marks the hole)")
    wait("Verify, then press ENTER...")
    api.clear()

    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("  All subtests complete!")
    print("=" * 60)

    api.cleanup()


if __name__ == '__main__':
    main()