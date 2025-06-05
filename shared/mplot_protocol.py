"""
Multi-plot Protocol for Pixil LED Matrix System

This module handles efficient batching of plot commands by packing multiple
plot operations into binary format for reduced queue overhead.

BINARY FORMAT (20 bytes per plot):
┌─────────────┬──────────────┬───────────────┬───────────────┬─────────────────┬─────────────┐
│ Field       │ Size (bytes) │ Type          │ Range         │ Special Values  │ Description │
├─────────────┼──────────────┼───────────────┼───────────────┼─────────────────┼─────────────┤
│ x           │ 2            │ unsigned      │ 0-65535       │ None            │ X coordinate│
│ y           │ 2            │ unsigned      │ 0-65535       │ None            │ Y coordinate│
│ color_id    │ 2            │ signed        │ -32768-32767  │ None            │ Color ID    │
│ intensity   │ 1            │ unsigned      │ 0-100         │ 255=default(100)│ Brightness  │
│ burnout     │ 4            │ unsigned      │ 0-4294967294  │ 0xFFFFFFFF=None │ Burnout ms  │
│ padding     │ 9            │ reserved      │ 0             │ None            │ Future use  │
└─────────────┴──────────────┴───────────────┴───────────────┴─────────────────┴─────────────┘

COLOR ID MAPPING:
- Spectral colors: 0-99 (current), 100-999 (future expansion)
- Named colors: -1, -2, -3, ... (negative values)
- Example: red=-1, blue=-2, green=-3, etc.

STRUCT FORMAT: '<HHhBI9x'
- < = little-endian
- H = unsigned short (2 bytes) for x, y
- h = signed short (2 bytes) for color_id  
- B = unsigned char (1 byte) for intensity
- I = unsigned int (4 bytes) for burnout
- 9x = 9 padding bytes (zeros)

USAGE:
    # Packing (Pixil.py side)
    buffer = bytearray()
    buffer.extend(pack_mplot(10, 20, "red", 100, 1000))
    buffer.extend(pack_mplot(15, 25, "blue"))  # defaults
    encoded = encode_buffer(buffer)
    
    # Unpacking (RGB_matrix_lib side)  
    binary_data = decode_buffer(encoded)
    for x, y, color, intensity, burnout in unpack_mplot_batch(binary_data):
        api.plot(x, y, color, intensity, burnout)
"""

import struct
import base64
from typing import Union, Optional, Iterator, Tuple, Any

# Binary format constants
MPLOT_RECORD_SIZE = 20
STRUCT_FORMAT = '<HHhBI9x'  # little-endian: ushort, ushort, short, uchar, uint, 9 padding

# Special values for optional parameters
INTENSITY_DEFAULT = 255      # Indicates "use default intensity (100)"
BURNOUT_NONE = 0xFFFFFFFF   # Indicates "no burnout"

# Color ID mapping: named colors to negative IDs
# Future expansion: add more colors with sequential negative IDs
NAMED_COLOR_TO_ID = {
    'black': -1,
    'white': -2,
    'gray': -3,
    'light_gray': -4,
    'dark_gray': -5,
    'silver': -6,
    'red': -7,
    'crimson': -8,
    'maroon': -9,
    'rose': -10,
    'pink': -11,
    'salmon': -12,
    'coral': -13,
    'brown': -14,
    'standard_brown': -15,
    'dark_brown': -16,
    'wood_brown': -17,
    'tan': -18,
    'orange': -19,
    'gold': -20,
    'peach': -21,
    'bronze': -22,
    'yellow': -23,
    'lime': -24,
    'green': -25,
    'olive': -26,
    'spring_green': -27,
    'forest_green': -28,
    'mint': -29,
    'teal': -30,
    'turquoise': -31,
    'cyan': -32,
    'sky_blue': -33,
    'azure': -34,
    'blue': -35,
    'navy': -36,
    'royal_blue': -37,
    'ocean_blue': -38,
    'indigo': -39,
    'purple': -40,
    'violet': -41,
    'magenta': -42,
    'lavender': -43,
}

# Reverse mapping: ID to named color (for unpacking)
ID_TO_NAMED_COLOR = {v: k for k, v in NAMED_COLOR_TO_ID.items()}

def get_color_id(color: Union[str, int]) -> int:
    """
    Convert color specification to color ID.
    """
    
    if isinstance(color, int):
        # Spectral color: validate range and return as-is
        if 0 <= color <= 99:
            return color
        else:
            raise ValueError(f"Spectral color must be 0-99, got {color}")
    
    elif isinstance(color, str):
        # Named color: lookup in mapping
        color_lower = color.lower()
        
        if color_lower in NAMED_COLOR_TO_ID:
            result = NAMED_COLOR_TO_ID[color_lower]
            return result
        else:
            raise ValueError(f"Unknown named color: {color}")
    
    else:
        raise ValueError(f"Color must be string or int, got {type(color)}")

def get_color_from_id(color_id: int) -> Union[str, int]:
    """
    Convert color ID back to color specification.
    
    Args:
        color_id: Color ID (negative for named, positive for spectral)
        
    Returns:
        Union[str, int]: Named color (str) or spectral number (int)
        
    Raises:
        ValueError: If color_id is not recognized
    """
    if color_id >= 0:
        # Spectral color
        if 0 <= color_id <= 99:
            return color_id
        else:
            raise ValueError(f"Invalid spectral color ID: {color_id}")
    else:
        # Named color
        if color_id in ID_TO_NAMED_COLOR:
            return ID_TO_NAMED_COLOR[color_id]
        else:
            raise ValueError(f"Unknown named color ID: {color_id}")

