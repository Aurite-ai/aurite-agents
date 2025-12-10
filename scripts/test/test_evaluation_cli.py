#!/usr/bin/env python
"""
Test script for evaluation CLI command functionality.
Tests running evaluation components via `aurite run` command.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from aurite.bin.cli.commands.run import run_component


async def test_evaluation_cli():
    """Test running an evaluation via CLI command."""

    print("Testing evaluation CLI command...")
    print("=" * 50)

    # Test running the weather_mcp_evaluation
    evaluation_name = "weather_mcp_evaluation"

    print(f"Running evaluation: {evaluation_name}")
    print("-" * 50)

    try:
        # Run the evaluation component
        # This simulates: aurite run weather_mcp_evaluation
        await run_component(
            name=evaluation_name,
            user_message=None,  # Not needed for evaluations
            system_prompt=None,  # Not needed for evaluations
            session_id=None,  # Optional
            short=False,  # Show full results
            debug=False,  # Normal output mode
        )

        print("\n" + "=" * 50)
        print("✅ Evaluation CLI test completed successfully!")

    except Exception as e:
        print(f"\n❌ Evaluation CLI test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def test_evaluation_cli_short_mode():
    """Test running an evaluation in short mode."""

    print("\nTesting evaluation CLI command in short mode...")
    print("=" * 50)

    evaluation_name = "weather_mcp_evaluation"

    print(f"Running evaluation (short mode): {evaluation_name}")
    print("-" * 50)

    try:
        await run_component(
            name=evaluation_name,
            user_message=None,
            system_prompt=None,
            session_id=None,
            short=True,  # Short mode - no detailed table
            debug=False,
        )

        print("\n" + "=" * 50)
        print("✅ Short mode evaluation test completed successfully!")

    except Exception as e:
        print(f"\n❌ Short mode evaluation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def main():
    """Run all evaluation CLI tests."""

    print("\n" + "=" * 60)
    print("EVALUATION CLI COMMAND TEST SUITE")
    print("=" * 60)

    tests = [
        ("Full evaluation output", test_evaluation_cli),
        ("Short mode evaluation", test_evaluation_cli_short_mode),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running test: {test_name}")
        success = await test_func()
        results.append((test_name, success))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
