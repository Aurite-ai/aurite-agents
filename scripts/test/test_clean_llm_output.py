#!/usr/bin/env python3
"""
Test script for the clean_llm_output function fix.

This script verifies that the clean_llm_output function correctly handles:
1. Valid JSON with trailing content
2. Valid JSON without trailing content
3. Nested JSON objects
4. JSON with strings containing braces
"""

import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aurite.testing.qa.utils.qa_utils import clean_llm_output


def test_clean_llm_output():
    """Test various scenarios for the clean_llm_output function."""

    print("Testing clean_llm_output function...")
    print("=" * 60)

    # Test 1: Valid JSON with trailing content (the reported issue)
    test1 = '{"analysis": "The agent successfully completed the task", "expectations_broken": []} This is extra text that should be ignored.'
    print("\nTest 1: JSON with trailing content")
    print(f"Input: {test1[:80]}...")
    cleaned1 = clean_llm_output(test1)
    print(f"Cleaned: {cleaned1}")
    try:
        parsed1 = json.loads(cleaned1)
        print(f"✓ Successfully parsed: {parsed1}")
    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse: {e}")
        return False

    # Test 2: Valid JSON without trailing content
    test2 = '{"analysis": "Test completed", "expectations_broken": ["expectation 1"]}'
    print("\nTest 2: Clean JSON without trailing content")
    print(f"Input: {test2}")
    cleaned2 = clean_llm_output(test2)
    print(f"Cleaned: {cleaned2}")
    try:
        parsed2 = json.loads(cleaned2)
        print(f"✓ Successfully parsed: {parsed2}")
    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse: {e}")
        return False
