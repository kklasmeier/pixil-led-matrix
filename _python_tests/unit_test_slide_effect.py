# test_slide_effect.py
from rgb_matrix_lib import execute_command
import time

def test_slide_effects():
    print("\nTesting Slide Effects...")
    
    # Clear display
    execute_command("clear()")
    
    # Test each direction
    test_commands = [
        # From right to left (default)
        ('draw_text(16, 41, "12321", "piboto-regular", 12, 23:90, "WIPE", "IN_LEFT")', 2),
        ('clear_text(16, 41)', 0.5),

        ('draw_text(12, 33, 2241, piboto-regular, 12, 44:20, WIPE, IN_LEFT)', 2),
        ('clear_text(12, 33)', 0.5),

        ('draw_text(1, 14, "Wipe In", piboto-regular, 12, white:16, WIPE, IN_RIGHT)', 2),
        ('clear_text(1, 14)', 0.5),

        ('draw_text(4, 40, "Wipe In", piboto-regular, 12, blue, WIPE, IN_UP)', 2),
        ('clear_text(4, 40)', 0.5),

        ('draw_text(0, 50, "Wipe In", piboto-regular, 12, yellow, WIPE, IN_DOWN)', 2),
        ('clear_text(0, 50)', 0.5),

        ('draw_text(3, 3, "Wipe Out", piboto-regular, 12, red, WIPE, OUT_LEFT)', 2),
        ('draw_text(1, 14, "Wipe Out", piboto-regular, 12, white, WIPE, OUT_RIGHT)', 2),
        ('draw_text(4, 40, "Wipe Out", piboto-regular, 12, blue, WIPE, OUT_UP)', 2),
        ('draw_text(0, 50, "Wipe Out", piboto-regular, 12, yellow, WIPE, OUT_DOWN)', 2),

        ('draw_text(5, 20, "Dissolve In", piboto-regular, 12, green, DISSOLVE, IN)', 2),
        ('clear_text(5, 20)', 0.5),

        ('draw_text(2, 35, "Dissolve Out", piboto-regular, 12, blue, DISSOLVE, OUT)', 2),

        ('draw_text(10, 10, "Slide Left", piboto-regular, 12, orange, SLIDE, LEFT)', 2),
        ('clear_text(10, 10)', 0.5),
        
        # From left to right
        ('draw_text(10, 25, "Slide Right", piboto-regular, 12, green, SLIDE, RIGHT)', 2),
        ('clear_text(10, 25)', 0.5),
        
        # From bottom to top
        ('draw_text(10, 40, "Slide Up", piboto-regular, 12, blue, SLIDE, UP)', 2),
        ('clear_text(10, 40)', 0.5),
        
        # From top to bottom
        ('draw_text(10, 55, "Slide Down", piboto-regular, 12, cyan, SLIDE, DOWN)', 2),
        ('clear_text(10, 55)', 0.5),
    ]
    
    try:
        for cmd, pause in test_commands:
            print(f"\nExecuting: {cmd}")
            execute_command(cmd)
            time.sleep(pause)
                
    except Exception as e:
        print(f"Error during test: {str(e)}")
    finally:
        execute_command("clear()")
        print("\nSlide effect tests completed")

if __name__ == "__main__":
    try:
        test_slide_effects()
    except KeyboardInterrupt:
        execute_command("clear()")
        print("\nTests interrupted by user")