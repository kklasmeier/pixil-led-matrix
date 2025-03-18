#!/usr/bin/env python
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time

class MatrixPOC:
    def __init__(self):
        print("Initializing matrix...")
        # Configure matrix
        self.options = RGBMatrixOptions()
        self.options.rows = 64
        self.options.cols = 64
        self.options.hardware_mapping = 'adafruit-hat'
        self.options.gpio_slowdown = 3
        self.options.scan_mode = 1
        self.options.pwm_bits = 11
        
        # Create matrix
        self.matrix = RGBMatrix(options=self.options)
        
        # Create canvases
        self.canvas = self.matrix.CreateFrameCanvas()
        
        self.matrix.SwapOnVSync(self.canvas)        


        
        # Clear the initial canvas
        self.canvas.Fill(0, 0, 0)
        
        self.frame_mode = False
        print("Initialization complete")

    def clear_canvas(self):
        """Clear the current canvas"""
        self.canvas.Fill(0, 0, 0)

    def _draw_to_canvas(self, x: int, y: int, r: int, g: int, b: int):
        """Draw a pixel to the current canvas"""
        if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
            self.canvas.SetPixel(x, y, r, g, b)
            print(f"Drawing pixel ({x},{y}) color=({r},{g},{b})")

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: tuple):
        """Draw a line using Bresenham's algorithm"""
        print(f"Drawing line from ({x0},{y0}) to ({x1},{y1}) color={color}")

        time.sleep(1)

        r, g, b = color
        
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            self._draw_to_canvas(x0, y0, r, g, b)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def begin_frame(self):
        """Prepare for frame mode by clearing the canvas"""
        print("Beginning frame mode")
        self.frame_mode = True
        self.clear_canvas()

    def end_frame(self):
        """End frame mode and update the display"""
        if self.frame_mode:
            print("Ending frame mode - updating display")
            # Swap the canvas to update the display
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            self.frame_mode = False

    def switch_to_immediate_mode(self):
        """Explicitly switch to immediate mode"""
        print("Switching to immediate mode")
        # Ensure any pending frame is displayed
        if self.frame_mode:
            self.end_frame()
        # Clear any previous drawing
        self.clear_canvas()

# Test functions remain the same
def test_immediate_mode():
    print("\nTest 1: Immediate Mode Drawing")
    matrix = MatrixPOC()
    
    print("Drawing red diagonal line...")
    matrix.draw_line(0, 0, 10, 10, (255, 0, 0))
    time.sleep(2)
    
    print("Drawing blue diagonal line...")
    matrix.draw_line(20, 0, 30, 10, (0, 0, 255))
    time.sleep(2)

def test_frame_mode():
    print("\nTest 2: Frame Mode Drawing")
    matrix = MatrixPOC()
    
    print("Beginning frame...")
    matrix.begin_frame()
    
    print("Drawing green line (should not appear yet)...")
    matrix.draw_line(0, 20, 10, 30, (0, 255, 0))
    time.sleep(2)
    
    print("Drawing yellow line (should not appear yet)...")
    matrix.draw_line(20, 20, 30, 30, (255, 255, 0))
    time.sleep(2)
    
    print("Ending frame (both lines should appear together)...")
    matrix.end_frame()
    time.sleep(2)

