#!/usr/bin/env python
from rgb_matrix_lib.api import RGB_Api
import time

def test_line():
    api = RGB_Api()
    
    # Direct canvas test (bypass our buffer system)
    r, g, b = 255, 0, 0  # Red
    for x in range(30):
        y = int((40.0/30.0) * x)
        api.offscreen_canvas.SetPixel(x, y, r, g, b)
    
    api.matrix.SwapOnVSync(api.offscreen_canvas)
    time.sleep(5)

if __name__ == "__main__":
    try:
        test_line()
    except KeyboardInterrupt:
        print("Exiting...")