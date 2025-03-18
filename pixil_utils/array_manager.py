# array_manager.py
from typing import Union, Any, Dict, Optional, Literal
from .debug import debug_print, DEBUG_VERBOSE

ArrayType = Literal['numeric', 'string']

class PixilArray:
    """Array implementation for Pixil scripting language."""
    
    MAX_STRING_LENGTH = 1000  # This needs to be defined as a class variable

    def __init__(self, size: int, array_type: ArrayType = 'numeric'):
        if not isinstance(size, (int, float)):
            raise ValueError(f"Array size must be a number, got {type(size)}")
            
        size = int(size)
        if size <= 0:
            raise ValueError(f"Array size must be positive, got {size}")
            
        self.size = size
        self._max_index = size - 1  # Cache max index
        self.array_type = array_type
        self.data = [0 if array_type == 'numeric' else '' for _ in range(size)]

    def __getitem__(self, index: int):
        # Fast path for common case (int index within bounds)
        if isinstance(index, int) and 0 <= index < self.size:
            value = self.data[index]
            if DEBUG_VERBOSE:
                debug_print(f"Getting array[{index}] = {value}", DEBUG_VERBOSE)
            return value
            
        # Fall back to validation for edge cases
        index = self._validate_index(index)
        value = self.data[index]
        if DEBUG_VERBOSE:
            debug_print(f"Getting array[{index}] = {value}", DEBUG_VERBOSE)
        return value

    # Note: The following method deliberatly has duplicated code for performance reasons
    def __setitem__(self, index: int, value: Any):
        # Fast path for common case (integer index within bounds)
        if isinstance(index, int) and 0 <= index < self.size:
            # Even in fast path, we still need to handle type validation and processing
            if self.array_type == 'string':
                if not isinstance(value, str):
                    raise ValueError(f"String array requires string values, got {type(value)}")
                    
                # Strip quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                    
                # Process escape sequences
                value = self._process_escape_sequences(value)
                
                # Validate string length
                if len(value) > self.MAX_STRING_LENGTH:
                    raise ValueError(f"String exceeds maximum length of {self.MAX_STRING_LENGTH}")
                    
            # Handle numeric array type
            else:
                if not isinstance(value, (int, float)):
                    raise ValueError(f"Numeric array requires numeric values, got {type(value)}")
                value = float(value)
                
            self.data[index] = value
            return
        
        # Slow path for non-integer indexes or potentially out-of-bounds indexes
        # First validate and convert the index
        if not isinstance(index, (int, float)):
            raise ValueError(f"Array index must be a number, got {type(index)}")
        
        index = int(index)
        if not (0 <= index < self.size):
            raise IndexError(f"Array index {index} out of bounds [0, {self.size-1}]")
        
        # Now handle the value type checks and processing - same as fast path
        if self.array_type == 'string':
            if not isinstance(value, str):
                raise ValueError(f"String array requires string values, got {type(value)}")
                
            # Strip quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
                
            # Process escape sequences
            value = self._process_escape_sequences(value)
            
            # Validate string length
            if len(value) > self.MAX_STRING_LENGTH:
                raise ValueError(f"String exceeds maximum length of {self.MAX_STRING_LENGTH}")
                
        # Handle numeric array type
        else:
            if not isinstance(value, (int, float)):
                raise ValueError(f"Numeric array requires numeric values, got {type(value)}")
            value = float(value)
            
        self.data[index] = value

    def _validate_index(self, index: Any) -> int:
        # Convert to int first if it's a float
        if isinstance(index, float):
            index = int(index)
        elif not isinstance(index, int):
            raise ValueError(f"Array index must be a number, got {type(index)}")
            
        # Check bounds
        if not (0 <= index < self.size):
            raise IndexError(f"Array index {index} out of bounds [0, {self.size-1}]")
        return index

    def _process_escape_sequences(self, value: str) -> str:
        """Process escape sequences in string values."""
        escape_sequences = {
            r'\"': '"',   # Double quote
            r"\'": "'",   # Single quote
            r'\n': '\n',  # Newline
            r'\t': '\t',  # Tab
            r'\\': '\\'   # Backslash
        }
        
        result = value
        for escaped, unescaped in escape_sequences.items():
            result = result.replace(escaped, unescaped)
        return result

    def get_formatted_value(self, index: int) -> str:
        """Get value formatted for command usage."""
        value = self[index]
        if self.array_type == 'string':
            # Don't add quotes - commands expect raw strings
            return value
        return str(value)

    def get_type(self) -> ArrayType:
        """Get array type."""
        return self.array_type

def validate_array_access(array_name: str, index: Any, variables: Dict[str, Any]) -> Union[float, str]:
    """
    Validate array access and return value.
    This encapsulates all array validation logic.
    """
    # Check array exists
    if array_name not in variables:
        raise ValueError(f"Array '{array_name}' not found")
        
    array = variables[array_name]
    if not isinstance(array, PixilArray):
        raise ValueError(f"'{array_name}' is not an array")
        
    # Validate index type
    if not isinstance(index, (int, float)):
        raise ValueError(f"Array index must be a number, got {type(index)}")
        
    # Access array (bounds checking done in __getitem__)
    return array[int(index)]

# Export symbols
__all__ = ['PixilArray', 'validate_array_access', 'ArrayType']