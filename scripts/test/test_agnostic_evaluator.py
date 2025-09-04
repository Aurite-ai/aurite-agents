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


def run_agent(case: EvaluationCase):
    if "weather" in case.input:
        return "The weather in London is 15°C, partly cloudy"
    elif "Calculate" in case.input:
        return "2 + 2 is 4"
    else:
        return "Hello world!"


async def run_agent_async(case: EvaluationCase):
    if "weather" in case.input:
        return "The weather in London is 15°C, partly cloudy"
    elif "Calculate" in case.input:
        return "2 + 2 is 4"
    else:
        return "Hello world!"


def run(case: EvaluationCase):
    if "weather" in case.input:
        return "The weather in London is 15°C, partly cloudy"
    elif "Calculate" in case.input:
        return "2 + 2 is 4"
    else:
        return "I'm sorry, I cannot help with that. Please try again later."


def create_test_evaluation_config(test_name: str = "basic_test") -> EvaluationConfig:
    """Create a test EvaluationConfig with sample data."""
    run_input = run_agent

    match test_name:
        case "basic_test":
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
        case "test_run_agent" | "test_run_agent_async" | "test_run_agent_file":
            test_cases = [
                EvaluationCase(
                    input="What's the weather in London?",
                    expectations=[
                        "The output contains temperature information in celcius",
                        "The output mentions the city name",
                        "The output provides weather conditions",
                    ],
                ),
                EvaluationCase(
                    input="Calculate 2 + 2",
                    expectations=[
                        "The output provides the correct mathematical result",
                        "The output shows the calculation",
                    ],
                ),
                EvaluationCase(
                    input="What is 2 + 2?",
                    expectations=[
                        "The output provides the correct mathematical result",
                        "The output shows the calculation",
                    ],
                ),
            ]

            if test_name == "test_run_agent_async":
                run_input = run_agent_async
            elif test_name == "test_run_agent_file":
                run_input = "scripts/test/test_agnostic_evaluator.py"

    return EvaluationConfig(
        name=f"Test Evaluation - {test_name}",
        type="evaluation",
        eval_name="test_agent",
        eval_type="agent",
        user_input="Test input",
        expected_output="Test expected output",
        review_llm="test_llm",
        test_cases=test_cases,
        run_agent=run_input,
    )


async def test_basic_evaluation():
    """Test basic evaluation functionality."""
    print("🧪 Testing Basic Evaluation")
    print("-" * 40)

    # Create test data
    config = create_test_evaluation_config("basic_test")

    result = await evaluate(config)

    # Verify results
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert "result" in result, "Result should contain 'result' key"
    assert len(result["result"]) == 5, f"Expected 5 test case results, got {len(result['result'])}"

    print("✅ Basic evaluation test passed")
    for res in result["result"].values():
        print(res)
    return result


async def test_run_agent():
    """Test run_agent functionality."""
    print("🧪 Testing Run Agent")
    print("-" * 40)

    # Create test data
    config = create_test_evaluation_config("test_run_agent")

    result = await evaluate(config)

    # Verify results
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert "result" in result, "Result should contain 'result' key"
    assert len(result["result"]) == 3, f"Expected 3 test case results, got {len(result['result'])}"

    print("✅ Run Agent test passed")
    for res in result["result"].values():
        print(res)
    return result


async def test_run_agent_async():
    """Test run_agent_async functionality."""
    print("🧪 Testing Run Agent Async")
    print("-" * 40)

    # Create test data
    config = create_test_evaluation_config("test_run_agent_async")

    result = await evaluate(config)

    # Verify results
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert "result" in result, "Result should contain 'result' key"
    assert len(result["result"]) == 3, f"Expected 3 test case results, got {len(result['result'])}"

    print("✅ Run Agent Async test passed")
    for res in result["result"].values():
        print(res)
    return result


async def test_run_agent_file():
    """Test run_agent functionality."""
    print("🧪 Testing Run Agent File")
    print("-" * 40)

    # Create test data
    config = create_test_evaluation_config("test_run_agent_file")

    result = await evaluate(config)

    # Verify results
    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert "result" in result, "Result should contain 'result' key"
    assert len(result["result"]) == 3, f"Expected 3 test case results, got {len(result['result'])}"

    print("✅ Run Agent File test passed")
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

        test_results["test_run_agent"] = await test_run_agent()
        print()

        test_results["test_run_agent_async"] = await test_run_agent_async()
        print()

        test_results["test_run_agent_file"] = await test_run_agent_file()
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
