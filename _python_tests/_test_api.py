# File: _test_api.py (place in /home/pi/Lightshow/current/)
from rgb_matrix_lib.api import RGB_Api
from rgb_matrix_lib.debug import configure_debug, Level
import time

# Configure debug logging
configure_debug(level=Level.DEBUG)

api = RGB_Api()

# Clear the display
api.clear()

# Test basic drawing commands
api.plot(10, 10, "red")                    # Red dot, full intensity
api.plot(20, 20, "blue", 2)               
api.plot(22, 20, "blue", 10)              
api.plot(24, 20, "blue", 15)              
api.plot(26, 20, "blue", 20)             
api.plot(26, 20, "blue", 100)             
api.plot(28, 20, "blue")             
#api.plot(23, 20, "blue", 50, 1000)               # Blue dot, 50% intensity with 1000ms duration
#api.draw_line(0, 0, 63, 63, "green", 75)   # Green diagonal, 75% intensity
#api.draw_rectangle(40, 40, 10, 10, "yellow", 60, True)  # Filled yellow rectangle, 60% intensity
#api.draw_circle(32, 32, 5, "purple")       # Purple circle, full intensity
#api.draw_polygon(32, 10, 8, 6, 45, 80, 0, False)  # Hexagon, spectral 45, 80% intensity

# Test text drawing
#api.draw_text(10, 50, "Hi", "piboto-regular", 12, "cyan")  # Cyan text, full intensity
#api.draw_text(30, 50, "Test", "piboto-regular", 12, "orange", 50, "TYPE", "SLOW")  # Orange text, 50%, typewriter effect

# Test sprite drawing
#api.sprite_manager.create_sprite("sprite1", 10, 10)  # Define a 10x10 sprite
#api.draw_to_sprite("sprite1", "draw_circle", 5, 5, 3, "red", 25, True)  # Red filled circle, 75% intensity
#api.show_sprite("sprite1", 15, 15)  
#time.sleep(1)  # Wait to observe
#api.move_sprite("sprite1", 18, 15)  
#time.sleep(1)  # Wait to observe
#api.move_sprite("sprite1", 20, 15)  
#time.sleep(1)  # Wait to observe
#api.move_sprite("sprite1", 22, 15)  
#time.sleep(1)  # Wait to observe
#api.move_sprite("sprite1", 24, 18)  
#time.sleep(1)  # Wait to observe
#api.move_sprite("sprite1", 26, 20)  
#time.sleep(1)  # Wait to observe
#api.move_sprite("sprite1", 28, 22)  
#time.sleep(1)  # Wait to observe
#api.move_sprite("sprite1", 32, 20)  
#time.sleep(1)  # Wait to observe
#api.move_sprite("sprite1", 35, 18)  

# Wait to observe
time.sleep(10)  # Longer to see all effects

# Cleanup
api.cleanup()