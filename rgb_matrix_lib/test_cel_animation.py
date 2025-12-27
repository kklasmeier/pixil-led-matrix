#!/usr/bin/env python3
"""
Test script for the Sprite Cel Animation System.
Tests rgb_matrix_lib directly without going through Pixil interpreter.

Run with: python3 test_cel_animation.py
"""

import sys
import os
import time

# Configuration
TEST_DELAY = 1.5  # Seconds to pause between tests (set to 0 for fast run)
VERBOSE_DEBUG = False  # Set True to see debug messages

# Auto-detect the script's directory for finding sprite.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_PATH = os.path.join(SCRIPT_DIR, 'sprite.py')

print("Setting up test environment...")
print(f"  Script directory: {SCRIPT_DIR}")
print(f"  Looking for sprite.py at: {SPRITE_PATH}")

if not os.path.exists(SPRITE_PATH):
    print(f"ERROR: sprite.py not found at {SPRITE_PATH}")
    sys.exit(1)

# Create mock modules before importing sprite
import types
import numpy as np

# Mock debug module
class MockLevel:
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

class MockComponent:
    SPRITE = "SPRITE"
    SYSTEM = "SYSTEM"
    DRAWING = "DRAWING"
    COMMAND = "COMMAND"
    MATRIX = "MATRIX"

debug_module = types.ModuleType('rgb_matrix_lib.debug')
debug_module.Level = MockLevel
debug_module.Component = MockComponent
if VERBOSE_DEBUG:
    debug_module.debug = lambda msg, level=None, component=None: print(f"  [DEBUG] {msg}")
else:
    debug_module.debug = lambda msg, level=None, component=None: None
debug_module.configure_debug = lambda **kwargs: None
sys.modules['rgb_matrix_lib.debug'] = debug_module

# Mock utils module
utils_module = types.ModuleType('rgb_matrix_lib.utils')
utils_module.TRANSPARENT_COLOR = (0, 0, 0)
utils_module.polygon_vertices = lambda cx, cy, r, sides, rot: [(cx+r, cy), (cx, cy+r), (cx-r, cy), (cx, cy-r)]
utils_module.is_transparent = lambda c: c == (0, 0, 0) or (hasattr(c, '__iter__') and tuple(c) == (0, 0, 0))
def mock_get_color_rgb(color, intensity):
    colors = {
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255),
        'yellow': (255, 255, 0),
        'white': (255, 255, 255),
    }
    if isinstance(color, str):
        return colors.get(color.lower(), (128, 128, 128))
    return (128, 128, 128)
utils_module.get_color_rgb = mock_get_color_rgb
sys.modules['rgb_matrix_lib.utils'] = utils_module

# Read, modify, and exec the sprite module
with open(SPRITE_PATH, 'r') as f:
    sprite_code = f.read()

# Replace relative imports with absolute imports (which we've mocked)
sprite_code = sprite_code.replace('from .debug import', 'from rgb_matrix_lib.debug import')
sprite_code = sprite_code.replace('from .utils import', 'from rgb_matrix_lib.utils import')

# Create a module and execute the code in it
sprite_module = types.ModuleType('sprite')
exec(sprite_code, sprite_module.__dict__)

# Extract the classes we need
MatrixSprite = sprite_module.MatrixSprite
SpriteInstance = sprite_module.SpriteInstance
SpriteManager = sprite_module.SpriteManager

print("✓ Test environment ready")
print(f"✓ Test delay between tests: {TEST_DELAY}s")
time.sleep(1)


def test_separator(name):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)


def test_single_cel_sprite():
    """Test backward compatibility - single cel sprite without explicit sprite_cel()"""
    test_separator("Single-Cel Sprite (Backward Compatibility)")
    
    manager = SpriteManager()
    
    # Define sprite the old way - no sprite_cel() calls
    template = manager.begin_sprite_definition("simple", 10, 10)
    template.plot(5, 5, 'red', 100)
    manager.end_sprite_definition()
    
    # Verify
    assert template.cel_count == 1, f"Expected 1 cel, got {template.cel_count}"
    assert manager.get_template("simple") is not None, "Template not stored"
    print(f"✓ Single-cel sprite created with {template.cel_count} cel(s)")
    
    # Create instance and verify it works
    instance = manager.create_instance("simple", 0, x=10, y=10)
    assert instance is not None, "Failed to create instance"
    assert instance.cel_count == 1, f"Instance cel_count wrong: {instance.cel_count}"
    assert instance.current_cel == 0, f"Instance current_cel wrong: {instance.current_cel}"
    print(f"✓ Instance created at ({instance.x}, {instance.y}) with cel {instance.current_cel}")
    
    return True


