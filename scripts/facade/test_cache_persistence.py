#!/usr/bin/env python3
"""
Test script to debug cache persistence functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aurite.aurite import Aurite

# Set up logging to see all debug messages
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


async def test_cache_persistence():
    """Test the cache persistence functionality."""
    print("=== Testing Cache Persistence ===")

    # Initialize Aurite with context manager
    print("\n1. Initializing Aurite...")
    async with Aurite() as aurite:
        # Check if cache directory exists
        cache_dir = Path(".aurite_cache")
        print(f"\n2. Checking cache directory: {cache_dir.absolute()}")
        print(f"   Cache directory exists: {cache_dir.exists()}")

        # Run an agent with a session ID
        session_id = "test-session-debug"
        agent_name = "Conversation History Weather Agent"

        print(f"\n3. Running agent '{agent_name}' with session_id: {session_id}")

        try:
            result = await aurite.run_agent(
                agent_name=agent_name, user_message="What is the weather in San Francisco?", session_id=session_id
            )

            print(f"\n4. Agent execution completed with status: {result.status}")
            print(f"   Conversation history length: {len(result.conversation_history)}")

        except Exception as e:
            print(f"\n   ERROR running agent: {e}")
            import traceback

            traceback.print_exc()

        # Check if cache file was created
        print(f"\n5. Checking for cache files in {cache_dir.absolute()}:")
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("*.json"))
            if cache_files:
                for file in cache_files:
                    print(f"   Found: {file.name}")
                    # Read and display file content
                    with open(file, "r") as f:
                        import json

                        data = json.load(f)
                        print(f"   - Session ID: {data.get('session_id')}")
                        print(f"   - Agent: {data.get('agent_name')}")
                        print(f"   - Messages: {data.get('message_count')}")
            else:
                print("   No cache files found!")
        else:
            print("   Cache directory doesn't exist!")

        # Check the cache manager directly
        if hasattr(aurite.kernel, "cache_manager"):
            print("\n6. Checking CacheManager state:")
            cm = aurite.kernel.cache_manager
            print(f"   Cache directory: {cm._cache_dir.absolute()}")
            print(f"   Sessions in memory: {list(cm._history_cache.keys())}")

            # Try to manually save
            print("\n7. Attempting manual save...")
            test_conversation = [
                {"role": "user", "content": "Test message"},
                {"role": "assistant", "content": "Test response"},
            ]
            cm.save_history("manual-test-session", test_conversation, "Test Agent")

            # Check again
            manual_file = cm._cache_dir / "manual-test-session.json"
            print(f"   Manual file exists: {manual_file.exists()}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_cache_persistence())
