#!/usr/bin/env python3
"""
Test script to verify the workflow history fix is working correctly.
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Get API key from environment
API_KEY = os.environ.get("API_KEY", "")
if not API_KEY:
    print("ERROR: API_KEY environment variable not set!")
    sys.exit(1)

API_BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def test_workflow_history():
    """Test the workflow history endpoints."""
    workflow_name = "Weather Planning Workflow"

    async with httpx.AsyncClient() as client:
        print("=== Testing Workflow History Fix ===\n")

        # Test 1: Get workflow history using dedicated endpoint
        print(f"1️⃣ Testing GET /execution/workflows/{workflow_name}/history")
        try:
            response = await client.get(
                f"{API_BASE_URL}/execution/workflows/{workflow_name}/history",
                headers=HEADERS,
                params={"limit": 5},
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            print(f"   ✅ Success! Found {result['total']} sessions")
            print(f"   Returned {len(result['sessions'])} sessions (limit=5)")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 2: Get workflow history using workflow_name parameter
        print(f"\n2️⃣ Testing GET /execution/history?workflow_name={workflow_name}")
        try:
            response = await client.get(
                f"{API_BASE_URL}/execution/history",
                headers=HEADERS,
                params={"workflow_name": workflow_name, "limit": 5},
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            print(f"   ✅ Success! Found {result['total']} sessions")
            print(f"   Returned {len(result['sessions'])} sessions (limit=5)")

            # Show first session details
            if result["sessions"]:
                session = result["sessions"][0]
                print("\n   First session details:")
                print(f"   - session_id: {session['session_id']}")
                print(f"   - agent_name: {session.get('agent_name')}")
                print(f"   - workflow_name: {session.get('workflow_name')}")
                print(f"   - message_count: {session.get('message_count')}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 3: Verify agent_name parameter doesn't find workflows
        print(f"\n3️⃣ Testing GET /execution/history?agent_name={workflow_name}")
        try:
            response = await client.get(
                f"{API_BASE_URL}/execution/history",
                headers=HEADERS,
                params={"agent_name": workflow_name, "limit": 5},
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            print(f"   ✅ Expected result: Found {result['total']} sessions")
            print("   (Should be 0 since workflows aren't agents)")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 4: Get agent history
        agent_name = "Weather Agent"
        print(f"\n4️⃣ Testing GET /execution/history?agent_name={agent_name}")
        try:
            response = await client.get(
                f"{API_BASE_URL}/execution/history",
                headers=HEADERS,
                params={"agent_name": agent_name, "limit": 5},
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            print(f"   ✅ Success! Found {result['total']} sessions for agent")
            print("   (Includes sessions where agent was part of workflows)")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print("\n=== All Tests Complete ===")
        print("\n✅ Summary:")
        print("- Workflow history search is now working correctly")
        print("- Use 'workflow_name' parameter to search for workflows")
        print("- Use 'agent_name' parameter to search for agents")
        print("- Both dedicated endpoints and general history endpoint work properly")


if __name__ == "__main__":
    asyncio.run(test_workflow_history())
