#!/usr/bin/env python
"""
Test script for the --test-cases filter functionality in aurite run evaluation command.

This script tests various filter patterns:
- Test case names
- Indices (single and ranges)
- Regex patterns
- Mixed filters
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aurite.bin.cli.commands.run import run_component


async def test_evaluation_filters():
    """Test different test case filter patterns."""

    evaluation_name = "weather_mcp_evaluation"

    print("=" * 60)
    print("Testing Evaluation CLI with --test-cases filters")
    print("=" * 60)

    # Test 1: Run without filter (all test cases)
    print("\n1. Running all test cases (no filter)...")
    print("-" * 40)
    try:
        await run_component(
            name=evaluation_name,
            user_message=None,
            system_prompt=None,
            session_id=None,
            short=False,
            debug=False,
            test_cases=None,
        )
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Filter by test case name
    print("\n2. Filter by test case name: 'Get San Francisco Weather'...")
    print("-" * 40)
    try:
        await run_component(
            name=evaluation_name,
            user_message=None,
            system_prompt=None,
            session_id=None,
            short=False,
            debug=False,
            test_cases="Get San Francisco Weather",
        )
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: Filter by index
    print("\n3. Filter by index: '0' (first test case)...")
    print("-" * 40)
    try:
        await run_component(
            name=evaluation_name,
            user_message=None,
            system_prompt=None,
            session_id=None,
            short=False,
            debug=False,
            test_cases="0",
        )
    except Exception as e:
        print(f"Error: {e}")

    # Test 4: Filter by regex pattern
    print("\n4. Filter by regex pattern: '/San Francisco/'...")
    print("-" * 40)
    try:
        await run_component(
            name=evaluation_name,
            user_message=None,
            system_prompt=None,
            session_id=None,
            short=False,
            debug=False,
            test_cases="/San Francisco/",
        )
    except Exception as e:
        print(f"Error: {e}")

    # Test 5: Invalid filter (should show error)
    print("\n5. Invalid filter: 'NonexistentTestCase'...")
    print("-" * 40)
    try:
        await run_component(
            name=evaluation_name,
            user_message=None,
            system_prompt=None,
            session_id=None,
            short=False,
            debug=False,
            test_cases="NonexistentTestCase",
        )
    except Exception as e:
        print(f"Expected error occurred: {e}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


async def test_filter_parsing():
    """Test the filter parsing logic directly."""
    from aurite.lib.config.config_manager import ConfigManager
    from aurite.testing.qa.qa_engine import QAEngine

    print("\n" + "=" * 60)
    print("Testing filter parsing logic")
    print("=" * 60)

    # Create a QA engine instance
    config_manager = ConfigManager()
    qa_engine = QAEngine(config_manager)

    # Sample test cases
    test_cases = [
        {"name": "Test Case 1", "input": "input1"},
        {"name": "Test Case 2", "input": "input2"},
        {"name": "Weather Test", "input": "weather input"},
        {"name": "Another Test", "input": "another input"},
        {"name": "Final Test", "input": "final input"},
    ]

    # Test different filter patterns
    test_patterns = [
        ("Test Case 1", "Single name filter"),
        ("0", "Single index"),
        ("0,2", "Multiple indices"),
        ("0-2", "Index range"),
        ("Test Case 1,Weather Test", "Multiple names"),
        ("/Test/", "Regex pattern"),
        ("regex:^Test", "Alternative regex syntax"),
        ("0,Test Case 2,/Weather/", "Mixed filter"),
    ]

    for pattern, description in test_patterns:
        print(f"\nTesting: {description}")
        print(f"Pattern: '{pattern}'")
        filtered = qa_engine._filter_test_cases(test_cases, pattern)
        print(f"Matched {len(filtered)} test case(s):")
        for case in filtered:
            print(f"  - {case['name']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Run both test suites
    asyncio.run(test_filter_parsing())
    print("\nNow testing with actual evaluation configuration...\n")
    asyncio.run(test_evaluation_filters())
