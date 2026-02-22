#!/usr/bin/env python3
"""
Test script for rgb_matrix_lib multi-layer background and (0,0,1) transparency.

Run directly on the Raspberry Pi:
    sudo python3 test_background_layers.py

Interactive: Press ENTER to advance between tests and substeps.

Tests:
     1. Transparent sentinel — black (0,0,0) is a real drawable color over backgrounds
     2. 4-layer compositing — each layer's transparent areas let lower layers bleed through
     3. Layer peeling — toggle each of the 4 layers off/on to verify isolation
     4. Parallax scrolling with 3 layers at different speeds
     5. begin_frame(false) / begin_frame(true) / end_frame with backgrounds
     6. Immediate mode drawing over backgrounds
     7. dispose_all_sprites destroys all layer state
     8. Sprite rendering over multi-layer backgrounds
     9. Replacing a sprite on an existing layer
    10. clear() hides all layers, preserves state for reactivation
    11. Performance — 3 pattern layers scrolling smoothly in all directions
"""

import sys
import time
import random
import math

# Adjust to your project root
sys.path.insert(0, '/home/pi/led_matrix')

from rgb_matrix_lib.api import RGB_Api
from rgb_matrix_lib.utils import TRANSPARENT_COLOR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait(msg=None):
    """Block until the user presses Enter."""
    prompt = msg or "Press ENTER to continue..."
    input(f"  >> {prompt}")


def header(test_num, title):
    print(f"\n{'='*60}")
    print(f"  TEST {test_num}: {title}")
    print(f"{'='*60}")


def define_sprite(api, name, width, height):
    """Convenience: begin definition, return the drawing target."""
    api.sprite_manager.begin_sprite_definition(name, width, height)
    return api.sprite_manager.get_drawing_target()


def end_sprite(api):
    api.sprite_manager.end_sprite_definition()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_1_black_is_drawable(api):
    """
    Black (0,0,0) drawn in the drawing buffer must appear as true black
    over a coloured background — NOT be treated as transparent.
    """
    header(1, "Black is a drawable color (not transparent)")

    sprite = define_sprite(api, 'red_bg', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'red', 100, True)
    end_sprite(api)

    api.set_background('red_bg')

    # Black rectangle over red — should show BLACK, not red bleed-through
    api.draw_rectangle(20, 20, 24, 24, 'black', 100, True)
    api.draw_rectangle(19, 19, 26, 26, 'white', 100, False)

    print("  EXPECTED: Red background with a BLACK rectangle (white border) in center.")
    print("  FAIL if: The center is RED (means black is still transparent).")
    wait("Verify, then press ENTER to continue...")
    api.clear()


def test_2_four_layer_compositing(api):
    """
    Four background layers stacked, each with transparent gaps so every
    layer beneath bleeds through in different regions.

    Layer 0 — navy starfield (full coverage)
    Layer 1 — large purple diamond in center (rest transparent)
    Layer 2 — two green circles, upper-left and lower-right (rest transparent)
    Layer 3 — small orange square dead-center (rest transparent)

    Result: navy stars everywhere not covered, purple diamond visible around
    the orange square, green circles overlap the diamond and stars, orange
    square sits on top of everything.
    """
    header(2, "4-layer compositing with transparency bleed-through")

    # --- Layer 0: navy field + white star dots ---
    sprite = define_sprite(api, 'l0_stars', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'navy', 100, True)
    random.seed(42)
    for _ in range(60):
        sx, sy = random.randint(0, 63), random.randint(0, 63)
        brightness = random.choice([60, 80, 100])
        sprite.plot(sx, sy, 'white', brightness)
    end_sprite(api)

    # --- Layer 1: purple diamond (polygon, 4 sides, 45deg rotation) ---
    sprite = define_sprite(api, 'l1_diamond', 64, 64)
    sprite.draw_polygon(32, 32, 22, 4, 'purple', 80, 45, True)
    end_sprite(api)

    # --- Layer 2: two green circles in opposite corners ---
    sprite = define_sprite(api, 'l2_circles', 64, 64)
    sprite.draw_circle(14, 14, 12, 'green', 80, True)
    sprite.draw_circle(50, 50, 12, 'green', 80, True)
    end_sprite(api)

    # --- Layer 3: small orange square dead-center ---
    sprite = define_sprite(api, 'l3_square', 64, 64)
    sprite.draw_rectangle(26, 26, 12, 12, 'orange', 100, True)
    end_sprite(api)

    api.set_background('l0_stars',   0, 0)
    api.set_background('l1_diamond', 0, 1)
    api.set_background('l2_circles', 0, 2)
    api.set_background('l3_square',  0, 3)

    print("  EXPECTED (bottom -> top):")
    print("    Layer 0: Navy starfield — visible in all uncovered areas")
    print("    Layer 1: Purple diamond center — visible around orange square")
    print("    Layer 2: Green circles top-left & bottom-right — overlap diamond + stars")
    print("    Layer 3: Orange square dead-center — on top of everything")
    print()
    print("  Verify that each lower layer bleeds through the transparent")
    print("  areas of every layer above it.")
    wait("Verify, then press ENTER to continue...")
    api.clear()


