#!/usr/bin/env python3
"""
Background Layer Interactive Test Script
==========================================

Interactive test suite for validating the background layer implementation.
Each test runs continuously until you press Enter to move to the next one.

Controls:
    Enter  = Stop current test, show next test description
    Enter  = Start the next test
    Ctrl+C = Exit immediately

Usage:
    sudo python3 test_background.py          # Run all tests interactively
    sudo python3 test_background.py 5        # Start from test 5
"""

import sys
import os
import time
import math
import select
import termios
import tty

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rgb_matrix_lib.api import get_api_instance, cleanup


# ============================================================
# Input Helpers
# ============================================================

def key_pressed():
    """Non-blocking check if a key has been pressed (stdin has data)."""
    return select.select([sys.stdin], [], [], 0)[0]


def wait_for_enter(prompt="Press Enter to continue..."):
    """Block until Enter is pressed."""
    print(f"\n  >>> {prompt}")
    sys.stdin.readline()


def run_until_enter(loop_fn, setup_msg=None):
    """
    Run loop_fn() repeatedly until Enter is pressed.
    loop_fn should do one frame of work and return.
    """
    if setup_msg:
        print(f"  {setup_msg}")
    print("  (Press Enter to stop)")

    # Drain any buffered input
    while key_pressed():
        sys.stdin.readline()

    frame = 0
    start = time.time()
    while True:
        if key_pressed():
            sys.stdin.readline()  # consume the Enter
            break
        loop_fn(frame, time.time() - start)
        frame += 1

    elapsed = time.time() - start
    if elapsed > 0 and frame > 0:
        print(f"  ({frame} frames in {elapsed:.1f}s = {frame/elapsed:.1f} FPS)")


# ============================================================
# Asset Creation
# ============================================================

def create_starfield_background(api, name="starfield", width=128, height=128):
    """Starfield with colored corner markers for visual reference."""
    commands = [
        f'define_sprite({name}, {width}, {height})',
        f'sprite_draw({name}, draw_circle, 16, 16, 10, red, 100, true)',
        f'sprite_draw({name}, draw_circle, {width - 16}, 16, 10, green, 100, true)',
        f'sprite_draw({name}, draw_circle, 16, {height - 16}, 10, blue, 100, true)',
        f'sprite_draw({name}, draw_circle, {width - 16}, {height - 16}, 10, yellow, 100, true)',
        f'sprite_draw({name}, draw_circle, {width // 2}, {height // 2}, 6, magenta, 100, true)',
    ]
    # Grid lines
    for x in range(0, width, 16):
        commands.append(f'sprite_draw({name}, draw_line, {x}, 0, {x}, {height - 1}, white, 15)')
    for y in range(0, height, 16):
        commands.append(f'sprite_draw({name}, draw_line, 0, {y}, {width - 1}, {y}, white, 15)')
    # Stars
    import random
    random.seed(42)
    for _ in range(200):
        sx = random.randint(0, width - 1)
        sy = random.randint(0, height - 1)
        brightness = random.randint(30, 100)
        commands.append(f'sprite_draw({name}, plot, {sx}, {sy}, white, {brightness})')
    commands.append('endsprite')
    for cmd in commands:
        api.execute_command(cmd)


def create_animated_background(api, name="animated_bg", width=64, height=64, num_cels=4):
    """Multi-cel background - each cel has a different color tint + position marker."""
    api.execute_command(f'define_sprite({name}, {width}, {height})')
    colors = ['red', 'green', 'blue', 'yellow']
    for cel in range(num_cels):
        api.execute_command(f'sprite_cel({cel})')
        color = colors[cel % len(colors)]
        api.execute_command(f'sprite_draw({name}, draw_rectangle, 0, 0, {width}, {height}, {color}, 20, true)')
        cx = 10 + cel * 15
        api.execute_command(f'sprite_draw({name}, draw_circle, {cx}, 10, 5, white, 100, true)')
        # Unique bar per cel so you can tell them apart
        api.execute_command(f'sprite_draw({name}, draw_rectangle, 5, 50, {8 + cel * 6}, 8, white, 80, true)')
    api.execute_command('endsprite')


