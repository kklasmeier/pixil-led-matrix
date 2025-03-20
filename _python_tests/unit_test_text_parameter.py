# test_text_commands.py
from rgb_matrix_lib import execute_command
import time

def test_text_commands():
    print("\nTesting Text Command Parsing...")

    # Test setup
    execute_command("clear()")
    
    test_cases = [
        # Basic text
        'draw_text(10, 5, "Simple Text", piboto-regular, 12, white)',
        
        # Text with commas
        'draw_text(10, 20, "Hello, World", piboto-regular, 12, green)',
        
        # Text with escaped quotes
        'draw_text(10, 35, "She said ""Hello""", piboto-regular, 12, blue)',
        
        # Complex case with commas and quotes
        'draw_text(10, 50, "Quote: ""Hello, World!"", end.", piboto-regular, 12, cyan)'
    ]

    try:
        for cmd in test_cases:
            print(f"\nExecuting: {cmd}")
            execute_command(cmd)
            time.sleep(2)  # Wait to see the result
            
            # Clear previous text using coordinates from the command
            x = int(cmd.split(',')[0].split('(')[1])
            y = int(cmd.split(',')[1].strip())
            execute_command(f"clear_text({x}, {y})")
            time.sleep(0.5)

    except Exception as e:
        print(f"Error during test: {str(e)}")
    finally:
        execute_command("clear()")

if __name__ == "__main__":
    try:
        test_text_commands()
        print("\nTests completed")
    except KeyboardInterrupt:
        execute_command("clear()")
        print("\nTests interrupted by user")