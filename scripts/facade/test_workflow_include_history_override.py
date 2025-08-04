#!/usr/bin/env python3
"""
Test script to verify that the workflow-level include_history setting
properly overrides individual agent settings.
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


async def create_test_workflow(name: str, include_history: bool = None):
    """Create a test workflow with specific include_history setting."""
    async with httpx.AsyncClient() as client:
        workflow_config = {
            "name": name,
            "type": "linear_workflow",
            "description": f"Test workflow with include_history={include_history}",
            "steps": ["Weather Agent", "Weather Planning Workflow Step 2"],
        }

        if include_history is not None:
            workflow_config["include_history"] = include_history

        response = await client.post(
            f"{API_BASE_URL}/config/linear_workflow", headers=HEADERS, json=workflow_config, timeout=10.0
        )
        return response.status_code == 201


async def run_workflow(workflow_name: str, session_id: str):
    """Run a workflow with a session ID."""
    async with httpx.AsyncClient() as client:
        payload = {"initial_input": "What's the weather like in New York?", "session_id": session_id}
        response = await client.post(
            f"{API_BASE_URL}/execution/workflows/linear/{workflow_name}/run",
            headers=HEADERS,
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()


async def delete_workflow(workflow_name: str):
    """Delete a workflow configuration."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{API_BASE_URL}/config/linear_workflow/{workflow_name}", headers=HEADERS, timeout=10.0
        )
        return response.status_code in [200, 204, 404]


def analyze_cache_for_session(session_id: str):
    """Analyze cache files for a specific session."""
    cache_dir = Path(".aurite_cache")
    agents_with_history = []

    if cache_dir.exists():
        for file in cache_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    if data.get("session_id") == session_id:
                        agents_with_history.append(data.get("agent_name"))
            except:
                pass

    return agents_with_history


async def main():
    """Test workflow-level include_history override."""
    print("=== Testing Workflow-Level include_history Override ===")

    # Clean up cache first
    cache_dir = Path(".aurite_cache")
    if cache_dir.exists():
        print("\n🧹 Cleaning up old cache files...")
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass

    # Test 1: Workflow with include_history=true (should save history for ALL agents)
    print("\n📝 Test 1: Workflow with include_history=true")
    workflow_name = "Test Workflow History True"
    session_id = f"test-true-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        # Create workflow
        if await create_test_workflow(workflow_name, include_history=True):
            print(f"   ✅ Created workflow: {workflow_name}")
        else:
            print("   ❌ Failed to create workflow")
            return

        # Run workflow
        print(f"   Running with session ID: {session_id}")
        result = await run_workflow(workflow_name, session_id)
        print(f"   ✅ Workflow completed with status: {result.get('status')}")

        # Wait for cache writes
        await asyncio.sleep(2)

        # Check cache
        agents = analyze_cache_for_session(session_id)
        print(f"   Agents that saved history: {len(agents)}")
        for agent in agents:
            print(f"   - {agent}")

        # Clean up
        await delete_workflow(workflow_name)

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Workflow with include_history=false (should NOT save history for any agents)
    print("\n📝 Test 2: Workflow with include_history=false")
    workflow_name = "Test Workflow History False"
    session_id = f"test-false-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        # Create workflow
        if await create_test_workflow(workflow_name, include_history=False):
            print(f"   ✅ Created workflow: {workflow_name}")
        else:
            print("   ❌ Failed to create workflow")
            return

        # Run workflow
        print(f"   Running with session ID: {session_id}")
        result = await run_workflow(workflow_name, session_id)
        print(f"   ✅ Workflow completed with status: {result.get('status')}")

        # Wait for cache writes
        await asyncio.sleep(2)

        # Check cache
        agents = analyze_cache_for_session(session_id)
        print(f"   Agents that saved history: {len(agents)}")
        if agents:
            for agent in agents:
                print(f"   - {agent}")
        else:
            print("   (None - as expected)")

        # Clean up
        await delete_workflow(workflow_name)

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 3: Workflow with no include_history setting (should use agent's own settings)
    print("\n📝 Test 3: Workflow with no include_history setting (default behavior)")
    session_id = f"test-default-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        # Use existing workflow
        print("   Using existing 'Weather Planning Workflow'")
        print(f"   Running with session ID: {session_id}")
        result = await run_workflow("Weather Planning Workflow", session_id)
        print(f"   ✅ Workflow completed with status: {result.get('status')}")

        # Wait for cache writes
        await asyncio.sleep(2)

        # Check cache
        agents = analyze_cache_for_session(session_id)
        print(f"   Agents that saved history: {len(agents)}")
        for agent in agents:
            print(f"   - {agent}")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print("\n📊 Summary:")
    print("   Based on the configuration:")
    print("   - 'Weather Agent' has include_history: false (first definition)")
    print("   - 'Weather Planning Workflow Step 2' has include_history: true")
    print("\n   Expected behavior:")
    print("   - Test 1 (workflow include_history=true): Both agents should save history")
    print("   - Test 2 (workflow include_history=false): No agents should save history")
    print("   - Test 3 (workflow no setting): Only 'Weather Planning Workflow Step 2' should save history")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
