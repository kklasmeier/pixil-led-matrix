#simple test, you can ignore this

import sys
print("Python path:")
for path in sys.path:
    print(path)
print("\nTrying to import rgb_matrix_lib...")
try:
    import rgb_matrix_lib
    print("Success! Module contents:", dir(rgb_matrix_lib))
except ImportError as e:
    print("Import failed:", str(e))
    
print("\nChecking if commands.py exists...")
import os
module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rgb_matrix_lib', 'commands.py')
print(f"Looking for: {module_path}")
print(f"File exists: {os.path.exists(module_path)}")
