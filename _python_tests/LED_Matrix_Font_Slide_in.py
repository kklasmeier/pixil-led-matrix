from PIL import Image, ImageDraw, ImageFont
import time
import math
from rgb_matrix_lib import execute_command

def ease_in_out(t):
    return 0.5 * (1 - math.cos(math.pi * t))

def slide_in_effect(text, direction="left", font_path="/usr/share/fonts/truetype/piboto/Piboto-Regular.ttf", font_size=10):
    # Initialize font
    font = ImageFont.truetype(font_path, font_size)
    
    # Get text dimensions
    text_width, text_height = font.getsize(text)
    
    # Create image with text
    img = Image.new('RGB', (text_width, text_height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), text, font=font, fill=(255, 255, 255))
    
    # Calculate final position (centered)
    final_x = (64 - text_width) // 2
    final_y = (64 - text_height) // 2
    
    # Set up starting position based on direction
    if direction == "left":
        start_x = -text_width
        start_y = final_y
    elif direction == "right":
        start_x = 64
        start_y = final_y
    elif direction == "top":
        start_x = final_x
        start_y = -text_height
    else:  # bottom
        start_x = final_x
        start_y = 64
    
    # Animation parameters
    duration = 1.0  # seconds
    frames = 40  # total animation frames
    
    # Get text pixels once
    pixels = img.load()
    lit_pixels = []
    for y in range(text_height):
        for x in range(text_width):
            if pixels[x, y] != (0, 0, 0):
                lit_pixels.append((x, y))
    
    # Clear screen at start
    execute_command("clear()")
    
    # Keep track of currently active pixels
    active_pixels = set()

    # Animation loop
    for frame in range(frames + 1):
        execute_command("begin_frame")
        
        # Calculate new position
        progress = frame / frames
        eased_progress = ease_in_out(progress)
        
        current_x = int(start_x + (final_x - start_x) * eased_progress)
        current_y = int(start_y + (final_y - start_y) * eased_progress)
        
        # Calculate new pixel positions
        new_active_pixels = set()
        for x, y in lit_pixels:
            plot_x = current_x + x
            plot_y = current_y + y
            if 0 <= plot_x < 64 and 0 <= plot_y < 64:
                new_active_pixels.add((plot_x, plot_y))
        
        # Clear pixels that are no longer active
        pixels_to_clear = active_pixels - new_active_pixels
        for x, y in pixels_to_clear:
            execute_command(f"plot({x}, {y}, black)")
        
        # Draw new pixels
        pixels_to_draw = new_active_pixels - active_pixels
        for x, y in pixels_to_draw:
            execute_command(f"plot({x}, {y}, white)")
        
        # Update active pixels for next frame
        active_pixels = new_active_pixels
        
        execute_command("end_frame")
        time.sleep(duration / frames)

# Test different slide directions
if __name__ == "__main__":
    try:
        while True:
            directions = ["left", "right", "top", "bottom"]
            for direction in directions:
                slide_in_effect(f"Slide {direction}", direction)
                time.sleep(1)
                execute_command("clear()")
                time.sleep(0.5)
    except KeyboardInterrupt:
        execute_command("clear()")
        print("\nAnimation ended by user")