def create_test_sprite(api, name="test_sprite", size=12):
    """Small orange circle sprite."""
    api.execute_command(f'define_sprite({name}, {size}, {size})')
    api.execute_command(f'sprite_draw({name}, draw_circle, {size // 2}, {size // 2}, {size // 2 - 1}, orange, 100, true)')
    api.execute_command('endsprite')


def cleanup_between_tests(api):
    """Full cleanup between tests."""
    api.execute_command('clear')
    try:
        api.execute_command('dispose_all_sprites')
    except:
        pass
    time.sleep(0.3)


# ============================================================
# Test Definitions
# ============================================================

TESTS = []

def test(number, title, what_to_look_for):
    """Decorator to register a test with its description."""
    def decorator(fn):
        TESTS.append({
            'number': number,
            'title': title,
            'look_for': what_to_look_for,
            'fn': fn,
        })
        return fn
    return decorator


@test(1, "Static Background",
      "You should see a starfield pattern with:\n"
      "  - RED circle (top-left)\n"
      "  - GREEN circle (top-right)\n"
      "  - BLUE circle (bottom-left)\n"
      "  - YELLOW circle (bottom-right, partially visible)\n"
      "  - MAGENTA circle (center, partially visible)\n"
      "  - Faint grid lines and scattered white stars")
def test_static_background(api):
    create_starfield_background(api)
    api.execute_command('set_background(starfield)')

    def loop(frame, elapsed):
        time.sleep(0.05)

    run_until_enter(loop, "Displaying static background...")
    assert api.background_manager.has_background(), "Background should be active"


@test(2, "Background Scrolling",
      "The starfield scrolls diagonally (right and down).\n"
      "  - Colored circles drift across and wrap/tile seamlessly\n"
      "  - Grid lines remain straight and continuous")
def test_scrolling(api):
    create_starfield_background(api)
    api.execute_command('set_background(starfield)')

    def loop(frame, elapsed):
        api.execute_command('begin_frame(true)')
        api.execute_command('nudge_background(2, 1, 0)')
        api.execute_command('end_frame')
        time.sleep(0.03)

    run_until_enter(loop, "Scrolling background diagonally...")


@test(3, "Tiling with Small Pattern",
      "A SMALL 32x32 pattern tiles to fill the 64x64 display.\n"
      "  - Pattern repeats 2x2 on screen\n"
      "  - As it scrolls, tiling seams should be seamless")
def test_tiling(api):
    create_starfield_background(api, name="small_bg", width=32, height=32)
    api.execute_command('set_background(small_bg)')

    def loop(frame, elapsed):
        api.execute_command('begin_frame(true)')
        api.execute_command('nudge_background(1, 1, 0)')
        api.execute_command('end_frame')
        time.sleep(0.04)

    run_until_enter(loop, "Scrolling small tiled pattern...")


@test(4, "Cel Animation",
      "Background cycles through 4 animation cels (one every ~0.5 sec):\n"
      "  - Cel 0: RED tint, white dot far left, short white bar\n"
      "  - Cel 1: GREEN tint, white dot second position, medium bar\n"
      "  - Cel 2: BLUE tint, white dot third position, longer bar\n"
      "  - Cel 3: YELLOW tint, white dot right side, longest bar")
def test_cel_animation(api):
    create_animated_background(api, num_cels=4)
    api.execute_command('set_background(animated_bg)')

    def loop(frame, elapsed):
        api.execute_command('begin_frame(true)')
        api.execute_command('nudge_background(0, 0)')  # Auto-advance cel
        api.execute_command('end_frame')
        time.sleep(0.5)

    run_until_enter(loop, "Cycling through animation cels...")


