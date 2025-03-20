from PIL import Image, ImageDraw, ImageFont
import time
from rgb_matrix_lib import execute_command

def test_fonts():
    # Extended font selection
    fonts_to_test = [
        # DejaVu baseline for comparison
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf", "DejaVu Light"),
        
        # Droid fonts
        ("/usr/share/fonts/truetype/droid/DroidSans.ttf", "Droid"),
        ("/usr/share/fonts/truetype/droid/DroidSansMono.ttf", "Droid Mono"),
        
        # Liberation fonts
        ("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", "Liberation"),
        ("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf", "Liberation Mono"),
        
        # Piboto (Pi-specific)
        ("/usr/share/fonts/truetype/piboto/Piboto-Light.ttf", "Piboto Light"),
        ("/usr/share/fonts/truetype/piboto/Piboto-Regular.ttf", "Piboto"),
        
        # Quicksand
        ("/usr/share/fonts/truetype/quicksand/Quicksand-Light.ttf", "Quicksand Light"),
        
        # Free fonts
        ("/usr/share/fonts/truetype/freefont/FreeSans.ttf", "Free Sans"),
        ("/usr/share/fonts/truetype/freefont/FreeMono.ttf", "Free Mono")
    ]
    
    size = 10
    test_text = "10:30pm"
    display_time = 3  # seconds per font

    while True:  # Loop forever until interrupted
        for font_path, font_label in fonts_to_test:
            try:
                # Start frame buffering
                execute_command("begin_frame")
                
                # Clear display
                execute_command("clear()")
                
                # Load font
                font = ImageFont.truetype(font_path, size)
                
                # Get dimensions
                text_width, text_height = font.getsize(test_text)
                
                # Center text
                x_position = (64 - text_width) // 2
                y_position = 25  # Center vertically
                
                # Create and draw text
                text_img = Image.new('RGB', (text_width, text_height), color=(0, 0, 0))
                text_draw = ImageDraw.Draw(text_img)
                text_draw.text((0, 0), test_text, font=font, fill=(255, 255, 255))
                
                # Draw main text
                pixels = text_img.load()
                for y in range(text_height):
                    for x in range(text_width):
                        if pixels[x, y] != (0, 0, 0):
                            execute_command(f"plot({x_position + x}, {y_position + y}, white)")
                            
                # Add font label below
                label = f"{font_label}"
                label_width, label_height = font.getsize(label)
                label_x = (64 - label_width) // 2
                label_y = y_position + text_height + 4
                
                label_img = Image.new('RGB', (label_width, label_height), color=(0, 0, 0))
                label_draw = ImageDraw.Draw(label_img)
                label_draw.text((0, 0), label, font=font, fill=(255, 255, 255))
                
                label_pixels = label_img.load()
                for y in range(label_height):
                    for x in range(label_width):
                        if label_pixels[x, y] != (0, 0, 0):
                            execute_command(f"plot({label_x + x}, {label_y + y}, cyan)")
                
                # End frame buffering
                execute_command("end_frame")
                
                # Display duration
                time.sleep(display_time)
                
            except Exception as e:
                print(f"Error with font {font_label}: {str(e)}")
                continue

if __name__ == "__main__":
    try:
        test_fonts()
    except KeyboardInterrupt:
        execute_command("clear()")
        print("\nTest ended by user")