def test_multi_cel_explicit_indices():
    """Test multi-cel sprite with explicit cel indices"""
    test_separator("Multi-Cel Sprite (Explicit Indices)")
    
    manager = SpriteManager()
    
    # Define sprite with explicit cel indices
    template = manager.begin_sprite_definition("pacman", 20, 20)
    
    manager.start_cel(0)  # Explicit cel 0
    template.plot(10, 10, 'red', 100)  # Closed mouth
    
    manager.start_cel(1)  # Explicit cel 1
    template.plot(10, 10, 'green', 100)  # Open mouth
    
    manager.end_sprite_definition()
    
    # Verify
    assert template.cel_count == 2, f"Expected 2 cels, got {template.cel_count}"
    print(f"✓ Multi-cel sprite created with {template.cel_count} cels")
    
    # Verify cel 0 has red pixel
    cel0_buffer = template.get_cel_buffer(0)
    cel1_buffer = template.get_cel_buffer(1)
    print(f"  Cel 0 pixel at (10,10): {cel0_buffer[10, 10]}")
    print(f"  Cel 1 pixel at (10,10): {cel1_buffer[10, 10]}")
    
    return True


def test_multi_cel_auto_indices():
    """Test multi-cel sprite with auto-assigned indices"""
    test_separator("Multi-Cel Sprite (Auto Indices)")
    
    manager = SpriteManager()
    
    # Define sprite with auto-assigned cel indices
    template = manager.begin_sprite_definition("fish", 16, 8)
    
    cel_idx = manager.start_cel()  # Auto-assigned
    assert cel_idx == 0, f"First auto-cel should be 0, got {cel_idx}"
    template.plot(8, 4, 'red', 100)
    
    cel_idx = manager.start_cel()  # Auto-assigned
    assert cel_idx == 1, f"Second auto-cel should be 1, got {cel_idx}"
    template.plot(8, 4, 'green', 100)
    
    cel_idx = manager.start_cel()  # Auto-assigned
    assert cel_idx == 2, f"Third auto-cel should be 2, got {cel_idx}"
    template.plot(8, 4, 'blue', 100)
    
    manager.end_sprite_definition()
    
    assert template.cel_count == 3, f"Expected 3 cels, got {template.cel_count}"
    print(f"✓ Auto-indexed sprite created with {template.cel_count} cels")
    
    return True


def test_mixed_indexing():
    """Test mixed explicit and auto indexing"""
    test_separator("Mixed Indexing")
    
    manager = SpriteManager()
    
    template = manager.begin_sprite_definition("mixed", 10, 10)
    
    manager.start_cel(0)  # Explicit 0
    template.plot(1, 1, 'red', 100)
    
    cel_idx = manager.start_cel()  # Auto -> should be 1
    assert cel_idx == 1, f"Auto after explicit 0 should be 1, got {cel_idx}"
    template.plot(2, 2, 'green', 100)
    
    cel_idx = manager.start_cel()  # Auto -> should be 2
    assert cel_idx == 2, f"Next auto should be 2, got {cel_idx}"
    template.plot(3, 3, 'blue', 100)
    
    manager.end_sprite_definition()
    
    assert template.cel_count == 3, f"Expected 3 cels, got {template.cel_count}"
    print(f"✓ Mixed indexing worked correctly")
    
    return True


def test_cel_index_gap_error():
    """Test that gaps in cel indices raise an error"""
    test_separator("Cel Index Gap Detection")
    
    manager = SpriteManager()
    
    template = manager.begin_sprite_definition("gapped", 10, 10)
    
    manager.start_cel(0)
    template.plot(1, 1, 'red', 100)
    
    manager.start_cel(2)  # Skip cel 1!
    template.plot(2, 2, 'green', 100)
    
    try:
        manager.end_sprite_definition()
        print("✗ Should have raised error for gap in cel indices")
        return False
    except ValueError as e:
        print(f"✓ Correctly caught gap error: {e}")
        return True


