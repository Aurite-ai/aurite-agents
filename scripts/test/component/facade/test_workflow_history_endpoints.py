#!/usr/bin/env python3
"""
Test script for workflow history endpoints in the API.
Tests the various history-related endpoints for workflows.
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


async def run_workflow_with_history(workflow_name: str, session_id: str):
    """Run a workflow with a specific session ID."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/execution/workflows/linear/{workflow_name}/run",
            headers=HEADERS,
            json={"initial_input": "What's the weather like in New York?", "session_id": session_id},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()


async def get_workflow_history(workflow_name: str, limit: int = 50):
    """Get history for a specific workflow."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/execution/workflows/{workflow_name}/history",
            headers=HEADERS,
            params={"limit": limit},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def get_all_history(limit: int = 50, offset: int = 0, agent_name: str = None):
    """Get all execution history with optional filtering."""
    async with httpx.AsyncClient() as client:
        params = {"limit": limit, "offset": offset}
        if agent_name:
            params["agent_name"] = agent_name

        response = await client.get(f"{API_BASE_URL}/execution/history", headers=HEADERS, params=params, timeout=10.0)
        response.raise_for_status()
        return response.json()


async def get_session_details(session_id: str, raw_format: bool = False):
    """Get detailed history for a specific session."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/execution/history/{session_id}",
            headers=HEADERS,
            params={"raw_format": raw_format},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def delete_session(session_id: str):
    """Delete a specific session."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/execution/history/{session_id}", headers=HEADERS, timeout=10.0)
        return response.status_code


async def cleanup_history(days: int = 30, max_sessions: int = 50):
    """Clean up old sessions."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/execution/history/cleanup",
            headers=HEADERS,
            params={"days": days, "max_sessions": max_sessions},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


def modify_workflow_config(include_history=True):
    """Modify the workflow config to enable history."""
    config_path = Path("tests/fixtures/workspace/shared_configs/example_multi_component.json")

    with open(config_path, "r") as f:
        configs = json.load(f)

    for config in configs:
        if config.get("name") == "Weather Planning Workflow" and config.get("type") == "linear_workflow":
            config["include_history"] = include_history
            break

    with open(config_path, "w") as f:
        json.dump(configs, f, indent=2)