def test_mixed_mode():
    print("\nTest 3: Mixed Mode Drawing")
    matrix = MatrixPOC()
    
    print("Drawing red line in immediate mode...")
    matrix.draw_line(0, 40, 10, 50, (255, 0, 0))
    time.sleep(2)
    
    print("Starting frame mode...")
    matrix.begin_frame()
    print("Drawing green line in frame mode...")
    matrix.draw_line(20, 40, 69, 10, (0, 255, 0))
    matrix.draw_line(22, 40, 68, 20, (255, 0, 0))
    matrix.draw_line(23, 40, 67, 30, (0, 255, 0))
    matrix.draw_line(24, 40, 66, 40, (255, 0, 0))
    matrix.draw_line(25, 40, 65, 50, (0, 255, 0))
    matrix.draw_line(26, 40, 64, 60, (255, 0, 0))
    matrix.draw_line(27, 40, 63, 70, (0, 255, 0))
    matrix.draw_line(28, 40, 62, 80, (255, 0, 0))
    matrix.draw_line(29, 40, 61, 90, (0, 255, 0))
    matrix.draw_line(30, 40, 59, 10, (255, 0, 0))
    matrix.draw_line(31, 40, 58, 20, (0, 255, 0))
    matrix.draw_line(32, 40, 57, 30, (255, 0, 0))
    time.sleep(2)
    print("Ending frame mode...")
    matrix.end_frame()
    time.sleep(2)
    
    print("Drawing blue line in immediate mode...")
    matrix.draw_line(40, 40, 50, 50, (0, 0, 255))
    time.sleep(2)

    print("Starting frame mode...")
    matrix.begin_frame()
    print("Drawing complex line pattern...")
    matrix.draw_line(10, 63, 54, 10, (0, 255, 0))  # Green
    matrix.draw_line(12, 63, 52, 20, (255, 0, 0))  # Red
    matrix.draw_line(14, 63, 50, 30, (0, 255, 0))  # Green
    matrix.draw_line(16, 63, 48, 40, (255, 0, 0))  # Red
    matrix.draw_line(18, 63, 46, 50, (0, 255, 0))  # Green
    matrix.draw_line(20, 63, 44, 60, (255, 0, 0))  # Red
    matrix.draw_line(22, 63, 42, 54, (0, 255, 0))  # Green
    matrix.draw_line(24, 63, 40, 48, (255, 0, 0))  # Red
    matrix.draw_line(26, 63, 38, 42, (0, 255, 0))  # Green
    matrix.draw_line(28, 63, 36, 36, (255, 0, 0))  # Red
    matrix.draw_line(30, 63, 34, 30, (0, 255, 0))  # Green
    matrix.draw_line(32, 63, 32, 24, (255, 0, 0))  # Red
    time.sleep(2)
    print("Ending frame mode...")
    matrix.end_frame()
    time.sleep(2)

    print("Drawing blue line in immediate mode...")
    matrix.draw_line(40, 40, 50, 50, (0, 0, 255))
    time.sleep(2)

def test_rapid_switching():
    print("\nTest 4: Rapid Mode Switching")
    matrix = MatrixPOC()
    
    for i in range(5):
        print(f"\nIteration {i+1}")
        
        # Immediate mode line
        print("Drawing red line in immediate mode...")
        matrix.draw_line(i*10, 0, i*10+5, 10, (255, 0, 0))
        time.sleep(0.5)
        
        # Complex frame mode pattern
        print("Frame mode drawing complex pattern...")
        matrix.begin_frame()
        # Starburst pattern
        matrix.draw_line(32, 32, 32+i*5, 32+i*5, (0, 255, 0))    # Green diagonal
        matrix.draw_line(32, 32, 32-i*5, 32-i*5, (0, 0, 255))    # Blue opposite diagonal
        matrix.draw_line(32, 32, 32+i*5, 32-i*5, (255, 255, 0))  # Yellow cross diagonal
        matrix.draw_line(32, 32, 32-i*5, 32+i*5, (255, 0, 255))  # Purple opposite cross
        
        # Box frame
        matrix.draw_line(10+i, 10+i, 50-i, 10+i, (255, 128, 0))  # Orange top
        matrix.draw_line(50-i, 10+i, 50-i, 50-i, (128, 255, 0))  # Lime right
        matrix.draw_line(50-i, 50-i, 10+i, 50-i, (0, 255, 128))  # Cyan bottom
        matrix.draw_line(10+i, 50-i, 10+i, 10+i, (128, 0, 255))  # Purple left
        
        # Cross pattern
        matrix.draw_line(0, 32, 63, 32, (255, 64, 64))     # Red horizontal
        matrix.draw_line(32, 0, 32, 63, (64, 64, 255))     # Blue vertical
        
        # Additional decorative elements
        matrix.draw_line(0, i*10, 63, 63-i*10, (64, 255, 64))  # Green sweep
        matrix.end_frame()
        time.sleep(0.5)

def main():
    print("RGBMatrix Drawing Mode POC")
    print("1: Test Immediate Mode")
    print("2: Test Frame Mode")
    print("3: Test Mixed Mode")
    print("4: Test Rapid Switching")
    
    try:
        test_to_run = input("Select test (1-4): ")
        if test_to_run == "1":
            test_immediate_mode()
        elif test_to_run == "2":
            test_frame_mode()
        elif test_to_run == "3":
            test_mixed_mode()
        elif test_to_run == "4":
            test_rapid_switching()
        else:
            print("Invalid selection")
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()