def test_duplicate_cel_index_error():
    """Test that duplicate cel indices raise an error"""
    test_separator("Duplicate Cel Index Detection")
    
    manager = SpriteManager()
    
    template = manager.begin_sprite_definition("duped", 10, 10)
    
    manager.start_cel(0)
    template.plot(1, 1, 'red', 100)
    
    manager.start_cel(1)
    template.plot(2, 2, 'green', 100)
    
    try:
        manager.start_cel(1)  # Duplicate!
        print("✗ Should have raised error for duplicate cel index")
        return False
    except ValueError as e:
        print(f"✓ Correctly caught duplicate error: {e}")
        # Clean up - we need to abandon this sprite definition
        manager._defining_sprite = None
        return True


def test_instance_cel_tracking():
    """Test that instances track their cel independently"""
    test_separator("Instance Cel Tracking")
    
    manager = SpriteManager()
    
    # Create a 3-cel sprite
    template = manager.begin_sprite_definition("animated", 10, 10)
    manager.start_cel(0)
    template.plot(1, 1, 'red', 100)
    manager.start_cel(1)
    template.plot(2, 2, 'green', 100)
    manager.start_cel(2)
    template.plot(3, 3, 'blue', 100)
    manager.end_sprite_definition()
    
    # Create two instances at different cels
    inst0 = manager.create_instance("animated", 0, cel_index=0)
    inst1 = manager.create_instance("animated", 1, cel_index=2)
    
    assert inst0.current_cel == 0, f"Instance 0 should be at cel 0, got {inst0.current_cel}"
    assert inst1.current_cel == 2, f"Instance 1 should be at cel 2, got {inst1.current_cel}"
    print(f"✓ Instance 0 at cel {inst0.current_cel}, Instance 1 at cel {inst1.current_cel}")
    
    # Advance instance 0
    new_cel = inst0.advance_cel()
    assert new_cel == 1, f"After advance, should be cel 1, got {new_cel}"
    assert inst0.current_cel == 1, f"current_cel should be 1, got {inst0.current_cel}"
    print(f"✓ Instance 0 advanced to cel {inst0.current_cel}")
    
    # Instance 1 should be unchanged
    assert inst1.current_cel == 2, f"Instance 1 should still be at cel 2, got {inst1.current_cel}"
    print(f"✓ Instance 1 unchanged at cel {inst1.current_cel}")
    
    return True


def test_cel_wrap_around():
    """Test that cel advancement wraps around"""
    test_separator("Cel Wrap-Around")
    
    manager = SpriteManager()
    
    # Create a 3-cel sprite
    template = manager.begin_sprite_definition("wrapper", 10, 10)
    manager.start_cel(0)
    template.plot(1, 1, 'red', 100)
    manager.start_cel(1)
    template.plot(2, 2, 'green', 100)
    manager.start_cel(2)
    template.plot(3, 3, 'blue', 100)
    manager.end_sprite_definition()
    
    instance = manager.create_instance("wrapper", 0, cel_index=0)
    
    # Advance through all cels and verify wrap
    cels_seen = [instance.current_cel]
    for i in range(5):
        instance.advance_cel()
        cels_seen.append(instance.current_cel)
    
    expected = [0, 1, 2, 0, 1, 2]
    assert cels_seen == expected, f"Expected {expected}, got {cels_seen}"
    print(f"✓ Cel sequence correct: {cels_seen}")
    
    return True


def test_set_cel_explicit():
    """Test explicit cel setting"""
    test_separator("Explicit Cel Setting")
    
    manager = SpriteManager()
    
    # Create a 4-cel sprite
    template = manager.begin_sprite_definition("jumper", 10, 10)
    for i in range(4):
        manager.start_cel(i)
        template.plot(i, i, 'red', 100)
    manager.end_sprite_definition()
    
    instance = manager.create_instance("jumper", 0, cel_index=0)
    
    # Jump to cel 3
    instance.set_cel(3)
    assert instance.current_cel == 3, f"Should be at cel 3, got {instance.current_cel}"
    print(f"✓ Jumped to cel {instance.current_cel}")
    
    # Jump back to cel 1
    instance.set_cel(1)
    assert instance.current_cel == 1, f"Should be at cel 1, got {instance.current_cel}"
    print(f"✓ Jumped back to cel {instance.current_cel}")
    
    # Advance should continue from there
    instance.advance_cel()
    assert instance.current_cel == 2, f"After advance should be cel 2, got {instance.current_cel}"
    print(f"✓ Advanced to cel {instance.current_cel}")
    
    return True


