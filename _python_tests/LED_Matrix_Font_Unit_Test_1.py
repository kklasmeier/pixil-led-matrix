# test_text_rendering.py
import time
from rgb_matrix_lib import execute_command
from rgb_matrix_lib.fonts import get_font_manager, FontError
from rgb_matrix_lib.text_renderer import TextRenderer
from rgb_matrix_lib.text_effects import TextEffect, EffectModifier

def test_font_system():
    print("\nTesting Font System:")
    print("-" * 50)
    manager = get_font_manager()
    print("Available fonts:", manager.list_available_fonts())
    
    try:
        # Test loading a known font
        font = manager.get_font("piboto-regular", 12)
        print("Successfully loaded Piboto Regular")
        
        # Test loading non-existent font
        try:
            font = manager.get_font("nonexistent-font", 12)
        except FontError as e:
            print("Correctly caught font error:", str(e))
    except Exception as e:
        print("Unexpected error:", str(e))

def test_basic_rendering():
    print("\nTesting Basic Text Rendering:")
    print("-" * 50)
    renderer = TextRenderer()
    
    try:
        # Clear display
        execute_command("clear()")
        
        print("Drawing text...")
        renderer.render_text(10, 20, "Test Text", "piboto-regular", 12, "white")
        time.sleep(3)
        
        print("Clearing text...")
        renderer.clear_text(10, 20)
        time.sleep(1)
        
    except Exception as e:
        print("Rendering error:", str(e))

def test_multiple_areas():
    print("\nTesting Multiple Text Areas:")
    print("-" * 50)
    renderer = TextRenderer()
    
    try:
        # Clear display
        execute_command("clear()")
        
        print("Drawing multiple text areas...")
        renderer.render_text(5, 10, "Area 1", "piboto-regular", 12, "red")
        renderer.render_text(5, 30, "Area 2", "piboto-regular", 12, "blue")
        time.sleep(3)
        
        print("Clearing Area 1...")
        renderer.clear_text(5, 10)
        time.sleep(2)
        
        print("Clearing Area 2...")
        renderer.clear_text(5, 30)
        
    except Exception as e:
        print("Multiple areas error:", str(e))

def test_bounds_tracking():
    test_typewriter_effect()
    print("\nTests completed")
    print("\nTesting Bounds Tracking:")
    print("-" * 50)
    renderer = TextRenderer()
    
    try:
        # Clear display
        execute_command("clear()")
        
        # Draw text and check bounds
        renderer.render_text(10, 20, "Test", "piboto-regular", 12, "white")
        bounds = renderer.get_text_bounds(10, 20)
        if bounds:
            print(f"Text bounds: x={bounds.x}, y={bounds.y}, width={bounds.width}, height={bounds.height}")
        
        time.sleep(2)
        renderer.clear_text(10, 20)
        
        # Verify bounds are cleared
        if not renderer.get_text_bounds(10, 20):
            print("Bounds successfully cleared")
        
    except Exception as e:
        print("Bounds tracking error:", str(e))

def test_typewriter_effect():
    print("\nTesting Typewriter Effect:")
    print("-" * 50)
    renderer = TextRenderer()
    
    try:
        # Clear display
        execute_command("clear()")
        
        # Test different speeds
        print("Testing SLOW speed...")
        renderer.render_text(5, 10, "Slow Type", "piboto-regular", 12, "white", 
                           TextEffect.TYPE, EffectModifier.SLOW)
        time.sleep(1)
        renderer.clear_text(5, 10)
        
        print("Testing MEDIUM speed...")
        renderer.render_text(5, 25, "Medium Type", "piboto-regular", 12, "white", 
                           TextEffect.TYPE, EffectModifier.MEDIUM)
        time.sleep(1)
        renderer.clear_text(5, 25)
        
        print("Testing FAST speed...")
        renderer.render_text(5, 40, "Fast Type", "piboto-regular", 12, "white", 
                           TextEffect.TYPE, EffectModifier.FAST)
        time.sleep(1)
        renderer.clear_text(5, 40)
        
    except Exception as e:
        print("Typewriter effect error:", str(e))
    finally:
        time.sleep(1)
        execute_command("clear()")

if __name__ == "__main__":
    try:
        test_typewriter_effect()
        print("\nTests completed")

        test_font_system()
        time.sleep(1)
        
        test_basic_rendering()
        time.sleep(1)
        
        test_multiple_areas()
        time.sleep(1)
        
        test_bounds_tracking()
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    finally:
        execute_command("clear()")
        print("\nTests completed")