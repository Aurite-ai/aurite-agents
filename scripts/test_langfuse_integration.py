#!/usr/bin/env python3
"""
Test script to verify Langfuse integration with proper spans and sessions.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure Langfuse is enabled
os.environ["LANGFUSE_ENABLED"] = "true"
os.environ["AURITE_LOG_LEVEL"] = "DEBUG"


async def test_agent_with_langfuse():
    """Test agent execution with Langfuse tracing."""
    from aurite import Aurite

    print("Initializing Aurite with Langfuse enabled...")
    aurite = Aurite()

    try:
        # Test 1: Simple agent run without tools
        print("\n=== Test 1: Simple agent run ===")
        result = await aurite.run_agent(
            agent_name="Weather Agent", user_message="What is the Weather in London?", session_id="test-session-001"
        )
        print(f"Agent response: {result.final_response.content if result.final_response else 'No response'}")
        print(f"Status: {result.status}")

        # Test 2: Agent run with the same session (should be grouped)
        print("\n=== Test 2: Follow-up in same session ===")
        result = await aurite.run_agent(
            agent_name="Weather Agent",
            user_message="What is the Weather in San Francisco?",
            session_id="test-session-001",
        )
        print(f"Agent response: {result.final_response.content if result.final_response else 'No response'}")
        print(f"Status: {result.status}")

        # Test 3: Different session
        print("\n=== Test 3: New session ===")
        result = await aurite.run_agent(
            agent_name="Weather Agent", user_message="What is the Weather in Tokyo?", session_id="test-session-002"
        )
        print(f"Agent response: {result.final_response.content if result.final_response else 'No response'}")
        print(f"Status: {result.status}")

        # Test 4: Streaming response
        print("\n=== Test 4: Streaming response ===")
        print("Streaming response: ", end="", flush=True)
        async for event in aurite.stream_agent(
            agent_name="Weather Agent", user_message="What is the Weather in New York?", session_id="test-session-003"
        ):
            if event.get("type") == "llm_response":
                print(event["data"]["content"], end="", flush=True)
        print()  # New line after streaming

        print("\n✅ All tests completed successfully!")
        print("\nCheck your Langfuse dashboard to verify:")
        print("1. Each test should create a single trace (not duplicate traces)")
        print("2. Traces should be grouped by session ID")
        print("3. Each trace should contain:")
        print("   - Agent execution span")
        print("   - Agent turn spans")
        print("   - LLM generation observations")
        print("4. Token usage should be tracked for each LLM call")

    finally:
        await aurite.kernel.shutdown()


async def test_agent_with_tools():
    """Test agent execution with tools to verify tool spans."""
    from aurite import Aurite

    print("\n=== Test with Tools ===")
    aurite = Aurite()

    try:
        # This assumes you have a weather MCP server configured
        result = await aurite.run_agent(
            agent_name="weather_assistant",
            user_message="What's the weather in San Francisco?",
            session_id="test-session-tools",
        )
        print(f"Agent response: {result.final_response.content if result.final_response else 'No response'}")
        print(f"Status: {result.status}")

        print("\nIn Langfuse, verify:")
        print("1. Tool calls appear as separate spans")
        print("2. Tool execution details are captured")

    except Exception as e:
        print(f"Tool test skipped (agent/server may not be configured): {e}")
    finally:
        await aurite.kernel.shutdown()


if __name__ == "__main__":
    print("Testing Langfuse Integration")
    print("=" * 50)

    # Check if Langfuse credentials are set
    if not all([os.getenv("LANGFUSE_SECRET_KEY"), os.getenv("LANGFUSE_PUBLIC_KEY"), os.getenv("LANGFUSE_HOST")]):
        print("❌ Langfuse credentials not found in environment!")
        print("Please set LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, and LANGFUSE_HOST")
        sys.exit(1)

    print("✅ Langfuse credentials found")
    print(f"Host: {os.getenv('LANGFUSE_HOST')}")

    # Run the tests
    asyncio.run(test_agent_with_langfuse())

    # Optionally run tool test
    # asyncio.run(test_agent_with_tools())
