#!/usr/bin/env python
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time

def setup_matrix():
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 3
    options.scan_mode = 1
    options.pwm_bits = 11
    return RGBMatrix(options=options)

def test_line():
    matrix = setup_matrix()
    canvas = matrix.CreateFrameCanvas()
    
    # Draw a red line from (0,0) to (30,40)
    r, g, b = 255, 0, 0  # Red
    for x in range(30):
        y = int((40.0/30.0) * x)  # Simple line algorithm
        canvas.SetPixel(x, y, r, g, b)
    
    # Show it
    matrix.SwapOnVSync(canvas)
    time.sleep(5)

if __name__ == "__main__":
    try:
        test_line()
    except KeyboardInterrupt:
        print("Exiting...")