#!/usr/bin/env python
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import time
import numpy as np
import math

def setup_matrix():
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 3
    options.scan_mode = 1
    options.pwm_bits = 11
    return RGBMatrix(options=options)

def test_animation_performance():
    matrix = setup_matrix()
    canvas = matrix.CreateFrameCanvas()
    drawing_buffer = np.zeros((64, 64, 3), dtype=np.uint8)
    frame_mode = False
    frame_times = []
    
    def draw_dot(x, y, r, g, b):
        drawing_buffer[y, x] = [r, g, b]
        if not frame_mode:
            canvas.SetPixel(x, y, r, g, b)
            matrix.SwapOnVSync(canvas)

    def end_frame():
        start_time = time.time()
        for y in range(64):
            for x in range(64):
                r, g, b = drawing_buffer[y, x]
                canvas.SetPixel(x, y, r, g, b)
        matrix.SwapOnVSync(canvas)
        end_time = time.time()
        return (end_time - start_time) * 1000

    # Test complex animation sequence
    print("Starting animation performance test")
    for frame in range(30):  # 30 frames
        # Clear buffer
        drawing_buffer.fill(0)
        
        # Start frame mode
        frame_mode = True
        
        # Draw a complex pattern (circle with rotating dots)
        center_x, center_y = 32, 32
        radius = 20
        angle = frame * (math.pi / 15)
        
        # Draw circle outline
        for i in range(60):
            a = i * (math.pi / 30)
            x = int(center_x + radius * math.cos(a))
            y = int(center_y + radius * math.sin(a))
            draw_dot(x, y, 255, 0, 0)
        
        # Draw rotating dots
        for i in range(8):
            a = angle + (i * math.pi / 4)
            x = int(center_x + radius * 0.7 * math.cos(a))
            y = int(center_y + radius * 0.7 * math.sin(a))
            draw_dot(x, y, 0, 255, 0)
        
        # End frame and measure time
        copy_time = end_frame()
        frame_times.append(copy_time)
        frame_mode = False
        
        # Small delay to control animation speed
        time.sleep(0.05)

    # Print performance statistics
    avg_time = sum(frame_times) / len(frame_times)
    max_time = max(frame_times)
    min_time = min(frame_times)
    print(f"\nPerformance Statistics:")
    print(f"Average frame copy time: {avg_time:.2f}ms")
    print(f"Maximum frame copy time: {max_time:.2f}ms")
    print(f"Minimum frame copy time: {min_time:.2f}ms")

if __name__ == "__main__":
    try:
        test_animation_performance()
    except KeyboardInterrupt:
        print("Exiting...")