@test(5, "Drawing Buffer Overlay",
      "Background with drawings on top:\n"
      "  - Starfield visible through BLACK areas of drawing buffer\n"
      "  - CYAN filled rectangle (upper-left area)\n"
      "  - MAGENTA filled circle (upper-right area)\n"
      "  - Background scrolls BEHIND the fixed drawings")
def test_drawing_overlay(api):
    create_starfield_background(api)
    api.execute_command('set_background(starfield)')
    api.execute_command('draw_rectangle(10, 10, 20, 20, cyan, 100, true)')
    api.execute_command('draw_circle(50, 14, 6, magenta, 100, true)')

    def loop(frame, elapsed):
        api.execute_command('begin_frame(true)')
        api.execute_command('nudge_background(1, 0, 0)')
        api.execute_command('end_frame')
        time.sleep(0.03)

    run_until_enter(loop, "Scrolling background behind fixed drawings...")


@test(6, "Sprites on Top of Everything",
      "All three layers visible:\n"
      "  - BOTTOM: Scrolling starfield background\n"
      "  - MIDDLE: Fixed CYAN rectangle (drawing buffer)\n"
      "  - TOP: ORANGE circle sprite orbiting the center\n"
      "  - Sprite passes OVER both the rectangle and the background")
def test_sprites_on_top(api):
    create_starfield_background(api)
    create_test_sprite(api)
    api.execute_command('set_background(starfield)')
    api.execute_command('draw_rectangle(20, 20, 24, 24, cyan, 100, true)')
    api.execute_command('show_sprite(test_sprite, 32, 32)')

    def loop(frame, elapsed):
        x = int(32 + 22 * math.cos(elapsed * 2))
        y = int(32 + 22 * math.sin(elapsed * 2))
        api.execute_command('begin_frame(true)')
        api.execute_command('nudge_background(1, 0, 0)')
        api.execute_command(f'move_sprite(test_sprite, {x}, {y})')
        api.execute_command('end_frame')
        time.sleep(0.016)

    run_until_enter(loop, "Full layer stack animation...")


@test(7, "Sprite Movement Restores Background",
      "ORANGE sprite sweeps across the screen slowly.\n"
      "  - Where the sprite WAS, background + cyan rect should restore cleanly\n"
      "  - NO black holes or artifacts left behind the sprite\n"
      "  - Watch carefully as sprite crosses over the cyan rectangle")
def test_sprite_restoration(api):
    create_starfield_background(api)
    create_test_sprite(api, name="mover", size=10)
    api.execute_command('set_background(starfield)')
    api.execute_command('draw_rectangle(20, 20, 24, 24, cyan, 100, true)')
    api.execute_command('show_sprite(mover, 0, 30)')

    def loop(frame, elapsed):
        x = int(elapsed * 8) % 64
        y = 30 + int(8 * math.sin(elapsed * 1.5))
        api.execute_command(f'move_sprite(mover, {x}, {y})')
        time.sleep(0.05)

    run_until_enter(loop, "Sprite sweeping — watch for clean restoration...")


@test(8, "Frame Mode Compositing",
      "Smooth animation using begin_frame/end_frame:\n"
      "  - Scrolling starfield + fixed cyan rectangle + orbiting sprite\n"
      "  - Should be FLICKER-FREE (double buffered)\n"
      "  - FPS shown when you press Enter — target 30+")
def test_frame_mode(api):
    create_starfield_background(api)
    create_test_sprite(api, name="frame_sprite", size=10)
    api.execute_command('set_background(starfield)')
    api.execute_command('draw_rectangle(22, 22, 20, 20, cyan, 80, true)')
    api.execute_command('show_sprite(frame_sprite, 32, 32)')

    def loop(frame, elapsed):
        x = int(32 + 22 * math.cos(elapsed * 2.5))
        y = int(32 + 22 * math.sin(elapsed * 2.5))
        api.execute_command('begin_frame(true)')
        api.execute_command('nudge_background(1, 0, 0)')
        api.execute_command(f'move_sprite(frame_sprite, {x}, {y})')
        api.execute_command('end_frame')

    run_until_enter(loop, "Frame mode animation (check for flicker)...")


