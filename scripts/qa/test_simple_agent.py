#!/usr/bin/env python3
"""
Simple test to verify agent configuration and execution.
"""

import asyncio
import sys
import uuid
from pathlib import Path

import httpx

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


async def test_simple_agent():
    """Test a simple agent with minimal expectations."""

    api_url = "http://localhost:8000"
    api_key = "test-api-key"

    # Create a very simple test case with a proper UUID
    test_case = {
        "id": str(uuid.uuid4()),
        "input": "Hello, can you help me?",
        "expectations": ["The response is coherent", "The response attempts to be helpful"],
    }

    # Create a minimal agent config

    eval_request = {
        "eval_name": "Weather Agent",
        "eval_type": "agent",
        "test_cases": [test_case],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{api_url}/testing/evaluate", json=eval_request, headers={"X-API-Key": api_key})

        if response.status_code == 200:
            result = response.json()
            print(f"Status: {result.get('status')}")
            print(f"Score: {result.get('overall_score')}%")
            print(f"Passed: {result.get('passed_cases')}/{result.get('total_cases')}")

            # Print case results
            case_results = result.get("case_results", {})
            for case_id, case_result in case_results.items():
                print(f"\nCase {case_id}:")
                print(f"  Grade: {case_result.get('grade')}")
                print(f"  Analysis: {case_result.get('analysis')}")
                if case_result.get("expectations_broken"):
                    print(f"  Broken expectations: {case_result.get('expectations_broken')}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)


if __name__ == "__main__":
    asyncio.run(test_simple_agent())
