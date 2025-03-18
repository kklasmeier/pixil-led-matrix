from PIL import Image, ImageDraw, ImageFont
import time
import random
from rgb_matrix_lib import execute_command

def create_matrix_effect(text, font_path="/usr/share/fonts/truetype/piboto/Piboto-Regular.ttf", font_size=10):
    # Initialize font
    font = ImageFont.truetype(font_path, font_size)
    
    # Create separate image for each character
    char_images = []
    total_width = 0
    max_height = 0
    
    # Process each character
    for char in text:
        width, height = font.getsize(char)
        img = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), char, font=font, fill=(255, 255, 255))
        char_images.append((img, width, height))
        total_width += width
        max_height = max(max_height, height)
    
    # Calculate starting positions for each character
    x_start = (64 - total_width) // 2
    x_positions = []
    current_x = x_start
    for _, width, _ in char_images:
        x_positions.append(current_x)
        current_x += width
    
    # Initialize character states
    char_states = []
    for i, (img, width, height) in enumerate(char_images):
        delay = i * 5  # Stagger the start of each character
        char_states.append({
            'image': img,
            'width': width,
            'height': height,
            'y': -height,  # Start above screen
            'x': x_positions[i],
            'delay': delay,
            'trail': [],  # Will store trail positions and intensities
            'active_pixels': set()  # Track currently lit pixels
        })
    
    # Clear screen once at start
    execute_command("clear()")
    
    # Animation loop
    frame = 0
    while True:
        execute_command("begin_frame")
        
        all_completed = True
        
        for state in char_states:
            # Clear previous pixels for this character
            for x, y in state['active_pixels']:
                execute_command(f"plot({x}, {y}, black)")
            state['active_pixels'].clear()
            
            if frame >= state['delay']:
                # Update trail first
                new_trail = []
                for trail_y, intensity in state['trail']:
                    # Fade the trail
                    new_intensity = intensity - 10
                    if new_intensity > 0:
                        new_trail.append((trail_y, new_intensity))
                
                # Draw trails
                for trail_y, intensity in new_trail:
                    pixels = state['image'].load()
                    for y in range(state['height']):
                        for x in range(state['width']):
                            if pixels[x, y] != (0, 0, 0):
                                px, py = state['x'] + x, trail_y + y
                                if 0 <= py < 64:  # Check vertical bounds
                                    execute_command(f"plot({px}, {py}, green:{intensity})")
                                    state['active_pixels'].add((px, py))
                
                # Update and draw current character
                if state['y'] < 32:  # Screen height/2
                    # Add current position to trail
                    new_trail.append((state['y'], 100))
                    state['trail'] = new_trail
                    
                    # Draw current character
                    pixels = state['image'].load()
                    for y in range(state['height']):
                        for x in range(state['width']):
                            if pixels[x, y] != (0, 0, 0):
                                px, py = state['x'] + x, state['y'] + y
                                if 0 <= py < 64:  # Check vertical bounds
                                    execute_command(f"plot({px}, {py}, green:100)")
                                    state['active_pixels'].add((px, py))
                    
                    # Move character down
                    state['y'] += 1
                    all_completed = False
                else:
                    # Character has reached final position
                    pixels = state['image'].load()
                    for y in range(state['height']):
                        for x in range(state['width']):
                            if pixels[x, y] != (0, 0, 0):
                                px, py = state['x'] + x, state['y'] + y
                                execute_command(f"plot({px}, {py}, green:100)")
                                state['active_pixels'].add((px, py))
        
        execute_command("end_frame")
        
        if all_completed and not any(state['trail'] for state in char_states):
            break
            
        frame += 1
        time.sleep(0.05)  # Control animation speed

# Test the effect
if __name__ == "__main__":
    try:
        while True:
            create_matrix_effect("MATRIX")
            time.sleep(2)  # Pause between animations
            execute_command("clear()")
            time.sleep(1)  # Pause before restart
    except KeyboardInterrupt:
        execute_command("clear()")
        print("\nAnimation ended by user")