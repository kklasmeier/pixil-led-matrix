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
        
        # Single canvas with A/B sides
        self.frame_mode_canvas = self.matrix.CreateFrameCanvas()
        self.frame_mode = False
        
        # Store current command pixels for immediate mode persistence
        self.current_command_pixels = []
        
        print("Initialization complete")

    def _draw_to_buffers(self, x: int, y: int, r: int, g: int, b: int):
        """Core pixel drawing function"""
        if 0 <= x < self.matrix.width and 0 <= y < self.matrix.height:
            print(f"Drawing pixel at ({x},{y}) color=({r},{g},{b}) frame_mode={self.frame_mode}")
            # Draw to current back side
            self.frame_mode_canvas.SetPixel(x, y, r, g, b)
            
            # In immediate mode, store for persistence
            if not self.frame_mode:
                self.current_command_pixels.append((x, y, r, g, b))

    def _maybe_swap_buffer(self):
        """Handle buffer swapping based on current mode"""
        if not self.frame_mode:
            # Immediate mode: swap and redraw for persistence
            self.frame_mode_canvas = self.matrix.SwapOnVSync(self.frame_mode_canvas)
            # Redraw stored pixels to new back side
            for x, y, r, g, b in self.current_command_pixels:
                self.frame_mode_canvas.SetPixel(x, y, r, g, b)
            # Clear stored pixels for next command
            self.current_command_pixels.clear()

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: tuple):
        """Draw a line using Bresenham's algorithm"""
        print(f"Drawing line from ({x0},{y0}) to ({x1},{y1}) color={color}")
        r, g, b = color
        
        # Clear stored pixels for new command
        self.current_command_pixels.clear()
        
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
        
        # Maybe swap buffer depending on mode
        self._maybe_swap_buffer()

    def begin_frame(self):
        """Start frame mode"""
        print("Beginning frame mode")
        self.frame_mode = True

    def end_frame(self):
        """End frame mode and display buffer"""
        if self.frame_mode:
            print("Ending frame mode - swapping buffers")
            # Swap to show frame
            self.frame_mode_canvas = self.matrix.SwapOnVSync(self.frame_mode_canvas)
            # Clear back side for next operations
            self.frame_mode_canvas.Fill(0, 0, 0)
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

def test_spiral_fill():
    print("\nTest 5: Spiral Fill Test")
    matrix = MatrixPOC()
    
    width = 64
    height = 64
    x = 0
    y = 0
    dx = 1
    dy = 0
    
    # Calculate steps needed for spiral
    steps = width * height
    boundary_x = width - 1
    boundary_y = height - 1
    boundary_left = 0
    boundary_top = 1
    
    for i in range(steps):
        # Draw current pixel
        matrix.draw_line(x, y, x, y, (255, 
                                    (i * 255) // steps,  # Fade from red to yellow
                                    0))
        
        # Move to next position
        x += dx
        y += dy
        
        # Check if we need to change direction
        if dx == 1 and x >= boundary_x:
            dx = 0
            dy = 1
            boundary_x -= 1
        elif dy == 1 and y >= boundary_y:
            dx = -1
            dy = 0
            boundary_y -= 1
        elif dx == -1 and x <= boundary_left:
            dx = 0
            dy = -1
            boundary_left += 1
        elif dy == -1 and y <= boundary_top:
            dx = 1
            dy = 0
            boundary_top += 1

