#!/usr/bin/python3

from rgb_matrix_lib import execute_command, cleanup
import time
import argparse

def parse_test_flags(flags):
    if len(flags) != 6:
        raise ValueError("Must provide exactly 5 test flags (y/n)")
    return [flag.lower() == 'y' for flag in flags]

def run_color_tests(test_flags):
    print("Starting color system tests...")
    
    # Basic point plotting with different color formats
    if test_flags[0]:
        print("\nRunning basic plotting tests...")
        commands = [
            # Named colors
            'plot(10, 10, red)',
            'plot(10, 12, blue)',
            'plot(10, 14, green)',
            
            # Named colors with intensity
            'plot(12, 10, red:75)',
            'plot(12, 12, blue:50)',
            'plot(12, 14, green:25)',
            
            # Spectral colors
            'plot(14, 10, 10)',      # Pure red
            'plot(14, 12, 50)',      # Pure yellow
            'plot(14, 14, 90)',      # Pure blue
            
            # Spectral colors with intensity
            'plot(16, 10, 10:75)',   # Red at 75%
            'plot(16, 12, 50:50)',   # Yellow at 50%
            'plot(16, 14, 90:25)',   # Blue at 25%
        ]
        
        for cmd in commands:
            print(f"Executing: {cmd}")
            execute_command(cmd)
            time.sleep()
    else:
        print("\nSkipping basic plotting tests...")

    # Test shapes with different color formats
    if test_flags[1]:
        print("\nRunning shape tests...")
        shape_commands = [
            # Lines with various colors
            'draw_line(20, 10, 30, 10, red)',
            'draw_line(20, 12, 30, 12, blue:50)',
            'draw_line(20, 14, 30, 14, 50)',
            'draw_line(20, 16, 30, 16, 50:50)',
            
            # Rectangles with various colors and fills
            'draw_rectangle(32, 10, 8, 8, green, true)',
            'draw_rectangle(32, 20, 8, 8, green:50, true)',
            'draw_rectangle(42, 10, 8, 8, 70, true)',
            'draw_rectangle(42, 20, 8, 8, 70:50, true)',
            
            # Circles with various colors and fills
            'draw_circle(55, 14, 4, yellow, true)',
            'draw_circle(55, 24, 4, yellow:50, true)',
            'draw_circle(55, 34, 4, 30, true)',
            'draw_circle(55, 44, 4, 30:50, true)',
        ]
        
        for cmd in shape_commands:
            print(f"Executing: {cmd}")
            execute_command(cmd)
            time.sleep(.01)
    else:
        print("\nSkipping shape tests...")

    # Test sprite system with colors
    if test_flags[2]:
        print("\nRunning sprite tests...")
        sprite_commands = [
            # Define test sprite
            'define_sprite(test_sprite, 8, 8)',
            
            # Draw on sprite with different colors
            'sprite_draw(test_sprite, draw_rectangle, 0, 0, 8, 8, red, true)',
            'sprite_draw(test_sprite, draw_circle, 4, 4, 3, blue:50, true)',
            
            # Show sprite
            'show_sprite(test_sprite, 10, 50)',
            
            # Define test sprite
            'define_sprite(test_sprite2, 8, 8)',
            
            # Draw on sprite with different colors
            'sprite_draw(test_sprite2, draw_rectangle, 0, 0, 8, 8, 50:75, true)',
            'sprite_draw(test_sprite2, draw_circle, 4, 4, 3, 30, true)',
            
            # Show sprite
            'show_sprite(test_sprite2, 20, 50)'
        ]
        
        for cmd in sprite_commands:
            print(f"Executing: {cmd}")
            execute_command(cmd)
            time.sleep(.01)
    else:
        print("\nSkipping sprite tests...")

    # Test frame buffering with colors
    if test_flags[3]:
        print("\nRunning frame buffer tests...")
        frame_commands = [
            'begin_frame',
            'draw_rectangle(0, 0, 8, 8, red, true)',
            'draw_rectangle(8, 0, 8, 8, 30:75, true)',
            'draw_circle(12, 12, 4, blue:50, true)',
            'draw_circle(24, 24, 4, 50, true)',
            'end_frame'
        ]
        
        for cmd in frame_commands:
            print(f"Executing: {cmd}")
            execute_command(cmd)
            time.sleep(.01)
    else:
        print("\nSkipping frame buffer tests...")

    # Test polygons
    if test_flags[4]:
        print("\nRunning polygon tests...")
        polygon_commands = [
            # Basic polygons
            'draw_polygon(10, 10, 8, 3, red)',          # Triangle
            'draw_polygon(30, 10, 8, 4, blue, 45)',     # Rotated square
            'draw_polygon(50, 10, 8, 6, green, 0, true)', # Filled hexagon
            
            # Color variations
            'draw_polygon(10, 30, 8, 5, red:75)',       # Pentagon with intensity
            'draw_polygon(30, 30, 8, 8, 50)',           # Octagon with spectral color
            'draw_polygon(50, 30, 8, 3, 70:50)',        # Triangle with spectral+intensity
            
            # Sprite with polygons
            'define_sprite(poly_sprite, 16, 16)',
            'sprite_draw(poly_sprite, draw_polygon, 8, 8, 7, 4, 15:10, 10, false)',
            'show_sprite(poly_sprite, 10, 50)',
            'move_sprite(poly_sprite, 10, 49)',
            'move_sprite(poly_sprite, 10, 48)',
            'move_sprite(poly_sprite, 10, 47)',
            'move_sprite(poly_sprite, 10, 46)',
            'move_sprite(poly_sprite, 10, 45)',
            'move_sprite(poly_sprite, 10, 44)',
            'move_sprite(poly_sprite, 10, 43)',
            'move_sprite(poly_sprite, 10, 42)',
            'move_sprite(poly_sprite, 10, 41)',
            'move_sprite(poly_sprite, 10, 40)',
            
            ## Frame buffer with polygons
            'begin_frame',
            'draw_polygon(32, 48, 10, 4, green:75, 45, true)',
            'draw_polygon(48, 48, 10, 3, yellow, 30, false)',
            'end_frame',

            # Clear
            'clear()',
            
            # Burnout test
            'draw_polygon(20, 20, 12, 5, magenta, 0, true, 1000)',
            'rest(3)',
            'draw_polygon(20, 20, 12, 5, magenta, 0, true, 2000)',
        ]
        
        for cmd in polygon_commands:
            print(f"Executing: {cmd}")
            execute_command(cmd)
            time.sleep(.1)
    else:
        print("\nSkipping polygon tests...")    

    # Test frame buffering with colors
    if test_flags[5]:
        print("\nRunning text tests...")
        
        # First clear the screen
        execute_command('clear()')
        
        # Draw all text at once
        execute_command('draw_text(10, 10, a1234567890, DejaVuSans-ExtraLight, 12, white, NORMAL)')
        execute_command('rest(1)')
        execute_command('draw_text(10, 30, a1234567890, piboto-regular, 12, green, TYPE, MEDIUM)')
        execute_command('rest(1)')
        execute_command('draw_text(10, 50, Test Scan, piboto-regular, 12, blue, SCAN)')
        execute_command('rest(1)')
        
        # Rest and clear operations
        execute_command('rest(2)')
        
        # Clear text operations
        execute_command('clear_text(10, 10)')
        execute_command('rest(1)')
        execute_command('clear_text(10, 30)')
        execute_command('rest(1)')
        execute_command('clear_text(10, 50)')
        execute_command('rest(1)')
        
        # Final clear
        execute_command('clear()')
    else:
        print("\nSkipping text tests...")

    time.sleep(2)
    print("\nRunning text tests completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run color system tests with selective test execution.')
    parser.add_argument('test_flags', help='Six y/n flags for tests (e.g., "nyyyyn" runs first 4 tests but skips polygon test)')    
    args = parser.parse_args()
    
    try:
        test_flags = parse_test_flags(args.test_flags)
        run_color_tests(test_flags)
    except ValueError as e:
        print(f"Error: {e}")
    finally:
        cleanup()
        print("Cleanup completed.")