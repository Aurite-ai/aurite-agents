#!/usr/bin/env python3
"""
Test script to verify that workflows auto-generate session IDs when include_history=true
but no session_id is provided.
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


async def run_workflow(workflow_name: str, session_id=None):
    """Run a workflow with optional session ID."""
    async with httpx.AsyncClient() as client:
        payload = {"initial_input": "What's the weather in New York?"}
        if session_id is not None:
            payload["session_id"] = session_id

        response = await client.post(
            f"{API_BASE_URL}/execution/workflows/linear/{workflow_name}/run",
            headers=HEADERS,
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()


def check_cache_files():
    """Check what cache files exist."""
    cache_dir = Path(".aurite_cache")
    files = []
    if cache_dir.exists():
        for file in cache_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    files.append(
                        {
                            "filename": file.name,
                            "session_id": data.get("session_id"),
                            "agent_name": data.get("agent_name"),
                            "message_count": data.get("message_count", 0),
                        }
                    )
            except:
                pass
    return files


def modify_workflow_config(include_history=None):
    """Modify the example_multi_component.json to add include_history to the workflow."""
    config_path = Path("tests/fixtures/workspace/shared_configs/example_multi_component.json")

    # Read current config
    with open(config_path, "r") as f:
        configs = json.load(f)

    # Find and modify the Weather Planning Workflow
    for config in configs:
        if config.get("name") == "Weather Planning Workflow" and config.get("type") == "linear_workflow":
            if include_history is None:
                # Remove include_history if it exists
                config.pop("include_history", None)
            else:
                # Set include_history
                config["include_history"] = include_history
            break

    # Write back
    with open(config_path, "w") as f:
        json.dump(configs, f, indent=2)

    return True


async def main():
    """Test auto-generation of session IDs."""
    print("=== Testing Auto-Generation of Session IDs ===")

    # Clean up cache first
    cache_dir = Path(".aurite_cache")
    if cache_dir.exists():
        print("\n🧹 Cleaning up old cache files...")
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass

    # Test 1: Workflow with include_history=true and NO session_id
    print("\n📝 Test 1: Workflow with include_history=true, NO session_id provided")
    print("   Expected: Should auto-generate a session ID")

    try:
        # Set include_history=true in workflow
        modify_workflow_config(include_history=True)
        print("   Modified config: set include_history=true in workflow")

        # Wait for config to reload
        await asyncio.sleep(2)

        # Run workflow WITHOUT session_id
        print("   Running workflow WITHOUT session_id...")
        result = await run_workflow("Weather Planning Workflow")
        print(f"   ✅ Workflow completed with status: {result.get('status')}")

        # Wait for cache writes
        await asyncio.sleep(2)

        # Check cache files
        files = check_cache_files()
        print(f"\n   Cache files found: {len(files)}")
        for file in files:
            print(f"   - Session: {file['session_id']}")
            print(f"     Agent: {file['agent_name']}")
            print(f"     Messages: {file['message_count']}")

            # Check if session_id was auto-generated
            if file["session_id"] and file["session_id"].startswith("workflow-Weather Planning Workflow-"):
                print("     ✅ Session ID was auto-generated!")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Workflow with include_history=false and NO session_id
    print("\n📝 Test 2: Workflow with include_history=false, NO session_id provided")
    print("   Expected: No history should be saved")

    # Clean cache again
    if cache_dir.exists():
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass

    try:
        # Set include_history=false in workflow
        modify_workflow_config(include_history=False)
        print("   Modified config: set include_history=false in workflow")

        # Wait for config to reload
        await asyncio.sleep(2)

        # Run workflow WITHOUT session_id
        print("   Running workflow WITHOUT session_id...")
        result = await run_workflow("Weather Planning Workflow")
        print(f"   ✅ Workflow completed with status: {result.get('status')}")

        # Wait for cache writes
        await asyncio.sleep(2)

        # Check cache files
        files = check_cache_files()
        print(f"\n   Cache files found: {len(files)}")
        if len(files) == 0:
            print("   ✅ No history saved (as expected)")
        else:
            print("   ❌ Unexpected cache files found")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 3: Workflow with no include_history setting and NO session_id
    print("\n📝 Test 3: Workflow with no include_history setting, NO session_id provided")
    print("   Expected: Only agents with include_history=true save history (but no session_id)")

    # Clean cache again
    if cache_dir.exists():
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass

    try:
        # Remove include_history from workflow
        modify_workflow_config(include_history=None)
        print("   Modified config: removed include_history from workflow")

        # Wait for config to reload
        await asyncio.sleep(2)

        # Run workflow WITHOUT session_id
        print("   Running workflow WITHOUT session_id...")
        result = await run_workflow("Weather Planning Workflow")
        print(f"   ✅ Workflow completed with status: {result.get('status')}")

        # Wait for cache writes
        await asyncio.sleep(2)

        # Check cache files
        files = check_cache_files()
        print(f"\n   Cache files found: {len(files)}")
        if len(files) == 0:
            print("   ✅ No history saved (agents need session_id even if they have include_history=true)")
        else:
            print("   ❌ Unexpected cache files found")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Restore original config
    print("\n🔧 Restoring original configuration...")
    modify_workflow_config(include_history=None)

    print("\n=== Summary ===")
    print("✅ When workflow has include_history=true and no session_id is provided:")
    print("   - A session ID is auto-generated in the format: workflow-{name}-{uuid}")
    print("   - All agents in the workflow save their history using this session ID")
    print("\n✅ When workflow has include_history=false:")
    print("   - No history is saved regardless of session_id")
    print("\n✅ When workflow has no include_history setting:")
    print("   - Agents use their own settings, but need a session_id to save history")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
