from PIL import Image, ImageDraw, ImageFont
import time
import math
from rgb_matrix_lib import execute_command

def wipe_effect(text, direction="left", font_path="/usr/share/fonts/truetype/piboto/Piboto-Regular.ttf", font_size=10):
    # Initialize font
    font = ImageFont.truetype(font_path, font_size)
    
    # Get text dimensions
    text_width, text_height = font.getsize(text)
    
    # Create image with text
    img = Image.new('RGB', (text_width, text_height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), text, font=font, fill=(255, 255, 255))
    
    # Calculate centered position
    x_start = (64 - text_width) // 2
    y_start = (64 - text_height) // 2
    
    # Get all lit pixels with their positions
    pixels = img.load()
    lit_pixels = []
    for y in range(text_height):
        for x in range(text_width):
            if pixels[x, y] != (0, 0, 0):
                lit_pixels.append((x + x_start, y + y_start))
    
    # Clear screen at start
    execute_command("clear()")
    
    # Sort pixels based on direction for wipe effect
    if direction == "left":
        lit_pixels.sort(key=lambda p: p[0])  # Sort by x coordinate
    elif direction == "right":
        lit_pixels.sort(key=lambda p: -p[0])  # Sort by negative x
    elif direction == "top":
        lit_pixels.sort(key=lambda p: p[1])  # Sort by y coordinate
    elif direction == "bottom":
        lit_pixels.sort(key=lambda p: -p[1])  # Sort by negative y
    elif direction == "diagonal":
        lit_pixels.sort(key=lambda p: p[0] + p[1])  # Sort by sum of coordinates
    
    # Animation parameters
    total_frames = 30
    pixels_per_frame = max(1, len(lit_pixels) // total_frames)
    
    # Wipe In
    revealed_pixels = set()
    for i in range(0, len(lit_pixels), pixels_per_frame):
        execute_command("begin_frame")
        
        # Get next batch of pixels
        new_pixels = lit_pixels[i:i + pixels_per_frame]
        
        # Draw new pixels
        for x, y in new_pixels:
            execute_command(f"plot({x}, {y}, white)")
            revealed_pixels.add((x, y))
            
        execute_command("end_frame")
        time.sleep(0.02)
    
    # Hold complete text
    time.sleep(1)
    
    # Wipe Out (reverse direction)
    remaining_pixels = list(revealed_pixels)
    if direction == "left":
        remaining_pixels.sort(key=lambda p: -p[0])  # Reverse sort
    elif direction == "right":
        remaining_pixels.sort(key=lambda p: p[0])
    elif direction == "top":
        remaining_pixels.sort(key=lambda p: -p[1])
    elif direction == "bottom":
        remaining_pixels.sort(key=lambda p: p[1])
    elif direction == "diagonal":
        remaining_pixels.sort(key=lambda p: -(p[0] + p[1]))
    
    for i in range(0, len(remaining_pixels), pixels_per_frame):
        execute_command("begin_frame")
        
        # Get next batch of pixels to remove
        pixels_to_remove = remaining_pixels[i:i + pixels_per_frame]
        
        # Clear pixels
        for x, y in pixels_to_remove:
            execute_command(f"plot({x}, {y}, black)")
            
        execute_command("end_frame")
        time.sleep(0.02)

# Test different wipe directions
if __name__ == "__main__":
    try:
        directions = ["left", "right", "top", "bottom", "diagonal"]
        while True:
            for direction in directions:
                wipe_effect(f"WIPE {direction}", direction)
                time.sleep(0.5)
    except KeyboardInterrupt:
        execute_command("clear()")
        print("\nAnimation ended by user")