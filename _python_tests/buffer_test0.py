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

def test_buffer_behavior():
    matrix = setup_matrix()
    canvas = matrix.CreateFrameCanvas()

    print("\nTest 1: Draw without SwapOnVSync")
    print("Drawing blue dot - this is not seen")
    canvas.SetPixel(10, 20, 0, 0, 255)  # Blue dot
    time.sleep(5)

    print("\nTest 2: Now SwapOnVSync")
    matrix.SwapOnVSync(canvas)
    print("Now we see the blue dot")
    time.sleep(5)

    print("\nTest 3: Draw two objects with one swap")
    canvas.SetPixel(30, 30, 255, 0, 0)  # Red dot
    print("Drew red dot - we should see without doing a SwapOnVSync")
    time.sleep(5)

    canvas.SetPixel(40, 40, 0, 255, 0)  # Green dot
    print("Drew green dot - we should see without doing a SwapOnVSync")
    time.sleep(5)

    print("Now swapping - this has no effect on what is already there")
    matrix.SwapOnVSync(canvas)
    time.sleep(5)

    print("\nTest 4: Clear and verify")
    canvas.Fill(0, 0, 0)  # Clear the canvas
    time.sleep(5)
    print("Cleared canvas but haven't swapped the display clears.")

    time.sleep(1)

if __name__ == "__main__":
    try:
        print("Starting buffer behavior test")
        test_buffer_behavior()
    except KeyboardInterrupt:
        print("Exiting...")