#!/usr/bin/env python3
"""
Interactive test script for multi-layer background system.

Drives the rendering engine directly through RGB_Api to test:
  - New parameter order: set_background(sprite_name, layer, cel_index)
  - hide_background() with no args hides ALL layers
  - hide_background(layer) hides specific layer
  - nudge_background(dx, dy, layer, cel_index)
  - set_background_offset(x, y, layer, cel_index)

Controls: Press 1-6 to run demos, q to quit.
"""

import sys
import os
import time
import math
import select
import termios
import tty

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rgb_matrix_lib.api import get_api_instance


# ──────────────────────────────────────────────
# Terminal helpers
# ──────────────────────────────────────────────

def setup_terminal():
    """Put terminal in raw mode for single-keypress reads."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    return old_settings


def restore_terminal(old_settings):
    """Restore terminal to original mode."""
    fd = sys.stdin.fileno()
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def check_key():
    """Non-blocking key check. Returns key char or None."""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None


def wait_for_key():
    """Blocking single key read."""
    return sys.stdin.read(1)


# ──────────────────────────────────────────────
# Sprite builders
# ──────────────────────────────────────────────

def define_stars(api):
    """Layer 0: sparse white star field (64x64)."""
    api.sprite_manager.begin_sprite_definition("bg_stars", 64, 64)
    stars = [
        (5,3,100), (12,8,60), (22,5,80), (35,2,100), (48,7,50), (58,4,90),
        (8,15,70), (20,18,100), (40,12,60), (55,16,80),
        (3,25,90), (15,28,50), (30,22,100), (45,26,70), (60,20,60),
        (10,35,80), (25,38,100), (42,32,50), (57,37,90),
        (7,45,60), (18,48,100), (33,42,70), (50,46,80), (62,44,50),
        (4,55,100), (16,58,60), (28,52,90), (44,56,70), (56,60,80), (38,62,100),
    ]
    for x, y, intensity in stars:
        api.draw_to_sprite("bg_stars", "plot", x, y, "white", intensity)
    api.sprite_manager.end_sprite_definition()


def define_mountains(api):
    """Layer 1: distant mountain range (128x64 for horizontal tiling)."""
    api.sprite_manager.begin_sprite_definition("bg_mountains", 128, 64)
    # Mountain peaks as filled triangles
    api.draw_to_sprite("bg_mountains", "draw_polygon", 20, 50, 18, 3, "navy", 50, 0, True)
    api.draw_to_sprite("bg_mountains", "draw_polygon", 45, 46, 22, 3, "navy", 60, 0, True)
    api.draw_to_sprite("bg_mountains", "draw_polygon", 64, 48, 16, 3, "indigo", 50, 0, True)
    api.draw_to_sprite("bg_mountains", "draw_polygon", 88, 44, 24, 3, "navy", 55, 0, True)
    api.draw_to_sprite("bg_mountains", "draw_polygon", 110, 50, 18, 3, "indigo", 45, 0, True)
    # Ground fill
    api.draw_to_sprite("bg_mountains", "draw_rectangle", 0, 52, 128, 12, "navy", 40, True)
    api.sprite_manager.end_sprite_definition()


def define_clouds(api):
    """Layer 2: scattered cloud shapes (96x64)."""
    api.sprite_manager.begin_sprite_definition("bg_clouds", 96, 64)
    api.draw_to_sprite("bg_clouds", "draw_ellipse", 15, 12, 8, 4, "white", 30, True, 0)
    api.draw_to_sprite("bg_clouds", "draw_ellipse", 22, 10, 6, 3, "white", 25, True, 0)
    api.draw_to_sprite("bg_clouds", "draw_ellipse", 55, 18, 10, 4, "white", 25, True, 0)
    api.draw_to_sprite("bg_clouds", "draw_ellipse", 63, 16, 7, 3, "white", 20, True, 0)
    api.draw_to_sprite("bg_clouds", "draw_ellipse", 80, 8, 9, 3, "white", 30, True, 0)
    api.sprite_manager.end_sprite_definition()


def define_ship(api):
    """Foreground sprite: small arrow/ship (8x5)."""
    api.sprite_manager.begin_sprite_definition("ship", 8, 5)
    api.draw_to_sprite("ship", "plot", 7, 2, "cyan", 100)
    api.draw_to_sprite("ship", "plot", 6, 1, "cyan", 100)
    api.draw_to_sprite("ship", "plot", 6, 2, "cyan", 100)
    api.draw_to_sprite("ship", "plot", 6, 3, "cyan", 100)
    api.draw_to_sprite("ship", "draw_line", 0, 2, 5, 2, "white", 100)
    api.draw_to_sprite("ship", "draw_line", 2, 1, 5, 1, "sky_blue", 80)
    api.draw_to_sprite("ship", "draw_line", 2, 3, 5, 3, "sky_blue", 80)
    api.draw_to_sprite("ship", "plot", 1, 0, "red", 80)
    api.draw_to_sprite("ship", "plot", 1, 4, "red", 80)
    api.sprite_manager.end_sprite_definition()


def define_blinker(api):
    """Multi-cel background sprite for cel animation test (64x64, 3 cels)."""
    api.sprite_manager.begin_sprite_definition("bg_blinker", 64, 64)

    positions = [(10,10), (30,20), (50,30), (20,50), (40,40)]
    colors = [("blue", 100), ("cyan", 100), ("purple", 100)]

    for cel_idx, (color, intensity) in enumerate(colors):
        api.sprite_manager.start_cel(cel_idx)
        for x, y in positions:
            api.draw_to_sprite("bg_blinker", "plot", x, y, color, intensity)

    api.sprite_manager.end_sprite_definition()


def define_ground(api):
    """Ground layer for compositing test (64x64)."""
    api.sprite_manager.begin_sprite_definition("bg_ground", 64, 64)
    api.draw_to_sprite("bg_ground", "draw_rectangle", 0, 50, 64, 14, "forest_green", 60, True)
    api.draw_to_sprite("bg_ground", "draw_rectangle", 0, 54, 64, 10, "forest_green", 80, True)
    for x in [5, 15, 25, 38, 50, 60]:
        api.draw_to_sprite("bg_ground", "plot", x, 49, "green", 70)
    api.sprite_manager.end_sprite_definition()


def define_all_sprites(api):
    """Define every sprite used in the test suite."""
    define_stars(api)
    define_mountains(api)
    define_clouds(api)
    define_ship(api)
    define_blinker(api)
    define_ground(api)
    print("  All sprites defined.")


# ──────────────────────────────────────────────
# Demos
# ──────────────────────────────────────────────

def demo_single_layer(api):
    """Demo 1: Single layer scroll — backward compatibility."""
    print("\n=== Demo 1: Single Layer Scroll ===")
    print("Tests: set_background(name) and nudge_background(dx, dy)")
    print("  No layer arg — everything defaults to layer 0.\n")

    api.clear()
    api.set_background("bg_stars")  # layer=0 default, cel_index=0 default

    for i in range(200):
        api.begin_frame(True)
        api.nudge_background(1, 0)  # layer=0 default
        api.end_frame()
        time.sleep(0.04)
        if check_key():
            break

    api.hide_background()  # no args = hide ALL
    api.clear()
    print("Demo 1 complete.")


def demo_parallax(api):
    """Demo 2: Parallax scrolling with 3 layers at different speeds."""
    print("\n=== Demo 2: Parallax Scrolling (3 layers) ===")
    print("Layer 0=stars(slow), 1=mountains(medium), 2=clouds(fast)")
    print("Tests: set_background(name, layer) and nudge_background(dx, dy, layer)\n")

    api.clear()
    api.set_background("bg_stars", 0)       # layer 0
    api.set_background("bg_mountains", 1)   # layer 1
    api.set_background("bg_clouds", 2)      # layer 2

    api.show_sprite("ship", 10, 28)

    for i in range(300):
        api.begin_frame(True)

        # Stars: slowest (every 3rd frame), hold cel 0
        if i % 3 == 0:
            api.nudge_background(1, 0, 0, 0)   # layer=0, cel_index=0 (hold)

        # Mountains: medium (every 2nd frame), hold cel 0
        if i % 2 == 0:
            api.nudge_background(1, 0, 1, 0)   # layer=1, cel_index=0 (hold)

        # Clouds: fastest (every frame), hold cel 0
        api.nudge_background(1, 0, 2, 0)       # layer=2, cel_index=0 (hold)

        # Bob the ship
        ship_y = 28 + math.sin(i * 0.1) * 3
        api.move_sprite("ship", 10, int(ship_y))

        api.end_frame()
        time.sleep(0.033)
        if check_key():
            break

    api.hide_sprite("ship")
    api.hide_background()  # no args = hide ALL
    api.clear()
    print("Demo 2 complete.")


def demo_toggle_layers(api):
    """Demo 3: Layer visibility toggling."""
    print("\n=== Demo 3: Layer Visibility Toggle ===")
    print("Tests: hide_background(layer), hide_background(), set_background reactivation\n")

    api.clear()
    api.set_background("bg_stars", 0)
    api.set_background("bg_mountains", 1)
    api.set_background("bg_clouds", 2)
    api.refresh_display()

    print("  All 3 layers visible. (1.5s)")
    time.sleep(1.5)

    print("  Hiding layer 2 (clouds)...")
    api.hide_background(2)       # specific layer
    time.sleep(1.5)

    print("  Hiding layer 1 (mountains)...")
    api.hide_background(1)       # specific layer
    time.sleep(1.5)

    print("  Only layer 0 (stars) visible.")
    time.sleep(1.5)

    print("  Restoring layer 1 (mountains)...")
    api.set_background("bg_mountains", 1)
    time.sleep(1.5)

    print("  Restoring layer 2 (clouds)...")
    api.set_background("bg_clouds", 2)
    time.sleep(1.5)

    print("  Hiding ALL layers (bare hide_background)...")
    api.hide_background()        # no args = hide ALL
    time.sleep(1.5)

    print("  Restoring all layers...")
    api.set_background("bg_stars", 0)
    api.set_background("bg_mountains", 1)
    api.set_background("bg_clouds", 2)
    time.sleep(2)

    api.hide_background()
    api.clear()
    print("Demo 3 complete.")


def demo_cel_animation(api):
    """Demo 4: Cel animation on a background layer."""
    print("\n=== Demo 4: Cel Animation on Background Layer ===")
    print("Layer 0=stars(static scroll), Layer 1=blinker(auto-advance cels)")
    print("Tests: nudge_background with/without cel_index for auto-advance\n")

    api.clear()
    api.set_background("bg_stars", 0)
    api.set_background("bg_blinker", 1)

    for i in range(150):
        api.begin_frame(True)

        # Stars: slow scroll, hold cel 0
        if i % 4 == 0:
            api.nudge_background(1, 0, 0, 0)   # layer=0, cel=0 (hold)

        # Blinker: no scroll, auto-advance cel every 10 frames
        if i % 10 == 0:
            api.nudge_background(0, 0, 1)       # layer=1, NO cel_index = auto-advance

        api.end_frame()
        time.sleep(0.05)
        if check_key():
            break

    api.hide_background()
    api.clear()
    print("Demo 4 complete.")


def demo_offset(api):
    """Demo 5: Absolute offset positioning."""
    print("\n=== Demo 5: Absolute Offset Positioning ===")
    print("Tests: set_background_offset(x, y, layer)\n")

    api.clear()
    api.set_background("bg_stars", 0)
    api.set_background("bg_mountains", 1)

    offsets = [(0, 0), (32, 0), (64, 0), (96, 0)]
    for ox, oy in offsets:
        print(f"  Mountains offset ({ox}, {oy})...")
        api.set_background_offset(ox, oy, 1, 0)  # layer=1, hold cel 0
        api.refresh_display()
        time.sleep(1)

    print("  Smooth scrolling back with nudge...")
    for i in range(96):
        api.begin_frame(True)
        api.nudge_background(-1, 0, 1, 0)   # layer=1, hold cel 0
        api.end_frame()
        time.sleep(0.03)
        if check_key():
            break

    api.hide_background()
    api.clear()
    print("Demo 5 complete.")


def demo_drawing_over_bg(api):
    """Demo 6: Drawing buffer compositing over multi-layer backgrounds."""
    print("\n=== Demo 6: Drawing Buffer Over Backgrounds ===")
    print("Tests: compositing order — bg layers -> draw buffer -> sprites\n")

    api.clear()
    api.set_background("bg_stars", 0)
    api.set_background("bg_ground", 1)

    api.show_sprite("ship", 28, 20)

    for i in range(200):
        api.begin_frame(True)

        # Scroll stars slowly, hold cel
        if i % 3 == 0:
            api.nudge_background(1, 0, 0, 0)

        # Pulsing circle on the drawing buffer (between bg and sprites)
        radius = int(5 + math.sin(i * 0.08) * 3)
        intensity = int(50 + math.sin(i * 0.12) * 30)
        api.draw_circle(32, 40, max(1, radius), "red", max(1, intensity), True)

        # Move ship across screen (wrapping)
        ship_x = i % 64
        api.move_sprite("ship", ship_x, 20)

        api.end_frame()
        time.sleep(0.04)
        if check_key():
            break

    api.hide_sprite("ship")
    api.hide_background()
    api.clear()
    print("Demo 6 complete.")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

DEMOS = {
    '1': ("Single layer scroll",              demo_single_layer),
    '2': ("Parallax scrolling (3 layers)",     demo_parallax),
    '3': ("Layer show/hide toggle",            demo_toggle_layers),
    '4': ("Cel animation on layers",           demo_cel_animation),
    '5': ("Absolute offset positioning",       demo_offset),
    '6': ("Drawing buffer over backgrounds",   demo_drawing_over_bg),
}


def print_menu():
    print("\n========================================")
    print(" Multi-Layer Background Test Suite")
    print("========================================")
    for key, (desc, _) in DEMOS.items():
        print(f"  {key} = {desc}")
    print("  q = Quit")
    print("========================================\n")


def main():
    api = get_api_instance()
    old_term = setup_terminal()

    try:
        print("Defining sprites...")
        define_all_sprites(api)
        print_menu()

        while True:
            print("Press 1-6 or q: ", end="", flush=True)
            key = wait_for_key()
            print(key)  # echo

            if key == 'q':
                break

            if key in DEMOS:
                _, demo_fn = DEMOS[key]
                demo_fn(api)
                print_menu()
            else:
                print(f"  Unknown key '{key}'. Try 1-6 or q.")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        restore_terminal(old_term)
        print("Cleaning up...")
        api.clear()
        from rgb_matrix_lib.api import cleanup
        cleanup()
        print("Done.")


if __name__ == "__main__":
    main()