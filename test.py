# Test script to see what's available
try:
    from rgbmatrix import graphics
    print("✓ graphics module is available")
    print(dir(graphics))
except ImportError as e:
    print("✗ graphics module not available:", e)

try:
    from rgbmatrix import RGBMatrix
    matrix = RGBMatrix()  # Or however you create it
    print("Available methods on canvas:")
    print([method for method in dir(matrix) if not method.startswith('_')])
except Exception as e:
    print("Error checking RGBMatrix methods:", e)