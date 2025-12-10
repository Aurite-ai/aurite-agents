#!/usr/bin/env python
"""
Test script to verify rate limiting functionality in evaluation system.

This script tests:
1. Semaphore-based concurrency control limits parallel test execution
2. Rate limit errors trigger retry logic with exponential backoff
3. Configuration parameters can be customized via EvaluationRequest
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Setup path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.aurite.lib.models.api.requests import EvaluationCase, EvaluationRequest
from src.aurite.testing.qa.component_qa_tester import ComponentQATester
from src.aurite.testing.qa.qa_models import ComponentQAConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_concurrent_execution_limit():
    """Test that semaphore properly limits concurrent test execution."""
    logger.info("=" * 80)
    logger.info("Test 1: Concurrent Execution Limit")
    logger.info("=" * 80)

    # Track concurrent executions
    concurrent_count = 0
    max_concurrent_observed = 0
    execution_times = []

    async def mock_execute_component(case, request, executor, mcp_test_agents):
        """Mock component execution that tracks concurrency."""
        nonlocal concurrent_count, max_concurrent_observed

        start_time = time.time()
        concurrent_count += 1
        max_concurrent_observed = max(max_concurrent_observed, concurrent_count)

        logger.info(f"  Executing test case {case.name} (concurrent: {concurrent_count})")

        # Simulate some work
        await asyncio.sleep(0.5)

        concurrent_count -= 1
        execution_times.append((case.name, time.time() - start_time))

        return f"Output for {case.name}"

    # Create test cases
    test_cases = [
        EvaluationCase(name=f"test_case_{i}", input=f"Input {i}", expectations=[f"Expectation {i}"]) for i in range(10)
    ]

    # Create evaluation request with max_concurrent_tests = 3
    request = EvaluationRequest(
        component_type="agent",
        test_cases=test_cases,
        max_concurrent_tests=3,  # Limit to 3 concurrent tests
        use_cache=False,
    )

    # Create tester
    tester = ComponentQATester()

    # Mock the execute_component function
    with patch("src.aurite.testing.qa.qa_utils.execute_component", side_effect=mock_execute_component):
        # Mock the LLM client and expectation analysis
        with patch("src.aurite.testing.qa.qa_utils.get_llm_client", return_value=AsyncMock()):
            with patch(
                "src.aurite.testing.qa.qa_utils.analyze_expectations",
                return_value=AsyncMock(analysis="All expectations met", expectations_broken=[]),
            ):
                # Run the evaluation
                start_time = time.time()
                result = await tester.test_component(request, None)
                total_time = time.time() - start_time

    # Verify results
    logger.info("\n  Results:")
    logger.info(f"    Max concurrent executions observed: {max_concurrent_observed}")
    logger.info(f"    Total execution time: {total_time:.2f}s")
    logger.info(f"    Total test cases: {result.total_cases}")
    logger.info(f"    Passed cases: {result.passed_cases}")

    assert max_concurrent_observed <= 3, f"Expected max 3 concurrent, got {max_concurrent_observed}"
    assert result.total_cases == 10

    logger.info("  ✅ Test passed: Concurrent execution properly limited to 3")
    return True


async def test_rate_limit_retry():
    """Test that rate limit errors trigger retry with exponential backoff."""
    logger.info("\n" + "=" * 80)
    logger.info("Test 2: Rate Limit Retry with Exponential Backoff")
    logger.info("=" * 80)

    # Track retry attempts
    retry_attempts = {}
    retry_delays = []

    async def mock_execute_with_rate_limit(case, request, executor, mcp_test_agents):
        """Mock that simulates rate limit errors."""
        case_name = case.name

        if case_name not in retry_attempts:
            retry_attempts[case_name] = 0

        retry_attempts[case_name] += 1
        attempt = retry_attempts[case_name]

        # Simulate rate limit on first 2 attempts
        if attempt <= 2:
            logger.info(f"  Simulating rate limit for {case_name} (attempt {attempt})")
            raise Exception("Error: Rate limit exceeded. Too many requests.")

        logger.info(f"  Success for {case_name} on attempt {attempt}")
        return f"Output for {case_name}"

    # Create test cases
    test_cases = [
        EvaluationCase(name=f"rate_limited_case_{i}", input=f"Input {i}", expectations=[f"Expectation {i}"])
        for i in range(3)
    ]

    # Create evaluation request with rate limit retry configuration
    request = EvaluationRequest(
        component_type="agent",
        test_cases=test_cases,
        max_concurrent_tests=1,  # Run sequentially for clearer testing
        rate_limit_retry_count=3,
        rate_limit_base_delay=0.1,  # Short delay for testing
        use_cache=False,
    )

    # Create tester
    tester = ComponentQATester()

    # Track sleep calls to verify exponential backoff
    original_sleep = asyncio.sleep

    async def mock_sleep(delay):
        retry_delays.append(delay)
        logger.info(f"    Sleeping for {delay:.3f}s (exponential backoff)")
        await original_sleep(min(delay, 0.2))  # Cap at 0.2s for testing speed

    # Mock the execute_component function and sleep
    with patch("src.aurite.testing.qa.qa_utils.execute_component", side_effect=mock_execute_with_rate_limit):
        with patch("asyncio.sleep", side_effect=mock_sleep):
            # Mock the LLM client and expectation analysis
            with patch("src.aurite.testing.qa.qa_utils.get_llm_client", return_value=AsyncMock()):
                with patch(
                    "src.aurite.testing.qa.qa_utils.analyze_expectations",
                    return_value=AsyncMock(analysis="All expectations met", expectations_broken=[]),
                ):
                    # Run the evaluation
                    start_time = time.time()
                    result = await tester.test_component(request, None)
                    total_time = time.time() - start_time

    # Verify results
    logger.info("\n  Results:")
    logger.info(f"    Retry attempts per case: {retry_attempts}")
    logger.info(f"    Retry delays observed: {[f'{d:.3f}s' for d in retry_delays]}")
    logger.info(f"    Total execution time: {total_time:.2f}s")
    logger.info(f"    Passed cases: {result.passed_cases}/{result.total_cases}")

    # Verify all cases eventually succeeded after retries
    assert result.passed_cases == 3, f"Expected all 3 cases to pass after retries, got {result.passed_cases}"

    # Verify exponential backoff pattern (with jitter, so check ranges)
    if len(retry_delays) >= 2:
        # First retry should be around base_delay (0.1s)
        assert 0.05 <= retry_delays[0] <= 0.15, f"First delay out of range: {retry_delays[0]}"
        # Second retry should be around base_delay * 2 (0.2s)
        if len(retry_delays) > 3:  # Multiple test cases might have retries
            # Find delays that are likely second retries
            second_retries = [d for d in retry_delays if 0.15 < d < 0.35]
            assert len(second_retries) > 0, "No second retry delays found in expected range"

    logger.info("  ✅ Test passed: Rate limit retry with exponential backoff working")
    return True


async def test_custom_config():
    """Test that custom configuration parameters are properly used."""
    logger.info("\n" + "=" * 80)
    logger.info("Test 3: Custom Configuration Parameters")
    logger.info("=" * 80)

    # Create test cases
    test_cases = [
        EvaluationCase(name=f"config_test_{i}", input=f"Input {i}", expectations=[f"Expectation {i}"]) for i in range(5)
    ]

    # Create evaluation request with custom configuration
    request = EvaluationRequest(
        component_type="agent",
        test_cases=test_cases,
        max_concurrent_tests=2,  # Custom concurrent limit
        rate_limit_retry_count=5,  # Custom retry count
        rate_limit_base_delay=2.0,  # Custom base delay
        use_cache=False,
    )

    # Create tester with custom ComponentQAConfig
    config = ComponentQAConfig(
        component_type="test",
        max_concurrent_tests=10,  # This should be overridden by request
        rate_limit_retry_count=10,  # This should be overridden by request
        rate_limit_base_delay=5.0,  # This should be overridden by request
    )
    tester = ComponentQATester(config)

    # Mock execute_component to just return quickly
    async def mock_execute_quick(case, request, executor, mcp_test_agents):
        await asyncio.sleep(0.01)
        return f"Output for {case.name}"

    with patch("src.aurite.testing.qa.qa_utils.execute_component", side_effect=mock_execute_quick):
        # Mock the LLM client and expectation analysis
        with patch("src.aurite.testing.qa.qa_utils.get_llm_client", return_value=AsyncMock()):
            with patch(
                "src.aurite.testing.qa.qa_utils.analyze_expectations",
                return_value=AsyncMock(analysis="All expectations met", expectations_broken=[]),
            ):
                # Run the evaluation
                result = await tester.test_component(request, None)

    # Verify the request parameters were used
    # Check by looking at the tester's semaphore value
    assert tester._semaphore._value == 2, f"Expected semaphore value 2, got {tester._semaphore._value}"

    logger.info("  Results:")
    logger.info(f"    Semaphore limit (from request): {2}")
    logger.info(f"    Test cases executed: {result.total_cases}")
    logger.info(f"    All passed: {result.passed_cases == result.total_cases}")

    logger.info("  ✅ Test passed: Custom configuration parameters properly used")
    return True


async def main():
    """Run all rate limiting tests."""
    logger.info("Starting Rate Limiting Tests")
    logger.info("=" * 80)

    results = []

    # Test 1: Concurrent execution limit
    try:
        result = await test_concurrent_execution_limit()
        results.append(("Concurrent Execution Limit", result))
    except Exception as e:
        logger.error(f"Test 1 failed: {e}")
        results.append(("Concurrent Execution Limit", False))

    # Test 2: Rate limit retry
    try:
        result = await test_rate_limit_retry()
        results.append(("Rate Limit Retry", result))
    except Exception as e:
        logger.error(f"Test 2 failed: {e}")
        results.append(("Rate Limit Retry", False))

    # Test 3: Custom configuration
    try:
        result = await test_custom_config()
        results.append(("Custom Configuration", result))
    except Exception as e:
        logger.error(f"Test 3 failed: {e}")
        results.append(("Custom Configuration", False))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        logger.info("\n🎉 All rate limiting tests passed!")
    else:
        logger.info("\n❌ Some tests failed. Please review the output above.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
