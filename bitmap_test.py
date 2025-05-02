# File: test_bitmap_font.py
import time 
# Import the necessary modules
from rgb_matrix_lib.api import get_api_instance

def main():
    # Get the API instance
    api = get_api_instance()
    
    # Clear the display
    api.clear()
    
    # Test regular font
    # api.draw_text(2, 2, "Hello", "piboto-regular", 8, "red", 100)
    
    # Test bitmap font with normal effect
    api.draw_text(2, 1, "! @ # $ % ^ & * (  )", "tiny64_font", 5, green, 100)
    api.draw_text(2, 7, "_ + - = { } | [ ] ", "tiny64_font", 5, green, 100)
    api.draw_text(2, 13, ": ; ' < > ? , . /", "tiny64_font", 5, green, 100)
    api.draw_text(2, 19, "!@#$%^&*()_+{}|[]\:", "tiny64_font", 5, green, 100)
    api.draw_text(2, 25, "'<>?,./1234567890", "tiny64_font", 5, green, 100)
    time.sleep(2)
    # Test bitmap font with TYPE effect
    api.draw_text(2, 25, "Type...", "tiny64_font", 5, "blue", 100, "TYPE", "MEDIUM")
    time.sleep(2)
    
    # Test bitmap font with other effects
    api.draw_text(2, 35, "Slide", "tiny64_font", 5, "yellow", 100, "SLIDE", "LEFT")
    time.sleep(2)

    #api.draw_text(2, 45, "g,j,p,q,y", "tiny64_font", 5, "purple", 100)  # Test descenders
    #time.sleep(2)
    
    # Wait for 10 seconds
    api.rest(10)
    
    # Clear the display
    api.clear()

if __name__ == "__main__":
    main()