#!/usr/bin/env python3
"""
Debug script to understand why workflow history search is returning nothing.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

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


async def run_workflow_with_history(workflow_name: str, session_id: str = None):
    """Run a workflow with a specific session ID."""
    async with httpx.AsyncClient() as client:
        payload = {"initial_input": "What's the weather like in New York?"}
        if session_id:
            payload["session_id"] = session_id
            
        print(f"\n🚀 Running workflow '{workflow_name}' with payload: {json.dumps(payload, indent=2)}")
        
        response = await client.post(
            f"{API_BASE_URL}/execution/workflows/simple/{workflow_name}/run",
            headers=HEADERS,
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Workflow completed with session_id: {result.get('session_id')}")
        return result


async def check_cache_files():
    """Check what files exist in the cache directory."""
    cache_dir = Path(".aurite_cache")
    print(f"\n📁 Checking cache directory: {cache_dir.absolute()}")
    
    if not cache_dir.exists():
        print("❌ Cache directory does not exist!")
        return
    
    files = list(cache_dir.glob("*.json"))
    print(f"Found {len(files)} cache files:")
    
    for file in sorted(files):
        print(f"\n  📄 {file.name}")
        try:
            with open(file, "r") as f:
                data = json.load(f)
                print(f"     - session_id: {data.get('session_id')}")
                print(f"     - agent_name: {data.get('agent_name')}")
                print(f"     - workflow_name: {data.get('workflow_name')}")
                print(f"     - message_count: {data.get('message_count', 0)}")
                print(f"     - agents_involved: {data.get('agents_involved', [])}")
        except Exception as e:
            print(f"     ❌ Error reading file: {e}")


async def search_workflow_history(workflow_name: str):
    """Search for workflow history using the API."""
    print(f"\n🔍 Searching for workflow history: '{workflow_name}'")
    
    # Try the workflow-specific endpoint
    async with httpx.AsyncClient() as client:
        print(f"\n1️⃣ Trying GET /execution/workflows/{workflow_name}/history")
        try:
            response = await client.get(
                f"{API_BASE_URL}/execution/workflows/{workflow_name}/history",
                headers=HEADERS,
                params={"limit": 50},
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            print(f"   Total sessions: {result['total']}")
            print(f"   Sessions returned: {len(result['sessions'])}")
            
            if result['sessions']:
                for session in result['sessions'][:3]:
                    print(f"\n   Session: {session['session_id']}")
                    print(f"   - agent_name: {session.get('agent_name')}")
                    print(f"   - workflow_name: {session.get('workflow_name')}")
                    print(f"   - message_count: {session.get('message_count')}")
            else:
                print("   ⚠️ No sessions found!")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Try the general history endpoint with agent_name filter (old way)
        print(f"\n2️⃣ Trying GET /execution/history?agent_name={workflow_name}")
        try:
            response = await client.get(
                f"{API_BASE_URL}/execution/history",
                headers=HEADERS,
                params={"agent_name": workflow_name, "limit": 50},
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            print(f"   Total sessions: {result['total']}")
            print(f"   Sessions returned: {len(result['sessions'])}")
            
            if result['sessions']:
                for session in result['sessions'][:3]:
                    print(f"\n   Session: {session['session_id']}")
                    print(f"   - agent_name: {session.get('agent_name')}")
                    print(f"   - workflow_name: {session.get('workflow_name')}")
                    print(f"   - message_count: {session.get('message_count')}")
            else:
                print("   ⚠️ No sessions found!")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Try the general history endpoint with workflow_name filter (new way)
        print(f"\n3️⃣ Trying GET /execution/history?workflow_name={workflow_name}")
        try:
            response = await client.get(
                f"{API_BASE_URL}/execution/history",
                headers=HEADERS,
                params={"workflow_name": workflow_name, "limit": 50},
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            print(f"   Total sessions: {result['total']}")
            print(f"   Sessions returned: {len(result['sessions'])}")
            
            if result['sessions']:
                for session in result['sessions'][:3]:
                    print(f"\n   Session: {session['session_id']}")
                    print(f"   - agent_name: {session.get('agent_name')}")
                    print(f"   - workflow_name: {session.get('workflow_name')}")
                    print(f"   - message_count: {session.get('message_count')}")
            else:
                print("   ⚠️ No sessions found!")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Try without any filters
        print(f"\n4️⃣ Trying GET /execution/history (no filters)")
        try:
            response = await client.get(
                f"{API_BASE_URL}/execution/history",
                headers=HEADERS,
                params={"limit": 50},
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            print(f"   Total sessions: {result['total']}")
            print(f"   Sessions returned: {len(result['sessions'])}")
            
            # Look for our workflow in the results
            workflow_sessions = [s for s in result['sessions'] if s.get('workflow_name') == workflow_name]
            print(f"   Sessions with workflow_name='{workflow_name}': {len(workflow_sessions)}")
            
            if workflow_sessions:
                for session in workflow_sessions[:3]:
                    print(f"\n   Session: {session['session_id']}")
                    print(f"   - agent_name: {session.get('agent_name')}")
                    print(f"   - workflow_name: {session.get('workflow_name')}")
                    print(f"   - message_count: {session.get('message_count')}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def check_workflow_config(workflow_name: str):
    """Check the workflow configuration."""
    print(f"\n⚙️ Checking workflow configuration for '{workflow_name}'")
    
    config_path = Path("tests/fixtures/workspace/shared_configs/example_multi_component.json")
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return
    
    with open(config_path, "r") as f:
        configs = json.load(f)
    
    workflow_config = None
    for config in configs:
        if config.get("name") == workflow_name and config.get("type") == "simple_workflow":
            workflow_config = config
            break
    
    if workflow_config:
        print(f"✅ Found workflow configuration:")
        print(f"   - include_history: {workflow_config.get('include_history')}")
        print(f"   - steps: {len(workflow_config.get('steps', []))}")
        
        # Check agent configurations
        print(f"\n   Checking agent configurations:")
        for step in workflow_config.get('steps', []):
            agent_name = step if isinstance(step, str) else step.get('name')
            agent_config = None
            for config in configs:
                if config.get("name") == agent_name and config.get("type") == "agent":
                    agent_config = config
                    break
            if agent_config:
                print(f"   - {agent_name}: include_history={agent_config.get('include_history')}")
            else:
                print(f"   - {agent_name}: ❌ Not found in config")
    else:
        print(f"❌ Workflow '{workflow_name}' not found in config!")


async def main():
    """Debug workflow history search issue."""
    print("=== Debugging Workflow History Search ===")
    
    workflow_name = "Weather Planning Workflow"
    
    # Step 1: Check workflow configuration
    await check_workflow_config(workflow_name)
    
    # Step 2: Run a workflow with include_history=true
    print(f"\n📝 Running workflow to create history...")
    session_id = f"debug-workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    result = await run_workflow_with_history(workflow_name, session_id)
    
    # Wait a bit for history to be saved
    await asyncio.sleep(2)
    
    # Step 3: Check cache files
    await check_cache_files()
    
    # Step 4: Search for workflow history
    await search_workflow_history(workflow_name)
    
    # Step 5: Try to get specific session details
    if result.get('session_id'):
        print(f"\n📋 Getting details for session: {result['session_id']}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{API_BASE_URL}/execution/history/{result['session_id']}",
                    headers=HEADERS,
                    timeout=10.0
                )
                response.raise_for_status()
                details = response.json()
                print(f"   ✅ Session found:")
                print(f"   - agent_name: {details.get('agent_name')}")
                print(f"   - messages: {len(details.get('messages', []))}")
                print(f"   - metadata.workflow_name: {details.get('metadata', {}).get('workflow_name')}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    print("\n=== Debug Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
