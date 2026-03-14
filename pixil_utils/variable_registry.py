"""
Variable Registry for Pixil - Optimized variable storage system.
Replaces string-based dictionary lookups with indexed array access.
"""

import re
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

class VariableRegistry:
    """
    Optimized variable storage using indexed arrays instead of string dictionaries.
    Provides faster variable access by eliminating string hashing overhead.
    """
    
    def __init__(self):
        """Initialize empty variable registry."""
        self.name_to_index: Dict[str, int] = {}  # "v_x" → 0
        self.values: List[Any] = []              # [32.0, array_obj, ...]
        self.next_index: int = 0
        
    def scan_and_register(self, script_lines: List[str]) -> None:
        """
        Scan script lines and pre-register all variables for optimal performance.
        
        Args:
            script_lines: List of script lines to scan
        """
        start_time = time.perf_counter()
        
        # Find all variable references in the script
        all_variables = set()
        
        for line in script_lines:
            # Find all v_variable references using regex
            variables_in_line = re.findall(r'v_\w+', line)
            all_variables.update(variables_in_line)
        
        # Register all found variables
        for var_name in sorted(all_variables):  # Sort for consistent indexing
            self.register(var_name)
            
        scan_time = time.perf_counter() - start_time
        print(f"Variable registry: Registered {len(all_variables)} variables in {scan_time*1000:.1f}ms")
        
    def register(self, var_name: str) -> int:
        """
        Register a variable and return its index.
        
        Args:
            var_name: Variable name (e.g., "v_x")
            
        Returns:
            Index assigned to this variable
        """
        if var_name not in self.name_to_index:
            self.name_to_index[var_name] = self.next_index
            self.values.append(0.0)  # Default value (float for numeric compatibility)
            self.next_index += 1
            
        return self.name_to_index[var_name]
    
    def get(self, var_name: str) -> Any:
        """
        Get variable value using optimized array access.
        
        Args:
            var_name: Variable name
            
        Returns:
            Variable value
            
        Raises:
            KeyError: If variable not found (matches current Pixil behavior)
        """
        try:
            index = self.name_to_index[var_name]
            return self.values[index]
        except KeyError:
            raise KeyError(f"Variable '{var_name}' not found")
    
    def set(self, var_name: str, value: Any) -> None:
        """
        Set variable value using optimized array access.
        
        Args:
            var_name: Variable name
            value: Value to set
        """
        if var_name not in self.name_to_index:
            # Auto-register new variables (for edge cases)
            self.register(var_name)
            
        index = self.name_to_index[var_name]
        self.values[index] = value
    
    def fast_array_access(self, array_name: str, index_var_name: str) -> Any:
        """
        Optimized array access that eliminates both variable lookups.
        
        Args:
            array_name: Name of array variable (e.g., "v_positions")
            index_var_name: Name of index variable (e.g., "v_i")
            
        Returns:
            Array element value
        """
        # Get both array object and index with direct array access
        array_obj = self.values[self.name_to_index[array_name]]
        index_val = self.values[self.name_to_index[index_var_name]]
        
        # Array access using PixilArray's optimized __getitem__
        return array_obj[int(index_val)]
    
    def fast_array_assign(self, array_name: str, index_var_name: str, value: Any) -> None:
        """
        Optimized array assignment that eliminates variable lookups.
        
        Args:
            array_name: Name of array variable
            index_var_name: Name of index variable  
            value: Value to assign
        """
        array_obj = self.values[self.name_to_index[array_name]]
        index_val = self.values[self.name_to_index[index_var_name]]
        
        array_obj[int(index_val)] = value
    
    # Dictionary-compatible interface for existing code
    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access for compatibility."""
        return self.get(key)
        
    def __setitem__(self, key: str, value: Any) -> None:
        """Dictionary-style assignment for compatibility."""
        self.set(key, value)
        
    def __contains__(self, key: str) -> bool:
        """Check if variable exists."""
        return key in self.name_to_index
    
    def keys(self):
        """Return variable names (for compatibility)."""
        return self.name_to_index.keys()
    
    def items(self):
        """Return variable name-value pairs (for compatibility)."""
        for name, index in self.name_to_index.items():
            yield name, self.values[index]
    
    def get_variable_count(self) -> int:
        """Return the number of registered variables."""
        return len(self.name_to_index)


def load_script_lines(script_path: str) -> List[str]:
    """
    Load and preprocess script lines for variable scanning.
    
    Args:
        script_path: Path to script file
        
    Returns:
        List of cleaned script lines
    """
    with open(script_path, 'r') as f:
        # Remove comments and empty lines
        lines = []
        for line in f:
            # Remove comments
            if '#' in line:
                line = line[:line.index('#')]
            line = line.strip()
            if line:
                lines.append(line)
        return lines


# Export the main class
__all__ = ['VariableRegistry', 'load_script_lines']