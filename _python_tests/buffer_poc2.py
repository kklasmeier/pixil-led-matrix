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
        self.offscreen_canvas = self.matrix.CreateFrameCanvas()
        self.frame_mode_canvas = self.matrix.CreateFrameCanvas()
        self.frame_mode_canvas = self.matrix.CreateFrameCanvas()
        self.frame_mode = False
        
        print("Initialization complete")

    def _draw_to_buffers(self, x: int, y: int, r: int, g: int, b: int):
        """Core pixel drawing function"""
        if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
            print(f"Drawing pixel at ({x},{y}) color=({r},{g},{b}) frame_mode={self.frame_mode}")
            if self.frame_mode:
                self.frame_mode_canvas.SetPixel(x, y, r, g, b)
            else:
                self.offscreen_canvas.SetPixel(x, y, r, g, b)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: tuple):
        """Draw a line using Bresenham's algorithm"""
        print(f"Drawing line from ({x0},{y0}) to ({x1},{y1}) color={color}")
        r, g, b = color
        
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            self._draw_to_buffers(x0, y0, r, g, b)
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
        """Start frame mode"""
        print("Beginning frame mode")
        self.frame_mode = True
        self.frame_mode_canvas.Fill(0, 0, 0)  # Clear frame buffer

    def end_frame(self):
        """End frame mode and display buffer"""
        if self.frame_mode:
            print("Ending frame mode - swapping buffers")
            self.frame_mode_canvas = self.matrix.SwapOnVSync(self.frame_mode_canvas)
            self.frame_mode = False

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
    matrix.draw_line(20, 40, 30, 50, (0, 255, 0))
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
        
        # Frame mode lines
        print("Frame mode drawing...")
        matrix.begin_frame()
        matrix.draw_line(i*10, 20, i*10+5, 30, (0, 255, 0))
        matrix.draw_line(i*10+2, 20, i*10+7, 30, (0, 0, 255))
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