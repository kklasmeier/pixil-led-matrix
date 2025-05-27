from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time

def setup_matrix():
    """Initialize the matrix with the same settings as your library."""
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 3
    options.pwm_bits = 11
    options.scan_mode = 1
    return RGBMatrix(options=options)

def scale_to_8bit(value):
    """Scale a 0-2047 value to 0-255 safely."""
    return max(0, min(255, int(value / 8)))

def draw_color_gradients(matrix):
    """Draw color gradient test patterns."""
    canvas = matrix.CreateFrameCanvas()
    
    # Define test patterns
    patterns = [
        ('Red Channel', lambda x: (x, 0, 0)),
        ('Green Channel', lambda x: (0, x, 0)),
        ('Blue Channel', lambda x: (0, 0, x)),
        ('Gray Scale', lambda x: (x, x, x)),
        ('Red-Blue Mix', lambda x: (x, 0, 2047-x)),  # Modified to use full range
        ('RGB Diagonal', lambda x: (x, x//2, x//4))   # Modified for safer values
    ]
    
    try:
        while True:
            for pattern_name, color_func in patterns:
                print(f"Displaying: {pattern_name}")
                
                # Draw gradient
                for x in range(64):
                    for y in range(64):
                        # Scale x to full PWM range (0-2047)
                        scaled_x = int((x / 63.0) * 2047)
                        r, g, b = color_func(scaled_x)
                        # Safely convert to 8-bit color values
                        r8 = scale_to_8bit(r)
                        g8 = scale_to_8bit(g)
                        b8 = scale_to_8bit(b)
                        canvas.SetPixel(x, y, r8, g8, b8)
                
                # Update display
                canvas = matrix.SwapOnVSync(canvas)
                time.sleep(5)  # Show each pattern for 5 seconds
                
    except KeyboardInterrupt:
        print("\nTest completed")

def main():
    matrix = setup_matrix()
    print("Starting color depth test...")
    print("This will display various color gradient patterns.")
    print("Each pattern will be shown for 5 seconds.")
    print("Observe the smoothness of transitions to evaluate color depth.")
    print("Press CTRL+C to exit.")
    
    draw_color_gradients(matrix)

if __name__ == "__main__":
    main()