@test(9, "Immediate Mode Compositing",
      "Same layers but using IMMEDIATE mode (no begin_frame/end_frame):\n"
      "  - Static starfield (not scrolling)\n"
      "  - Fixed cyan rectangle\n"
      "  - ORANGE sprite moving diagonally\n"
      "  - May have slight flicker vs frame mode — that's expected")
def test_immediate_mode(api):
    create_starfield_background(api)
    create_test_sprite(api, name="imm_sprite", size=10)
    api.execute_command('set_background(starfield)')
    api.execute_command('draw_rectangle(20, 20, 24, 24, cyan, 100, true)')
    api.execute_command('show_sprite(imm_sprite, 10, 10)')

    def loop(frame, elapsed):
        x = int(10 + elapsed * 6) % 54
        y = int(10 + elapsed * 3) % 54
        api.execute_command(f'move_sprite(imm_sprite, {x}, {y})')
        time.sleep(0.05)

    run_until_enter(loop, "Immediate mode sprite movement...")


@test(10, "Hide / Show Background Cycle",
      "Background toggles ON and OFF every ~2 seconds:\n"
      "  - ON: Starfield visible with cyan rectangle\n"
      "  - OFF: Black screen, cyan rectangle STILL visible\n"
      "  - The rectangle should ALWAYS be visible (it's in drawing buffer)")
def test_hide_show(api):
    create_starfield_background(api)
    api.execute_command('set_background(starfield)')
    api.execute_command('draw_rectangle(20, 20, 24, 24, cyan, 100, true)')
    bg_visible = [True]  # Use list for mutable closure

    def loop(frame, elapsed):
        # Toggle every 2 seconds based on even/odd period
        should_show = int(elapsed / 2.0) % 2 == 0
        if should_show and not bg_visible[0]:
            api.execute_command('set_background(starfield)')
            bg_visible[0] = True
        elif not should_show and bg_visible[0]:
            api.execute_command('hide_background')
            bg_visible[0] = False
        time.sleep(0.05)

    run_until_enter(loop, "Toggling background on/off every 2 sec...")


@test(11, "Clear Hides Background (Template Survives)",
      "Repeating cycle:\n"
      "  Phase 1: Background + cyan rect visible (~2.5 sec)\n"
      "  Phase 2: CLEAR called — screen goes BLACK (~2.5 sec)\n"
      "  Phase 3: set_background reactivates — starfield returns\n"
      "           but NO cyan rect (drawing buffer was also cleared)")
def test_clear(api):
    create_starfield_background(api)
    phase_duration = 2.5
    last_phase = [-1]  # Track which phase we last executed

    def loop(frame, elapsed):
        cycle = elapsed % (phase_duration * 3)
        if cycle < phase_duration:
            current_phase = 0
        elif cycle < phase_duration * 2:
            current_phase = 1
        else:
            current_phase = 2

        # Only act on phase transitions
        if current_phase != last_phase[0]:
            last_phase[0] = current_phase
            if current_phase == 0:
                api.execute_command('set_background(starfield)')
                api.execute_command('draw_rectangle(20, 20, 24, 24, cyan, 100, true)')
            elif current_phase == 1:
                api.execute_command('clear')
            elif current_phase == 2:
                api.execute_command('set_background(starfield)')
        time.sleep(0.05)

    run_until_enter(loop, "Clear/reactivate cycle...")


@test(12, "Dispose All Sprites Destroys Background",
      "Repeating cycle:\n"
      "  Phase 1: Background created and visible (~2.5 sec)\n"
      "  Phase 2: dispose_all_sprites — screen goes BLACK (~2.5 sec)\n"
      "           Template is DESTROYED (cannot reactivate)\n"
      "  Phase 3: Recreates sprite from scratch, background returns")