def pack_mplot(x: int, y: int, color: Union[str, int], 
               intensity: Optional[int] = None, 
               burnout: Optional[int] = None) -> bytes:
    """
    Pack a single mplot command into 20-byte binary format.
    """
    # Validate coordinates
    if not (0 <= x <= 65535):
        raise ValueError(f"X coordinate must be 0-65535, got {x}")
    if not (0 <= y <= 65535):
        raise ValueError(f"Y coordinate must be 0-65535, got {y}")
    
    # Convert color to ID
    color_id = get_color_id(color)
    
    # Handle optional intensity
    if intensity is None:
        intensity_value = INTENSITY_DEFAULT
    else:
        if not (0 <= intensity <= 100):
            raise ValueError(f"Intensity must be 0-100, got {intensity}")
        intensity_value = intensity
    
    # Handle optional burnout
    if burnout is None:
        burnout_value = BURNOUT_NONE
    else:
        if not (0 <= burnout <= 4294967294):  # Leave room for special value
            raise ValueError(f"Burnout must be 0-4294967294, got {burnout}")
        burnout_value = burnout
    
    # Pack into binary format
    return struct.pack(STRUCT_FORMAT, x, y, color_id, intensity_value, burnout_value)

def unpack_mplot_batch(binary_data: bytes) -> Iterator[Tuple[int, int, Union[str, int], Optional[int], Optional[int]]]:
    """
    Unpack binary data into individual mplot commands.
    
    Args:
        binary_data: Binary data containing packed mplot records
        
    Yields:
        Tuple[int, int, Union[str, int], Optional[int], Optional[int]]: 
            (x, y, color, intensity, burnout) for each plot
            
    Raises:
        ValueError: If binary data is malformed
    """
    if len(binary_data) % MPLOT_RECORD_SIZE != 0:
        raise ValueError(f"Binary data size {len(binary_data)} is not multiple of record size {MPLOT_RECORD_SIZE}")
    
    # Process each 20-byte record
    for offset in range(0, len(binary_data), MPLOT_RECORD_SIZE):
        record = binary_data[offset:offset + MPLOT_RECORD_SIZE]
        
        # Unpack binary record
        x, y, color_id, intensity_value, burnout_value = struct.unpack(STRUCT_FORMAT, record)
        
        # Convert color ID back to color
        color = get_color_from_id(color_id)
        
        # Handle special values
        intensity = None if intensity_value == INTENSITY_DEFAULT else intensity_value
        burnout = None if burnout_value == BURNOUT_NONE else burnout_value
        
        yield (x, y, color, intensity, burnout)

def encode_buffer(buffer: bytes) -> str:
    """
    Encode binary buffer as base64 string for transmission.
    
    Args:
        buffer: Binary data containing packed mplot records
        
    Returns:
        str: Base64 encoded string
    """
    return base64.b64encode(buffer).decode('ascii')

def decode_buffer(encoded_string: str) -> bytes:
    """
    Decode base64 string back to binary buffer.
    
    Args:
        encoded_string: Base64 encoded string
        
    Returns:
        bytes: Binary data
        
    Raises:
        ValueError: If string is not valid base64
    """
    try:
        return base64.b64decode(encoded_string.encode('ascii'))
    except Exception as e:
        raise ValueError(f"Invalid base64 encoding: {str(e)}")

def get_protocol_info() -> dict:
    """
    Get protocol information for debugging and validation.
    
    Returns:
        dict: Protocol constants and mappings
    """
    return {
        'record_size': MPLOT_RECORD_SIZE,
        'struct_format': STRUCT_FORMAT,
        'intensity_default': INTENSITY_DEFAULT,
        'burnout_none': BURNOUT_NONE,
        'named_color_count': len(NAMED_COLOR_TO_ID),
        'spectral_color_range': '0-99 (current), 100-999 (future)',
        'max_burnout_ms': 4294967294,
        'max_coordinates': 65535,
    }

# For debugging and testing
if __name__ == "__main__":
    # Example usage
    print("MPlot Protocol Test")
    print("==================")
    
    # Test packing
    buffer = bytearray()
    buffer.extend(pack_mplot(10, 20, "red", 100, 1000))
    buffer.extend(pack_mplot(15, 25, "blue"))  # Test defaults
    buffer.extend(pack_mplot(30, 40, 50, 75, 2000))  # Test spectral
    
    print(f"Buffer size: {len(buffer)} bytes ({len(buffer)//MPLOT_RECORD_SIZE} records)")
    
    # Test encoding/decoding
    encoded = encode_buffer(buffer)
    print(f"Encoded length: {len(encoded)} characters")
    
    decoded = decode_buffer(encoded)
    print(f"Decoded size: {len(decoded)} bytes")
    
    # Test unpacking
    print("\nUnpacked records:")
    for i, (x, y, color, intensity, burnout) in enumerate(unpack_mplot_batch(decoded)):
        print(f"  {i+1}: plot({x}, {y}, {color}, {intensity}, {burnout})")
    
    # Protocol info
    print(f"\nProtocol info: {get_protocol_info()}")