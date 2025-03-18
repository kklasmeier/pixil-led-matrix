#!/usr/bin/env python
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time
import numpy as np

def setup_matrix():
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 3
    options.scan_mode = 1
    options.pwm_bits = 11
    return RGBMatrix(options=options)

def test_buffer_behavior():
    matrix = setup_matrix()
    canvas = matrix.CreateFrameCanvas()
    # Our in-memory buffer
    drawing_buffer = np.zeros((64, 64, 3), dtype=np.uint8)
    frame_mode = False
    
    def draw_dot(x, y, r, g, b):
        # Always update our buffer
        drawing_buffer[y, x] = [r, g, b]
        # Update canvas only if not in frame mode
        if not frame_mode:
            canvas.SetPixel(x, y, r, g, b)
            matrix.SwapOnVSync(canvas)
    
    # Test 1: Normal mode - immediate updates
    print("Test 1: Normal mode - dots should appear immediately")
    draw_dot(10, 20, 0, 0, 255)  # Blue
    time.sleep(2)
    draw_dot(20, 20, 255, 0, 0)  # Red
    time.sleep(5)
    
    # Test 2: Frame mode
    print("\nTest 2: Frame mode - dots should appear all at once")
    frame_mode = True  # begin_frame
    print("Drawing dots (should not see them yet)")
    draw_dot(30, 20, 0, 255, 0)  # Green
    time.sleep(2)
    draw_dot(40, 20, 255, 255, 0)  # Yellow
    time.sleep(5)
    
    # end_frame - copy buffer to canvas
    print("Ending frame - now dots should appear")
    start_time = time.time()
    for y in range(64):
        for x in range(64):
            r, g, b = drawing_buffer[y, x]
            canvas.SetPixel(x, y, r, g, b)
    matrix.SwapOnVSync(canvas)
    end_time = time.time()
    print(f"Buffer copy took {(end_time - start_time)*1000:.2f}ms")
    frame_mode = False
    
    time.sleep(5)

if __name__ == "__main__":
    try:
        test_buffer_behavior()
    except KeyboardInterrupt:
        print("Exiting...")