def test_dispose(api):
    phase_duration = 2.5
    last_phase = [-1]

    def loop(frame, elapsed):
        cycle = elapsed % (phase_duration * 3)
        if cycle < phase_duration:
            current_phase = 0
        elif cycle < phase_duration * 2:
            current_phase = 1
        else:
            current_phase = 2

        if current_phase != last_phase[0]:
            last_phase[0] = current_phase
            if current_phase == 0:
                # Recreate sprite (template was destroyed by dispose)
                if api.sprite_manager.get_template('starfield') is None:
                    create_starfield_background(api)
                api.execute_command('set_background(starfield)')
            elif current_phase == 1:
                api.execute_command('dispose_all_sprites')
            # Phase 2: stays black (template destroyed, nothing to do)
        time.sleep(0.05)

    run_until_enter(loop, "Dispose/recreate cycle...")


@test(13, "Performance Benchmark",
      "Full layer stack running at MAX SPEED:\n"
      "  - Scrolling background + drawing buffer + orbiting sprite\n"
      "  - Let it run for several seconds, then press Enter\n"
      "  - FPS will be displayed — target: 30+")
def test_performance(api):
    create_starfield_background(api)
    create_test_sprite(api, name="perf_sprite", size=12)
    api.execute_command('set_background(starfield)')
    api.execute_command('draw_rectangle(22, 22, 20, 20, cyan, 80, true)')
    api.execute_command('show_sprite(perf_sprite, 32, 32)')

    def loop(frame, elapsed):
        x = int(32 + 22 * math.cos(elapsed * 3))
        y = int(32 + 22 * math.sin(elapsed * 3))
        api.execute_command('begin_frame(true)')
        api.execute_command('nudge_background(1, 0, 0)')
        api.execute_command(f'move_sprite(perf_sprite, {x}, {y})')
        api.execute_command('end_frame')

    run_until_enter(loop, "Running at max speed for FPS measurement...")


# ============================================================
# Main
# ============================================================

def main():
    start_from = 1
    if len(sys.argv) > 1:
        try:
            start_from = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [start_test_number]")
            sys.exit(1)

    TESTS.sort(key=lambda t: t['number'])

    api = get_api_instance()

    old_settings = termios.tcgetattr(sys.stdin)

    try:
        print("=" * 65)
        print("  Background Layer Interactive Test Suite")
        print("=" * 65)
        print(f"  {len(TESTS)} tests available (starting from test {start_from})")
        print("  Each test runs until you press Enter")
        print("  Ctrl+C to exit at any time")
        print("=" * 65)

        passed = 0
        skipped = 0
        failed = 0

        for t in TESTS:
            if t['number'] < start_from:
                skipped += 1
                continue

            cleanup_between_tests(api)

            print(f"\n{'─' * 65}")
            print(f"  TEST {t['number']}: {t['title']}")
            print(f"{'─' * 65}")
            print(f"\n  What to look for:")
            for line in t['look_for'].split('\n'):
                print(f"  {line}")

            wait_for_enter(f"Press Enter to START test {t['number']}...")

            try:
                t['fn'](api)
                passed += 1
                print(f"\n  ✓ Test {t['number']} complete")
            except AssertionError as e:
                failed += 1
                print(f"\n  ✗ Test {t['number']} ASSERTION FAILED: {e}")
            except Exception as e:
                failed += 1
                print(f"\n  ✗ Test {t['number']} ERROR: {e}")
                import traceback
                traceback.print_exc()

        cleanup_between_tests(api)
        print(f"\n{'=' * 65}")
        print(f"  RESULTS: {passed} passed, {failed} failed, {skipped} skipped")
        print(f"{'=' * 65}")

    except KeyboardInterrupt:
        print("\n\n  Interrupted by user")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        cleanup()
        print("  Cleanup complete")


if __name__ == "__main__":
    main()