def test_3_layer_peeling(api):
    """
    Re-use the 4-layer scene from test 2 and toggle layers off one at a
    time from top to bottom, then back on.
    """
    header(3, "Layer peeling — toggle layers off/on individually")

    # Re-create same sprites
    sprite = define_sprite(api, 'p_stars', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'navy', 100, True)
    random.seed(42)
    for _ in range(60):
        sx, sy = random.randint(0, 63), random.randint(0, 63)
        sprite.plot(sx, sy, 'white', random.choice([60, 80, 100]))
    end_sprite(api)

    sprite = define_sprite(api, 'p_diamond', 64, 64)
    sprite.draw_polygon(32, 32, 22, 4, 'purple', 80, 45, True)
    end_sprite(api)

    sprite = define_sprite(api, 'p_circles', 64, 64)
    sprite.draw_circle(14, 14, 12, 'green', 80, True)
    sprite.draw_circle(50, 50, 12, 'green', 80, True)
    end_sprite(api)

    sprite = define_sprite(api, 'p_square', 64, 64)
    sprite.draw_rectangle(26, 26, 12, 12, 'orange', 100, True)
    end_sprite(api)

    api.set_background('p_stars',   0, 0)
    api.set_background('p_diamond', 0, 1)
    api.set_background('p_circles', 0, 2)
    api.set_background('p_square',  0, 3)

    print("  All 4 layers visible.")
    wait("Press ENTER to hide layer 3 (orange square)...")
    api.hide_background(3)

    print("  Layer 3 hidden — orange square gone, purple/green/stars remain.")
    wait("Press ENTER to hide layer 2 (green circles)...")
    api.hide_background(2)

    print("  Layers 2+3 hidden — only purple diamond on navy stars.")
    wait("Press ENTER to hide layer 1 (purple diamond)...")
    api.hide_background(1)

    print("  Layers 1+2+3 hidden — only navy starfield (layer 0).")
    wait("Press ENTER to hide layer 0 (starfield)...")
    api.hide_background(0)

    print("  All layers hidden — display should be BLACK.")
    wait("Press ENTER to restore layers bottom-up...")

    api.set_background('p_stars', 0, 0)
    print("  Layer 0 restored (stars).")
    wait()

    api.set_background('p_diamond', 0, 1)
    print("  Layer 1 restored (diamond over stars).")
    wait()

    api.set_background('p_circles', 0, 2)
    print("  Layer 2 restored (circles over diamond + stars).")
    wait()

    api.set_background('p_square', 0, 3)
    print("  Layer 3 restored (orange square). Full scene back.")
    wait("Verify full scene restored, then press ENTER...")
    api.clear()


