#!/usr/bin/env python3
"""
Test script to verify that workflows with agents that have include_history: true
properly save conversation history when a session_id is provided.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
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


async def create_test_workflow():
    """Create a test workflow with agents that have include_history: true."""
    async with httpx.AsyncClient() as client:
        # Create a simple workflow with two agents that both have include_history: true
        workflow_config = {
            "name": "Test History Workflow",
            "type": "linear_workflow",
            "description": "Test workflow with history-enabled agents",
            "steps": ["Conversation History Weather Agent", "Weather Planning Workflow Step 2"],
        }

        response = await client.post(
            f"{API_BASE_URL}/config/linear_workflow", headers=HEADERS, json=workflow_config, timeout=10.0
        )
        return response.status_code == 201


async def run_workflow(workflow_name: str, session_id: str):
    """Run a workflow with a session ID."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/execution/workflows/linear/{workflow_name}/run",
            headers=HEADERS,
            json={
                "initial_input": "What's the weather like in New York and what should I wear?",
                "session_id": session_id,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()


async def main():
    """Test workflow with history-enabled agents."""
    print("=== Testing Workflow with History-Enabled Agents ===")

    # Clean up cache first
    cache_dir = Path(".aurite_cache")
    if cache_dir.exists():
        print("\n🧹 Cleaning up old cache files...")
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass

    # Test with existing workflow
    print("\n📝 Testing with 'Weather Planning Workflow'")
    session_id = f"history-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        print(f"   Running workflow with session ID: {session_id}")
        result = await run_workflow("Weather Planning Workflow", session_id)
        print(f"   ✅ Workflow completed with status: {result.get('status')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Wait for cache writes
    await asyncio.sleep(2)

    # Check cache files
    print("\n📊 Cache Analysis:")
    if cache_dir.exists():
        cache_files = list(cache_dir.glob("*.json"))
        print(f"   Found {len(cache_files)} cache file(s)")

        agents_with_history = []
        for file in cache_files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    if data.get("session_id") == session_id:
                        agent_name = data.get("agent_name")
                        message_count = data.get("message_count", 0)
                        agents_with_history.append(agent_name)
                        print(f"\n   ✅ Agent: {agent_name}")
                        print(f"      Session: {data.get('session_id')}")
                        print(f"      Messages: {message_count}")

                        # Show conversation snippet
                        conversation = data.get("conversation", [])
                        if conversation:
                            print("      First message:")
                            first_msg = conversation[0]
                            print(f"        Role: {first_msg.get('role')}")
                            content = str(first_msg.get("content", ""))[:100]
                            print(f"        Content: {content}...")
            except Exception as e:
                print(f"   Error reading {file}: {e}")

        print("\n📋 Summary:")
        print(f"   Session ID: {session_id}")
        print(f"   Agents with saved history: {len(agents_with_history)}")
        if agents_with_history:
            print(f"   - {', '.join(agents_with_history)}")

        # Expected vs actual
        print("\n🔍 Analysis:")
        expected_agents = ["Weather Agent", "Weather Planning Workflow Step 2"]
        agents_with_include_history = ["Weather Planning Workflow Step 2"]  # Based on config

        print(f"   Expected agents in workflow: {', '.join(expected_agents)}")
        print(f"   Agents with include_history=true: {', '.join(agents_with_include_history)}")
        print(f"   Agents that saved history: {', '.join(agents_with_history)}")

        if set(agents_with_history) == set(agents_with_include_history):
            print("\n   ✅ SUCCESS: All agents with include_history=true saved their conversation history!")
            print("   ✅ Session IDs are being properly passed through linear workflows!")
        else:
            print("\n   ⚠️  Some agents with include_history=true did not save history")
    else:
        print("   ❌ No cache directory found!")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