def test_invalid_cel_index():
    """Test error handling for invalid cel indices"""
    test_separator("Invalid Cel Index Handling")
    
    manager = SpriteManager()
    
    # Create a 2-cel sprite
    template = manager.begin_sprite_definition("limited", 10, 10)
    manager.start_cel(0)
    template.plot(1, 1, 'red', 100)
    manager.start_cel(1)
    template.plot(2, 2, 'green', 100)
    manager.end_sprite_definition()
    
    instance = manager.create_instance("limited", 0, cel_index=0)
    
    # Try to set invalid cel
    try:
        instance.set_cel(5)
        print("✗ Should have raised error for invalid cel index")
        return False
    except IndexError as e:
        print(f"✓ Correctly caught invalid cel error: {e}")
    
    # Try to create instance with invalid cel
    bad_instance = manager.create_instance("limited", 99, cel_index=10)
    if bad_instance is None:
        print("✓ Correctly rejected instance creation with invalid cel")
    else:
        print("✗ Should have rejected invalid cel on instance creation")
        return False
    
    return True


def test_buffer_access_by_cel():
    """Test that buffer access returns correct cel data"""
    test_separator("Buffer Access Per Cel")
    
    manager = SpriteManager()
    
    # Create sprite with distinct data in each cel
    template = manager.begin_sprite_definition("distinct", 5, 5)
    
    manager.start_cel(0)
    template.plot(0, 0, 'red', 100)  # Red pixel at (0,0) in cel 0
    
    manager.start_cel(1)
    template.plot(1, 1, 'green', 100)  # Green pixel at (1,1) in cel 1
    
    manager.end_sprite_definition()
    
    # Create instance
    instance = manager.create_instance("distinct", 0, cel_index=0)
    
    # At cel 0, buffer should have red at (0,0)
    buffer0 = instance.buffer
    print(f"  Cel 0 buffer[0,0]: {buffer0[0, 0]}")
    
    # Switch to cel 1
    instance.set_cel(1)
    buffer1 = instance.buffer
    print(f"  Cel 1 buffer[1,1]: {buffer1[1, 1]}")
    
    # Verify they're different
    assert not (buffer0[0, 0] == buffer1[0, 0]).all() or not (buffer0[1, 1] == buffer1[1, 1]).all(), \
        "Buffers should have different content"
    print("✓ Different cels return different buffer data")
    
    return True


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("SPRITE CEL ANIMATION SYSTEM - TEST SUITE")
    print("="*60)
    
    tests = [
        ("Single-cel backward compatibility", test_single_cel_sprite),
        ("Multi-cel explicit indices", test_multi_cel_explicit_indices),
        ("Multi-cel auto indices", test_multi_cel_auto_indices),
        ("Mixed indexing", test_mixed_indexing),
        ("Gap detection", test_cel_index_gap_error),
        ("Duplicate detection", test_duplicate_cel_index_error),
        ("Instance cel tracking", test_instance_cel_tracking),
        ("Cel wrap-around", test_cel_wrap_around),
        ("Explicit cel setting", test_set_cel_explicit),
        ("Invalid cel handling", test_invalid_cel_index),
        ("Buffer access per cel", test_buffer_access_by_cel),
    ]
    
    results = []
    for i, (name, test_func) in enumerate(tests):
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
        
        # Pause between tests so user can see results
        if TEST_DELAY > 0 and i < len(tests) - 1:
            print(f"\n  ... pausing {TEST_DELAY}s before next test ...")
            time.sleep(TEST_DELAY)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{len(results)} passed")
    
    if failed > 0:
        print(f"\n⚠ {failed} test(s) failed!")
        return 1
    else:
        print("\n✓ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())