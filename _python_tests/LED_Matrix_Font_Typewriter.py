from PIL import Image, ImageDraw, ImageFont
import time
from rgb_matrix_lib import execute_command

def typewriter_effect(text, font_path="/usr/share/fonts/truetype/piboto/Piboto-Regular.ttf", font_size=10):
    # Initialize font
    font = ImageFont.truetype(font_path, font_size)
    
    # Create a temporary image to measure total text width
    temp_img = Image.new('RGB', (300, 50), color=(0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    total_width, text_height = font.getsize(text)
    
    # Calculate starting x position to center the full text
    x_start = (64 - total_width) // 2
    y_position = (64 - text_height) // 2
    
    # Clear screen once at start
    execute_command("clear()")
    
    # Keep track of current text
    current_text = ""
    x_cursor = x_start
    
    # Create cursor blink state
    cursor_visible = True
    last_cursor_toggle = time.time()
    cursor_blink_interval = 0.3
    
    for char in text:
        # Add new character
        current_text += char
        
        # Create image for current text
        char_width, _ = font.getsize(char)
        
        img = Image.new('RGB', (char_width, text_height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), char, font=font, fill=(255, 255, 255))
        
        # Draw the new character with a "typing" effect
        execute_command("begin_frame")
        
        # Draw new character
        pixels = img.load()
        for y in range(text_height):
            for x in range(char_width):
                if pixels[x, y] != (0, 0, 0):
                    execute_command(f"plot({x_cursor + x}, {y_position + y}, white)")
        
        # Draw cursor at new position
        x_cursor += char_width
        for y in range(text_height):
            execute_command(f"plot({x_cursor}, {y_position + y}, cyan)")
        
        execute_command("end_frame")
        
        # Random typing delay for more natural effect
        time.sleep(0.1 + (time.time() % 0.15))
        
        # Clear cursor before next character
        execute_command("begin_frame")
        for y in range(text_height):
            execute_command(f"plot({x_cursor}, {y_position + y}, black)")
        execute_command("end_frame")
    
    # Final cursor blink effect
    blink_count = 0
    while blink_count < 6:  # Blink 3 times (on/off cycles)
        current_time = time.time()
        if current_time - last_cursor_toggle >= cursor_blink_interval:
            execute_command("begin_frame")
            for y in range(text_height):
                execute_command(f"plot({x_cursor}, {y_position + y}, cyan if cursor_visible else black)")
            execute_command("end_frame")
            
            cursor_visible = not cursor_visible
            last_cursor_toggle = current_time
            blink_count += 1
            
        time.sleep(0.05)
    
    # Clear final cursor
    execute_command("begin_frame")
    for y in range(text_height):
        execute_command(f"plot({x_cursor}, {y_position + y}, black)")
    execute_command("end_frame")

# Test the effect
if __name__ == "__main__":
    try:
        while True:
            typewriter_effect("Hello, World!")
            time.sleep(2)
            execute_command("clear()")
            time.sleep(1)
    except KeyboardInterrupt:
        execute_command("clear()")
        print("\nAnimation ended by user")