def test_spiral_fill_lines():
    print("\nTest 6: Spiral Fill Lines Test")
    matrix = MatrixPOC()
    
    width = 64
    height = 64
    x = 0
    y = 0
    total_steps = width * height
    
    boundary_right = width - 1
    boundary_bottom = height - 1
    boundary_left = 0
    boundary_top = 1
    
    step_count = 0
    
    while boundary_right >= boundary_left and boundary_bottom >= boundary_top:
        # Draw top line (left to right)
        matrix.draw_line(x, y, boundary_right, y, 
                        (255, (step_count * 255) // total_steps, 0))
        step_count += boundary_right - x
        x = boundary_right
        
        # Draw right line (top to bottom)
        matrix.draw_line(x, y, x, boundary_bottom,
                        (255, (step_count * 255) // total_steps, 0))
        step_count += boundary_bottom - y
        y = boundary_bottom
        
        # Draw bottom line (right to left)
        matrix.draw_line(x, y, boundary_left, y,
                        (255, (step_count * 255) // total_steps, 0))
        step_count += x - boundary_left
        x = boundary_left
        
        # Draw left line (bottom to top)
        matrix.draw_line(x, y, x, boundary_top,
                        (255, (step_count * 255) // total_steps, 0))
        step_count += y - boundary_top
        y = boundary_top
        
        # Update boundaries for next spiral
        boundary_right -= 1
        boundary_bottom -= 1
        boundary_left += 1
        boundary_top += 1
        x = boundary_left
        y = boundary_top

def test_spiral_fill_lines_frame():
    print("\nTest 7: Spiral Fill Lines Test")
    matrix = MatrixPOC()
    
    width = 64
    height = 64
    x = 0
    y = 0
    total_steps = width * height
    
    boundary_right = width - 1
    boundary_bottom = height - 1
    boundary_left = 0
    boundary_top = 1
    
    step_count = 0
    matrix.begin_frame()
    while boundary_right >= boundary_left and boundary_bottom >= boundary_top:
        # Draw top line (left to right)
        matrix.draw_line(x, y, boundary_right, y, 
                        (255, (step_count * 255) // total_steps, 0))
        step_count += boundary_right - x
        x = boundary_right
        
        # Draw right line (top to bottom)
        matrix.draw_line(x, y, x, boundary_bottom,
                        (255, (step_count * 255) // total_steps, 0))
        step_count += boundary_bottom - y
        y = boundary_bottom
        
        # Draw bottom line (right to left)
        matrix.draw_line(x, y, boundary_left, y,
                        (255, (step_count * 255) // total_steps, 0))
        step_count += x - boundary_left
        x = boundary_left
        
        # Draw left line (bottom to top)
        matrix.draw_line(x, y, x, boundary_top,
                        (255, (step_count * 255) // total_steps, 0))
        step_count += y - boundary_top
        y = boundary_top
        
        # Update boundaries for next spiral
        boundary_right -= 1
        boundary_bottom -= 1
        boundary_left += 1
        boundary_top += 1
        x = boundary_left
        y = boundary_top

    matrix.end_frame()
    time.sleep(4)   

def test_rectangle_animation():
    print("\nTest 8: Animated Rectangle Border Tour")
    matrix = MatrixPOC()
    
    RECT_SIZE = 6
    MATRIX_SIZE = 64
    PATH_SIZE = MATRIX_SIZE - RECT_SIZE  # Maximum travel distance on each side
    MOVE_STEP = 1  # How many pixels to move per frame
    FPS = 60  # Desired frames per second
    frame_delay = 1.0 / FPS
    
    def draw_rectangle(x, y, color):
        # Draw filled 6x6 rectangle at position (x,y)
        for rx in range(RECT_SIZE):
            for ry in range(RECT_SIZE):
                matrix._draw_to_buffers(x + rx, y + ry, *color)
    
    # Calculate total frames needed for full path
    # Each side needs PATH_SIZE frames to traverse
    total_frames = PATH_SIZE * 4
    
    # Start position
    x = 0
    y = 0
    
    # Animation loop
    for frame in range(total_frames):
        matrix.begin_frame()
        
        # Calculate position based on frame number
        if frame < PATH_SIZE:  # Moving right
            x = frame
            y = 0
        elif frame < PATH_SIZE * 2:  # Moving down
            x = PATH_SIZE
            y = frame - PATH_SIZE
        elif frame < PATH_SIZE * 3:  # Moving left
            x = PATH_SIZE - (frame - PATH_SIZE * 2)
            y = PATH_SIZE
        else:  # Moving up
            x = 0
            y = PATH_SIZE - (frame - PATH_SIZE * 3)
        
        # Calculate color based on position (cycle through rainbow)
        hue = (frame * 255) // total_frames
        if hue < 85:
            color = (255 - hue * 3, hue * 3, 0)
        elif hue < 170:
            hue -= 85
            color = (0, 255 - hue * 3, hue * 3)
        else:
            hue -= 170
            color = (hue * 3, 0, 255 - hue * 3)
        
        # Draw rectangle at current position
        draw_rectangle(x, y, color)
        
        # Show frame and wait
        matrix.end_frame()
        #time.sleep(frame_delay)
    
    # Rest at the end
    print("Animation complete - resting for 3 seconds")
    time.sleep(3)

def main():
    print("RGBMatrix Drawing Mode POC")
    print("1: Test Immediate Mode")
    print("2: Test Frame Mode")
    print("3: Test Mixed Mode")
    print("4: Test Rapid Switching")
    print("5: Test Spiral Fill by pixel")
    print("6: Test Spiral Fill by lines")
    print("7: Test Spiral Fill by lines in frame mode")
    print("8: Test Animated Rectangle Border Tour")
    
    try:
        test_to_run = input("Select test (1-8): ")  
        if test_to_run == "1":
            test_immediate_mode()
        elif test_to_run == "2":
            test_frame_mode()
        elif test_to_run == "3":
            test_mixed_mode()
        elif test_to_run == "4":
            test_rapid_switching()
        elif test_to_run == "5":
            test_spiral_fill()
        elif test_to_run == "6":
            test_spiral_fill_lines()
        elif test_to_run == "7":
            test_spiral_fill_lines_frame()
        elif test_to_run == "8":
            test_rectangle_animation() 
        else:
            print("Invalid selection")
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()