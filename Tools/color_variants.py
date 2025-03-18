from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time
import sys
import tty
import termios
import numpy as np

def setup_matrix():
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 3
    options.pwm_bits = 11
    options.scan_mode = 1
    return RGBMatrix(options=options)

def get_key():
    """Get a single keypress without waiting for enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# Key spectral points for 0-99 color system
SPECTRAL_POINTS = {
    0: (2047, 2047, 2047),  # White
    10: (2047, 0, 0),       # Red
    20: (2047, 512, 0),     # Red-Orange
    30: (2047, 1024, 0),    # Orange
    40: (2047, 1536, 0),    # Yellow-Orange
    50: (2047, 2047, 0),    # Yellow
    60: (1024, 2047, 0),    # Yellow-Green
    70: (0, 2047, 0),       # Green
    80: (0, 2047, 1024),    # Blue-Green
    90: (0, 0, 2047),       # Blue
    99: (1024, 0, 2047)     # Purple
}

def interpolate_color(index):
    """Interpolate color for any point in the 0-99 spectrum."""
    # Find surrounding key points
    lower_point = max(p for p in SPECTRAL_POINTS.keys() if p <= index)
    upper_point = min(p for p in SPECTRAL_POINTS.keys() if p >= index)

    # If exact match, return the color
    if lower_point == upper_point:
        return SPECTRAL_POINTS[lower_point]

    # Interpolate between points
    lower_color = np.array(SPECTRAL_POINTS[lower_point])
    upper_color = np.array(SPECTRAL_POINTS[upper_point])
    
    fraction = (index - lower_point) / (upper_point - lower_point)
    interpolated = lower_color + (upper_color - lower_color) * fraction
    
    return tuple(int(round(c)) for c in interpolated)

def apply_intensity(color, intensity):
    """Apply intensity scaling to a color."""
    scale = intensity / 99.0
    return tuple(int(round(c * scale)) for c in color)

def scale_to_8bit(value):
    """Scale 11-bit color value (0-2047) to 8-bit (0-255)."""
    return max(0, min(255, int(value / 8)))

def draw_spectral_test(matrix):
    """Draw spectral color test with intensity variations."""
    canvas = matrix.CreateFrameCanvas()
    
    try:
        while True:
            # Cycle through spectral colors (0-99)
            for color_index in range(100):
                print(f"\nDisplaying color index: {color_index}")
                print(f"Key color points: {', '.join(str(k) for k in SPECTRAL_POINTS.keys())}")
                print("Press SPACE for next color or Q to quit")
                
                # Get the base color for this index
                base_color = interpolate_color(color_index)
                
                # Draw vertical line of full intensity color on left edge
                for y in range(64):
                    r8 = scale_to_8bit(base_color[0])
                    g8 = scale_to_8bit(base_color[1])
                    b8 = scale_to_8bit(base_color[2])
                    canvas.SetPixel(0, y, r8, g8, b8)
                
                # Fill rest of display with intensity variations
                # Each row will show the same progression of intensity
                for y in range(64):
                    for x in range(1, 64):  # Start at x=1 since x=0 is full intensity
                        # Calculate intensity based on x position (63 steps)
                        intensity = 99 - int((x - 1) * (99.0 / 62))  # Map x=1-63 to intensity 99-0
                        
                        # Apply intensity to base color
                        color = apply_intensity(base_color, intensity)
                        
                        # Draw pixel
                        r8 = scale_to_8bit(color[0])
                        g8 = scale_to_8bit(color[1])
                        b8 = scale_to_8bit(color[2])
                        canvas.SetPixel(x, y, r8, g8, b8)
                
                # Update display
                matrix.SwapOnVSync(canvas)
                
                # Wait for keypress
                key = get_key()
                if key.lower() == 'q':
                    return
                elif key == ' ':
                    continue
                    
    except KeyboardInterrupt:
        print("\nTest completed")

def main():
    matrix = setup_matrix()
    print("Starting Spectral Color Test...")
    print("This will display each color with intensity variations")
    print("Left edge shows full intensity color")
    print("Rest of display shows intensity variations")
    print("Press SPACE to advance through colors")
    print("Press Q to quit")
    
    draw_spectral_test(matrix)
    
    # Clear display on exit
    canvas = matrix.CreateFrameCanvas()
    canvas.Fill(0, 0, 0)
    matrix.SwapOnVSync(canvas)

if __name__ == "__main__":
    main()