def test_4_parallax_scrolling(api):
    """
    Three layers scrolling at different speeds for a parallax depth effect.
    Layer 0 (far):   slow stripe background
    Layer 1 (mid):   medium-speed diamond pattern
    Layer 2 (near):  fast sparse dots
    """
    header(4, "Parallax scrolling — 3 layers, 3 speeds")

    # Layer 0: wide horizontal stripes (128px wide for smooth scroll)
    sprite = define_sprite(api, 'par_stripes', 128, 64)
    for y in range(64):
        color = 'navy' if (y // 8) % 2 == 0 else 'dark_gray'
        sprite.draw_line(0, y, 127, y, color, 100)
    end_sprite(api)

    # Layer 1: diamond grid (every 16px, small diamonds)
    sprite = define_sprite(api, 'par_diamonds', 64, 64)
    for cx in range(8, 64, 16):
        for cy in range(8, 64, 16):
            sprite.draw_polygon(cx, cy, 4, 4, 'purple', 60, 45, True)
    end_sprite(api)

    # Layer 2: sparse bright dots
    sprite = define_sprite(api, 'par_dots', 64, 64)
    random.seed(99)
    for _ in range(20):
        dx, dy = random.randint(0, 63), random.randint(0, 63)
        sprite.draw_circle(dx, dy, 1, 'orange', 100, True)
    end_sprite(api)

    api.set_background('par_stripes',  0, 0)
    api.set_background('par_diamonds', 0, 1)
    api.set_background('par_dots',     0, 2)

    print("  Scrolling for ~3 seconds...")
    print("    Layer 0 (stripes)  — 1 px/frame  (far / slow)")
    print("    Layer 1 (diamonds) — 2 px/frame  (mid)")
    print("    Layer 2 (dots)     — 4 px/frame  (near / fast)")

    for _ in range(90):
        api.begin_frame(True)
        api.nudge_background(1, 0, 0, 0)
        api.nudge_background(2, 0, 0, 1)
        api.nudge_background(4, 0, 0, 2)
        api.end_frame()
        time.sleep(0.033)

    print("  Parallax scroll complete.")
    wait()
    api.clear()


def test_5_frame_modes(api):
    """
    Test begin_frame(false) and begin_frame(true) with active backgrounds.
    """
    header(5, "Frame modes with background")

    sprite = define_sprite(api, 'fm_bg', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'blue', 50, True)
    end_sprite(api)
    api.set_background('fm_bg')

    # Part A
    api.begin_frame(False)
    api.draw_circle(32, 32, 15, 'yellow', 100, True)
    api.end_frame()
    print("  Part A: begin_frame(false) — blue bg + yellow circle only.")
    wait()

    # Part B
    api.begin_frame(True)
    api.draw_circle(16, 16, 8, 'red', 100, True)
    api.end_frame()
    print("  Part B: begin_frame(true) — yellow preserved + red circle added.")
    wait()

    # Part C
    api.begin_frame(False)
    api.draw_rectangle(50, 50, 10, 10, 'white', 100, True)
    api.end_frame()
    print("  Part C: begin_frame(false) — only white rect remains; circles gone.")
    wait()
    api.clear()


def test_6_immediate_mode(api):
    """
    Drawing commands outside frame mode render immediately over background.
    """
    header(6, "Immediate mode drawing over background")

    sprite = define_sprite(api, 'im_bg', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'forest_green', 60, True)
    end_sprite(api)
    api.set_background('im_bg')

    api.draw_line(0, 0, 63, 63, 'white', 100)
    api.draw_line(63, 0, 0, 63, 'white', 100)
    api.draw_circle(32, 32, 10, 'red', 100, True)
    api.draw_rectangle(28, 2, 8, 8, 'black', 100, True)

    print("  EXPECTED: Green bg, white X, red circle, BLACK square (top center).")
    print("  The black square must be BLACK — not green.")
    wait()
    api.clear()


def test_7_dispose_all(api):
    """
    dispose_all_sprites should destroy all layer state and clear display.
    """
    header(7, "dispose_all_sprites clears background layers")

    sprite = define_sprite(api, 'disp_bg', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'purple', 80, True)
    end_sprite(api)

    api.set_background('disp_bg', 0, 0)
    print("  Background set — display should be purple.")
    wait("Press ENTER to call dispose_all_sprites...")

    api.dispose_all_sprites()
    has_bg = api.background_manager.has_background()
    layer_count = len(api.background_manager._layers)
    print(f"  After dispose: has_background()={has_bg}, layer_count={layer_count}")
    print(f"  Display should now be BLACK (drawing buffer with no background).")

    ok = (not has_bg) and (layer_count == 0)
    print(f"  {'PASS' if ok else 'FAIL'}: Background state {'destroyed' if ok else 'NOT destroyed'}.")
    wait()
    api.clear()


def test_8_sprites_over_layers(api):
    """
    Sprites render on top of the multi-layer background stack.
    """
    header(8, "Sprites over multi-layer background")

    # Layer 0: sky gradient
    sprite = define_sprite(api, 'sp_sky', 64, 64)
    for y in range(64):
        intensity = max(20, 100 - y)
        sprite.draw_line(0, y, 63, y, 'sky_blue', intensity)
    end_sprite(api)

    # Layer 1: ground bar
    sprite = define_sprite(api, 'sp_ground', 64, 64)
    sprite.draw_rectangle(0, 48, 64, 16, 'forest_green', 80, True)
    end_sprite(api)

    # Layer 2: sun circle top-right
    sprite = define_sprite(api, 'sp_sun', 64, 64)
    sprite.draw_circle(52, 10, 6, 'yellow', 100, True)
    end_sprite(api)

    # Foreground sprite: yellow square "player"
    sprite = define_sprite(api, 'sp_player', 6, 6)
    sprite.draw_rectangle(0, 0, 6, 6, 'yellow', 100, True)
    end_sprite(api)

    api.set_background('sp_sky',    0, 0)
    api.set_background('sp_ground', 0, 1)
    api.set_background('sp_sun',    0, 2)

    print("  Moving yellow sprite across 3-layer background (sky + ground + sun)...")
    api.show_sprite('sp_player', 0, 42, 0, 0)
    for x in range(0, 58):
        api.begin_frame(True)
        api.move_sprite('sp_player', x, 42, 0)
        api.end_frame()
        time.sleep(0.04)

    print("  EXPECTED: Sky gradient + green ground + yellow sun + moving square.")
    wait()
    api.clear()


def test_9_replace_layer(api):
    """
    set_background on an existing layer replaces the sprite, resets offset.
    """
    header(9, "Replace sprite on an existing layer")

    sprite = define_sprite(api, 'rep_a', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'red', 60, True)
    end_sprite(api)

    sprite = define_sprite(api, 'rep_b', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'cyan', 60, True)
    end_sprite(api)

    api.set_background('rep_a', 0, 0)
    print("  Layer 0 = red.")
    wait("Press ENTER to replace with cyan...")

    api.set_background('rep_b', 0, 0)
    print("  Layer 0 replaced with cyan (offset reset to 0,0).")
    wait()
    api.clear()


def test_10_clear_hides_all(api):
    """
    clear() hides all background layers but preserves state for reactivation.
    """
    header(10, "clear() hides all layers, preserves state")

    # Use dispose_all_sprites first to start with a clean slate
    api.dispose_all_sprites()

    sprite = define_sprite(api, 'ch_l0', 64, 64)
    sprite.draw_rectangle(0, 0, 64, 64, 'maroon', 80, True)
    end_sprite(api)

    sprite = define_sprite(api, 'ch_l1', 64, 64)
    sprite.draw_circle(32, 32, 15, 'gold', 100, True)
    end_sprite(api)

    api.set_background('ch_l0', 0, 0)
    api.set_background('ch_l1', 0, 1)
    print("  Both layers active — maroon + gold circle.")
    wait("Press ENTER to call clear()...")

    api.clear()
    has_bg = api.background_manager.has_background()
    layer_count = len(api.background_manager._layers)
    print(f"  After clear(): has_background()={has_bg}, layer_count={layer_count}")
    print(f"  Display should be BLACK.")

    layers_hidden = not has_bg
    layers_preserved = layer_count == 2
    print(f"  Layers hidden: {layers_hidden} (expected True)")
    print(f"  Layer state preserved: {layers_preserved} (expected True, count={layer_count})")
    ok = layers_hidden and layers_preserved
    print(f"  {'PASS' if ok else 'FAIL'}")

    wait("Press ENTER to reactivate both layers...")

    api.set_background('ch_l0', 0, 0)
    api.set_background('ch_l1', 0, 1)
    print("  Both layers reactivated — maroon + gold circle should be back.")
    wait()
    api.clear()


def test_11_performance_scroll(api):
    """
    Performance stress test: 3 dense pattern-based layers scrolling
    smoothly in different directions with sine-wave motion.

    Layer 0 (128x128): Diagonal crosshatch grid — scrolls right + down (slow)
    Layer 1 (96x96):   Concentric ring pattern — scrolls left with vertical sine wave (medium)
    Layer 2 (64x64):   Dot matrix grid — scrolls up-right with horizontal sine wave (fast)

    Measures and reports frame timing.
    """
    header(11, "Performance — 3 pattern layers, smooth multi-direction scroll")

    # Use dispose_all_sprites to start clean
    api.dispose_all_sprites()

    # --- Layer 0: diagonal crosshatch on dark background (128x128) ---
    print("  Building layer 0: 128x128 crosshatch grid...")
    sprite = define_sprite(api, 'perf_cross', 128, 128)
    # Fill dark background
    sprite.draw_rectangle(0, 0, 128, 128, 'navy', 40, True)
    # Diagonal lines in both directions, every 12 pixels
    for i in range(-128, 256, 12):
        sprite.draw_line(i, 0, i + 128, 128, 'sky_blue', 35)
        sprite.draw_line(i, 128, i + 128, 0, 'sky_blue', 35)
    end_sprite(api)

    # --- Layer 1: concentric rings (96x96) ---
    print("  Building layer 1: 96x96 concentric rings...")
    sprite = define_sprite(api, 'perf_rings', 96, 96)
    for r in range(4, 60, 6):
        color = 'purple' if (r // 6) % 2 == 0 else 'violet'
        intensity = 50 + (r % 30)
        sprite.draw_circle(48, 48, r, color, intensity, False)
    end_sprite(api)

    # --- Layer 2: dot matrix grid (64x64) ---
    print("  Building layer 2: 64x64 dot matrix...")
    sprite = define_sprite(api, 'perf_dotgrid', 64, 64)
    for gx in range(2, 64, 6):
        for gy in range(2, 64, 6):
            sprite.draw_circle(gx, gy, 1, 'orange', 80, True)
    end_sprite(api)

    api.set_background('perf_cross',   0, 0)
    api.set_background('perf_rings',   0, 1)
    api.set_background('perf_dotgrid', 0, 2)

    total_frames = 300
    target_fps = 30
    target_dt = 1.0 / target_fps

    print(f"  Running {total_frames} frames at target {target_fps} FPS...")
    print("    Layer 0 (crosshatch): scroll right+down, 1px/frame")
    print("    Layer 1 (rings):      scroll left + sine-wave vertical")
    print("    Layer 2 (dots):       scroll up-right + sine-wave horizontal")
    print()

    frame_times = []
    start_time = time.time()

    for frame in range(total_frames):
        t0 = time.time()

        # Layer 0: steady diagonal scroll
        dx0 = 1
        dy0 = 1

        # Layer 1: scroll left, vertical sine wave
        dx1 = -2
        dy1 = round(3.0 * math.sin(frame * 0.08))

        # Layer 2: scroll up-right, horizontal sine wave
        dx2 = round(2.0 * math.sin(frame * 0.1)) + 2
        dy2 = -3

        api.begin_frame(True)
        api.nudge_background(dx0, dy0, 0, 0)
        api.nudge_background(dx1, dy1, 0, 1)
        api.nudge_background(dx2, dy2, 0, 2)
        api.end_frame()

        elapsed = time.time() - t0
        frame_times.append(elapsed)

        # Sleep to maintain target frame rate
        sleep_time = target_dt - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    total_elapsed = time.time() - start_time

    # --- Performance report ---
    avg_frame = sum(frame_times) / len(frame_times)
    min_frame = min(frame_times)
    max_frame = max(frame_times)
    actual_fps = total_frames / total_elapsed

    # Count frames that exceeded target
    slow_frames = sum(1 for t in frame_times if t > target_dt)

    print()
    print(f"  Performance Report ({total_frames} frames)")
    print(f"  {'─'*40}")
    print(f"  Total time:     {total_elapsed:.2f}s")
    print(f"  Actual FPS:     {actual_fps:.1f} (target {target_fps})")
    print(f"  Avg frame time: {avg_frame*1000:.1f} ms")
    print(f"  Min frame time: {min_frame*1000:.1f} ms")
    print(f"  Max frame time: {max_frame*1000:.1f} ms")
    print(f"  Slow frames:    {slow_frames}/{total_frames} (>{target_dt*1000:.0f} ms)")

    if actual_fps >= target_fps * 0.9:
        print(f"  PASS: Achieved {actual_fps:.1f} FPS (>= 90% of target)")
    else:
        print(f"  WARN: Only {actual_fps:.1f} FPS — below 90% of target {target_fps}")

    wait()
    api.clear()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  RGB Matrix Lib — Multi-Layer Background Test Suite")
    print("=" * 60)
    print(f"  TRANSPARENT_COLOR = {TRANSPARENT_COLOR}")
    print()
    print("  Each test pauses for you to verify the display.")
    print("  Press ENTER to advance between steps.")
    print()

    api = RGB_Api()

    tests = [
        ("Black is drawable",             test_1_black_is_drawable),
        ("4-layer compositing",           test_2_four_layer_compositing),
        ("Layer peeling (toggle off/on)", test_3_layer_peeling),
        ("Parallax scrolling (3 layers)", test_4_parallax_scrolling),
        ("Frame modes with background",   test_5_frame_modes),
        ("Immediate mode drawing",        test_6_immediate_mode),
        ("dispose_all_sprites cleanup",   test_7_dispose_all),
        ("Sprites over multi-layer bg",   test_8_sprites_over_layers),
        ("Replace layer sprite",          test_9_replace_layer),
        ("clear() hides all layers",      test_10_clear_hides_all),
        ("Performance scroll (3 layers)", test_11_performance_scroll),
    ]

    for i, (name, test_fn) in enumerate(tests, 1):
        try:
            test_fn(api)
            print(f"\n  ✓ Test {i} ({name}) completed.\n")
        except Exception as e:
            print(f"\n  ✗ Test {i} ({name}) FAILED: {e}")
            import traceback
            traceback.print_exc()
            api.clear()

        if i < len(tests):
            wait(f"Press ENTER to start test {i + 1}: {tests[i][0]}...")

    print("\n" + "=" * 60)
    print("  All tests complete!")
    print("=" * 60)

    api.cleanup()


if __name__ == '__main__':
    main()