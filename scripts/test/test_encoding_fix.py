#!/usr/bin/env python3
"""
Test script to verify the encoding fix in studio.py works correctly.

This script tests the safe_decode_line function with various problematic
characters that could cause UnicodeDecodeError.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import aurite modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from aurite.bin.studio.studio import safe_decode_line


def test_safe_decode_line():
    """Test the safe_decode_line function with various problematic inputs."""
    
    print("Testing safe_decode_line function...")
    
    # Test cases with different encodings and problematic characters
    test_cases = [
        # Normal UTF-8 text
        ("Normal text", "Normal text".encode('utf-8')),
        
        # Degree symbol in different encodings
        ("Degree symbol UTF-8", "Temperature: 25°C".encode('utf-8')),
        ("Degree symbol Windows-1252", "Temperature: 25°C".encode('windows-1252')),
        ("Degree symbol Latin-1", "Temperature: 25°C".encode('latin-1')),
        
        # Other special characters
        ("Euro symbol", "Price: 100€".encode('windows-1252')),
        ("Pound symbol", "Cost: £50".encode('windows-1252')),
        
        # Mixed content that might cause issues
        ("Weather report", "London: 15°C, partly cloudy ☁️".encode('utf-8')),
        
        # Completely invalid UTF-8 sequence
        ("Invalid bytes", b'\xff\xfe\xfd\xfc'),
        
        # Empty input
        ("Empty", b''),
    ]
    
    print("\nRunning test cases:")
    print("-" * 60)
    
    for description, test_bytes in test_cases:
        try:
            result = safe_decode_line(test_bytes)
            print(f"✓ {description:20} -> {repr(result)}")
        except Exception as e:
            print(f"✗ {description:20} -> ERROR: {e}")
    
    print("-" * 60)
    print("All tests completed!")
    
    # Test the specific byte sequence from the original error
    print("\nTesting the specific problematic byte sequence:")
    problematic_bytes = b'Some text with \xb0 degree symbol'
    try:
        result = safe_decode_line(problematic_bytes)
        print(f"✓ Problematic sequence -> {repr(result)}")
    except Exception as e:
        print(f"✗ Problematic sequence -> ERROR: {e}")


if __name__ == "__main__":
    test_safe_decode_line()
