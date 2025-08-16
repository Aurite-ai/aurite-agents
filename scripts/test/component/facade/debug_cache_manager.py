#!/usr/bin/env python3
"""
Debug script to check if CacheManager is properly initialized in the API.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx

# Get API key from environment
API_KEY = os.environ.get("API_KEY", "")
if not API_KEY:
    print("ERROR: API_KEY environment variable not set!")
    sys.exit(1)

API_BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def check_facade_status():
    """Check the engine status endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/execution/status", headers=HEADERS, timeout=10.0)
        response.raise_for_status()
        return response.json()


async def run_agent_with_history(agent_name: str, session_id: str):
    """Run an agent with include_history and session_id."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/execution/agents/{agent_name}/run",
            headers=HEADERS,
            json={"user_message": "Test message for cache debugging", "session_id": session_id},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()


async def main():
    """Debug the cache manager initialization."""
    print("=== Debugging Cache Manager ===")

    # Check engine status
    print("\n1️⃣ Checking engine status...")
    try:
        status = await check_facade_status()
        print(f"   ✅ Facade status: {status}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # Test with an agent that has include_history: true
    print("\n2️⃣ Testing with 'Conversation History Weather Agent'...")
    session_id = "debug-cache-test"

    try:
        result = await run_agent_with_history(agent_name="Conversation History Weather Agent", session_id=session_id)
        print(f"   ✅ Agent completed with status: {result.get('status')}")
        print(f"   Conversation history length: {len(result.get('conversation_history', []))}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Check cache directory
    print("\n3️⃣ Checking cache directory...")
    cache_dir = Path(".aurite_cache")
    print(f"   Cache directory: {cache_dir.absolute()}")
    print(f"   Exists: {cache_dir.exists()}")

    if cache_dir.exists():
        files = list(cache_dir.glob("*.json"))
        print(f"   Files found: {len(files)}")
        for file in files:
            print(f"   - {file.name}")
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    print(f"     Session ID: {data.get('session_id')}")
                    print(f"     Agent: {data.get('agent_name')}")
                    print(f"     Messages: {data.get('message_count', 0)}")
            except Exception as e:
                print(f"     Error reading: {e}")

    # Also check if .aurite_cache was created in the wrong location
    print("\n4️⃣ Checking for cache in other locations...")
    possible_locations = [
        Path.cwd() / ".aurite_cache",
        Path.home() / ".aurite_cache",
        Path(__file__).parent.parent.parent / ".aurite_cache",
    ]

    for location in possible_locations:
        if location.exists() and location.is_dir():
            print(f"   Found cache directory at: {location}")
            files = list(location.glob("*.json"))
            if files:
                print(f"   Contains {len(files)} files")


if __name__ == "__main__":
    asyncio.run(main())
