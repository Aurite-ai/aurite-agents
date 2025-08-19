#!/usr/bin/env python3
"""
Test script to simulate the exact weather response scenario that caused the original crash.

This script simulates what happens when a weather API returns temperature data
with degree symbols in different encodings.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import aurite modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from aurite.bin.studio.studio import safe_decode_line


def test_weather_scenario():
    """Test the exact weather response scenario that caused the original crash."""
    
    print("Testing weather response encoding scenarios...")
    print("=" * 60)
    
    # Simulate various weather responses that could cause encoding issues
    weather_responses = [
        "The weather in London is: 15°C, partly cloudy",
        "Temperature: 25°C, Humidity: 60%",
        "Current conditions: -5°C, snowing ❄️",
        "Heat index: 35°C (feels like 40°C)",
        "Wind chill: -10°C, gusts up to 25 km/h",
        "Today's high: 22°C, low: 8°C",
        "UV index: 7, temperature: 28°C ☀️",
    ]
    
    # Test each response in different encodings that might be output by the API server
    encodings_to_test = ['utf-8', 'windows-1252', 'latin-1']
    
    for response in weather_responses:
        print(f"\nTesting response: {repr(response)}")
        print("-" * 40)
        
        for encoding in encodings_to_test:
            try:
                # Encode the response as it might appear in subprocess output
                encoded_bytes = response.encode(encoding)
                
                # Test our safe decoding function
                decoded_result = safe_decode_line(encoded_bytes)
                
                print(f"  {encoding:12} -> ✓ {repr(decoded_result)}")
                
            except Exception as e:
                print(f"  {encoding:12} -> ✗ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("Weather encoding test completed!")
    
    # Test the specific byte that caused the original error (0xb0 = degree symbol in Windows-1252)
    print(f"\nTesting the specific problematic byte 0xb0:")
    problematic_line = b'Workflow finished successfully. Returning: The weather in London is: 15\xb0C, partly cloudy'
    
    try:
        result = safe_decode_line(problematic_line)
        print(f"✓ Successfully decoded: {repr(result)}")
    except Exception as e:
        print(f"✗ Failed to decode: {e}")


if __name__ == "__main__":
    test_weather_scenario()