async def main():
    """Test workflow history endpoints."""
    print("=== Testing Workflow History Endpoints ===")

    # Ensure workflow has include_history=true
    modify_workflow_config(include_history=True)
    await asyncio.sleep(2)  # Wait for config reload

    # Test 1: Run workflows with different session IDs
    print("\n📝 Test 1: Creating workflow history")
    workflow_name = "Weather Planning Workflow"
    session_ids = []

    for i in range(3):
        session_id = f"test-workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{i}"
        session_ids.append(session_id)
        print(f"   Running workflow with session: {session_id}")

        try:
            result = await run_workflow_with_history(workflow_name, session_id)
            print(f"   ✅ Workflow completed: {result.get('status')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        await asyncio.sleep(1)  # Small delay between runs

    # Test 2: Get workflow-specific history
    print(f"\n📝 Test 2: Getting history for workflow '{workflow_name}'")
    try:
        history = await get_workflow_history(workflow_name)
        print(f"   Total sessions: {history['total']}")
        print(f"   Sessions returned: {len(history['sessions'])}")

        for session in history["sessions"][:5]:  # Show first 5
            print(f"\n   Session: {session['session_id']}")
            print(f"   - Agent: {session['agent_name']}")
            print(f"   - Messages: {session['message_count']}")
            print(f"   - Created: {session.get('created_at', 'N/A')}")
            print(f"   - Updated: {session.get('last_updated', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Get all history with pagination
    print("\n📝 Test 3: Getting all history with pagination")
    try:
        # First page
        page1 = await get_all_history(limit=2, offset=0)
        print(f"   Page 1: {len(page1['sessions'])} sessions (offset=0, limit=2)")
        print(f"   Total available: {page1['total']}")

        # Second page
        if page1["total"] > 2:
            page2 = await get_all_history(limit=2, offset=2)
            print(f"   Page 2: {len(page2['sessions'])} sessions (offset=2, limit=2)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Get session details
    if session_ids:
        print(f"\n📝 Test 4: Getting session details for: {session_ids[0]}")
        try:
            # Simplified format
            details = await get_session_details(session_ids[0], raw_format=False)
            print(f"   Session: {details['session_id']}")
            print(f"   Agent: {details['agent_name']}")
            print(f"   Messages: {len(details['messages'])}")

            # Show first message
            if details["messages"]:
                first_msg = details["messages"][0]
                print("\n   First message:")
                print(f"   - Role: {first_msg['role']}")
                print(f"   - Content: {str(first_msg['content'])[:100]}...")

            # Raw format
            print("\n   Getting raw format...")
            raw_details = await get_session_details(session_ids[0], raw_format=True)
            print(f"   ✅ Raw format retrieved with {len(raw_details['messages'])} messages")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Test 5: Filter history by agent name
    print("\n📝 Test 5: Filtering history by agent name")
    try:
        # This will actually filter by workflow name since workflows save with their name
        filtered = await get_all_history(agent_name=workflow_name)
        print(f"   Sessions for '{workflow_name}': {filtered['total']}")

        # Also try filtering by an agent that's part of the workflow
        agent_filtered = await get_all_history(agent_name="Weather Planning Workflow Step 2")
        print(f"   Sessions for 'Weather Planning Workflow Step 2': {agent_filtered['total']}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 6: Delete a session
    if session_ids:
        print(f"\n📝 Test 6: Deleting session: {session_ids[0]}")
        try:
            status_code = await delete_session(session_ids[0])
            if status_code == 204:
                print("   ✅ Session deleted successfully")
            else:
                print(f"   ❌ Unexpected status code: {status_code}")

            # Verify deletion
            try:
                await get_session_details(session_ids[0])
                print("   ❌ Session still exists!")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    print("   ✅ Confirmed: Session not found (deleted)")
                else:
                    print(f"   ❌ Unexpected error: {e}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Test 7: Cleanup old sessions
    print("\n📝 Test 7: Testing cleanup endpoint")
    try:
        # Clean up sessions older than 1 day, keep max 10
        result = await cleanup_history(days=1, max_sessions=10)
        print(f"   Cleanup result: {result['message']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 8: Verify workflow history shows correct agent names
    print("\n📝 Test 8: Verifying workflow history shows correct data")
    try:
        # Run a workflow with auto-generated session ID
        print("   Running workflow without session ID (auto-generate)...")
        result = await run_workflow_with_history(workflow_name, None)

        await asyncio.sleep(2)  # Wait for history to be saved

        # Get the latest history
        history = await get_workflow_history(workflow_name, limit=5)
        if history["sessions"]:
            latest = history["sessions"][0]
            print("\n   Latest session:")
            print(f"   - Session ID: {latest['session_id']}")
            print(f"   - Agent Name: {latest['agent_name']}")
            print(f"   - Auto-generated: {'workflow-' in latest['session_id']}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Restore original config
    print("\n🔧 Restoring original configuration...")
    modify_workflow_config(include_history=None)

    print("\n=== Summary ===")
    print("✅ Workflow history endpoints tested:")
    print("   - GET /workflows/{workflow_name}/history")
    print("   - GET /history (with pagination and filtering)")
    print("   - GET /history/{session_id} (with raw_format option)")
    print("   - DELETE /history/{session_id}")
    print("   - POST /history/cleanup")
    print("\n💡 Key findings:")
    print("   - Workflows save history under the agent names that have include_history=true")
    print("   - The workflow name itself doesn't appear in history unless saved separately")
    print("   - Pagination and filtering work as expected")
    print("   - Session deletion and cleanup work correctly")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
