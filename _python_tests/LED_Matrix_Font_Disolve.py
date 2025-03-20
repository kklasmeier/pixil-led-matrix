from PIL import Image, ImageDraw, ImageFont
import time
import random
from rgb_matrix_lib import execute_command

def disolve_effect(text, font_path="/usr/share/fonts/truetype/piboto/Piboto-Regular.ttf", font_size=10):
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
    
    # Get list of all lit pixels
    pixels = img.load()
    lit_pixels = []
    for y in range(text_height):
        for x in range(text_width):
            if pixels[x, y] != (0, 0, 0):
                lit_pixels.append((x + x_start, y + y_start))
    
    # Clear screen at start
    execute_command("clear()")
    
    # Disolve In
    remaining_pixels = lit_pixels.copy()
    active_pixels = set()
    
    while remaining_pixels:
        execute_command("begin_frame")
        
        # Add random pixels
        num_pixels = min(len(remaining_pixels), 5)  # Add 5 pixels per frame
        for _ in range(num_pixels):
            if remaining_pixels:
                idx = random.randint(0, len(remaining_pixels) - 1)
                x, y = remaining_pixels.pop(idx)
                execute_command(f"plot({x}, {y}, white)")
                active_pixels.add((x, y))
        
        execute_command("end_frame")
        time.sleep(0.02)
    
    # Hold the complete text
    time.sleep(2)
    
    # Disolve Out
    remaining_pixels = list(active_pixels)
    
    while remaining_pixels:
        execute_command("begin_frame")
        
        # Remove random pixels
        num_pixels = min(len(remaining_pixels), 5)  # Remove 5 pixels per frame
        for _ in range(num_pixels):
            if remaining_pixels:
                idx = random.randint(0, len(remaining_pixels) - 1)
                x, y = remaining_pixels.pop(idx)
                execute_command(f"plot({x}, {y}, black)")
        
        execute_command("end_frame")
        time.sleep(0.02)

# Test the effect
if __name__ == "__main__":
    try:
        while True:
            disolve_effect("DISSOLVE")
            time.sleep(1)
    except KeyboardInterrupt:
        execute_command("clear()")
        print("\nAnimation ended by user")