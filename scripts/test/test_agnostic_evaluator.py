#!/usr/bin/env python3
"""
Test script for the agnostic_evaluator.py component.

This script provides a quick test of the evaluation functionality with mock dependencies
and various test scenarios to verify the evaluator works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path so we can import aurite modules
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from aurite.lib.components.evaluation.agnostic_evaluator import evaluate
from aurite.lib.models.config.components import EvaluationCase, EvaluationConfig


def create_test_evaluation_config(test_name: str = "basic_test") -> EvaluationConfig:
    """Create a test EvaluationConfig with sample data."""

    test_cases = [
        EvaluationCase(
            input="What's the weather in London?",
            output="The weather in London is 15°C, partly cloudy",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
        EvaluationCase(
            input="What's the weather in London?",
            output="The weather is 15°C, partly cloudy",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
        EvaluationCase(
            input="What's the weather in London?",
            output="The weather in London is 62°F, partly cloudy",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
        EvaluationCase(
            input="What's the weather in London?",
            output="The weather in London is 15°C",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
        EvaluationCase(
            input="Calculate 2 + 2",
            output="2 + 2 = 4",
            expectations=[
                "The output provides the correct mathematical result",
                "The output shows the calculation",
            ],
        ),
    ]

    return EvaluationConfig(
        name=f"Test Evaluation - {test_name}",
        type="evaluation",
        eval_name="test_agent",
        eval_type="agent",
        user_input="Test input",
        expected_output="Test expected output",
        review_llm="test_llm",
        test_cases=test_cases,
    )


async def test_basic_evaluation():
    """Test basic evaluation functionality."""
    print("🧪 Testing Basic Evaluation")
    print("-" * 40)

    # Create test data
    config = create_test_evaluation_config("basic_test")

    result = await evaluate(config, session_id="test_session")

    # Verify results
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert "result" in result, "Result should contain 'result' key"
    assert len(result["result"]) == 5, f"Expected 5 test case results, got {len(result['result'])}"

    print("✅ Basic evaluation test passed")
    for res in result["result"].values():
        print(res)
    return result


async def run_all_tests():
    """Run all test scenarios."""
    print("🚀 Starting Agnostic Evaluator Tests")
    print("=" * 60)

    test_results = {}

    try:
        # Run all test scenarios
        test_results["basic_evaluation"] = await test_basic_evaluation()
        print()

        # Print summary
        print("\n📊 Test Results Summary:")
        for test_name, result in test_results.items():
            if isinstance(result, dict) and "status" in result:
                status = "✅ PASS" if result["status"] == "success" else "❌ FAIL"
                print(f"  {test_name}: {status}")
            else:
                print(f"  {test_name}: ✅ PASS")

        return True

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main entry point for the test script."""
    print("Agnostic Evaluator Test Script")
    print("Testing: src/aurite/lib/components/evaluation/agnostic_evaluator.py")
    print()

    # Run the tests
    success = asyncio.run(run_all_tests())

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
