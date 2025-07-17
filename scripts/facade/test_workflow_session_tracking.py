#!/usr/bin/env python3
"""
Detailed test to track how session IDs are handled in simple workflows.
This script will:
1. Run individual agents with session IDs to verify they work
2. Run a simple workflow and check if session IDs are propagated
3. Analyze the cache structure
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx

# Set up logging to see all debug messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get API key from environment
API_KEY = os.environ.get("API_KEY", "")
if not API_KEY:
    print("ERROR: API_KEY environment variable not set!")
    sys.exit(1)

API_BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


async def run_agent(agent_name: str, user_message: str, session_id: str):
    """Run a single agent via the API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/execution/agents/{agent_name}/run",
            headers=HEADERS,
            json={
                "user_message": user_message,
                "session_id": session_id
            },
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()


async def run_simple_workflow(workflow_name: str, initial_input: str, session_id: str):
    """Run a simple workflow via the API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/execution/workflows/simple/{workflow_name}/run",
            headers=HEADERS,
            json={
                "initial_input": initial_input,
                "session_id": session_id
            },
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()


def analyze_cache_structure():
    """Analyze the structure of all cache files."""
    cache_dir = Path(".aurite_cache")
    if not cache_dir.exists():
        return {}
    
    cache_structure = {}
    for file in cache_dir.glob("*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                session_id = data.get('session_id', 'unknown')
                agent_name = data.get('agent_name', 'unknown')
                
                if session_id not in cache_structure:
                    cache_structure[session_id] = []
                
                cache_structure[session_id].append({
                    'file': file.name,
                    'agent': agent_name,
                    'messages': data.get('message_count', 0),
                    'created': data.get('created_at', 'N/A'),
                    'updated': data.get('last_updated', 'N/A')
                })
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    return cache_structure


async def main():
    """Test session ID handling in workflows."""
    print("=== Testing Session ID Handling in Simple Workflows ===")
    
    # Clean up old cache files first
    cache_dir = Path(".aurite_cache")
    if cache_dir.exists():
        print("\n🧹 Cleaning up old cache files...")
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass
    
    # Test 1: Individual agent with session ID
    print("\n📝 Test 1: Individual Agent with Session ID")
    agent_session_id = f"agent-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        print(f"   Running 'Weather Agent' with session ID: {agent_session_id}")
        result = await run_agent(
            agent_name="Weather Agent",
            user_message="What's the weather in New York?",
            session_id=agent_session_id
        )
        print(f"   ✅ Agent completed with status: {result.get('status')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Wait for cache write
    await asyncio.sleep(1)
    
    # Check cache
    print("\n   Cache check after individual agent:")
    cache_structure = analyze_cache_structure()
    if agent_session_id in cache_structure:
        print(f"   ✅ Found cache entry for session: {agent_session_id}")
        for entry in cache_structure[agent_session_id]:
            print(f"      - Agent: {entry['agent']}, Messages: {entry['messages']}")
    else:
        print(f"   ❌ No cache entry found for session: {agent_session_id}")
    
    # Test 2: Simple workflow with session ID
    print("\n📝 Test 2: Simple Workflow with Session ID")
    workflow_session_id = f"workflow-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        print(f"   Running 'Weather Planning Workflow' with session ID: {workflow_session_id}")
        result = await run_simple_workflow(
            workflow_name="Weather Planning Workflow",
            initial_input="What should I wear in San Francisco today?",
            session_id=workflow_session_id
        )
        print(f"   ✅ Workflow completed with status: {result.get('status')}")
        
        # Show step results
        step_results = result.get('step_results', [])
        if step_results:
            print("   Steps executed:")
            for i, step in enumerate(step_results):
                print(f"      {i+1}. {step.get('step_name')} ({step.get('step_type')})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Wait for cache write
    await asyncio.sleep(2)
    
    # Final cache analysis
    print("\n📊 Final Cache Analysis:")
    cache_structure = analyze_cache_structure()
    
    if not cache_structure:
        print("   ❌ No cache files found!")
    else:
        print(f"   Found {len(cache_structure)} unique session(s):")
        for session_id, entries in cache_structure.items():
            print(f"\n   Session: {session_id}")
            for entry in entries:
                print(f"      - File: {entry['file']}")
                print(f"        Agent: {entry['agent']}")
                print(f"        Messages: {entry['messages']}")
    
    # Check if workflow session ID is present
    print("\n🔍 Workflow Session ID Analysis:")
    if workflow_session_id in cache_structure:
        print(f"   ✅ Found entries for workflow session: {workflow_session_id}")
        agents_in_workflow = [e['agent'] for e in cache_structure[workflow_session_id]]
        print(f"   Agents: {', '.join(agents_in_workflow)}")
    else:
        print(f"   ❌ No entries found for workflow session: {workflow_session_id}")
        print("   This suggests that simple workflows are NOT passing session_id to agent executions!")
    
    # Look for any files that might be related to our workflow
    print("\n🔍 Looking for workflow-related files:")
    if cache_dir.exists():
        all_files = list(cache_dir.glob("*.json"))
        print(f"   Total cache files: {len(all_files)}")
        
        # Check file creation times
        workflow_time = datetime.now()
        for file in all_files:
            stat = file.stat()
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            time_diff = (workflow_time - mod_time).total_seconds()
            
            if time_diff < 10:  # Files created in last 10 seconds
                print(f"   📄 Recently created: {file.name} ({time_diff:.1f}s ago)")
                try:
                    with open(file, "r") as f:
                        data = json.load(f)
                        print(f"      Session: {data.get('session_id', 'N/A')}")
                        print(f"      Agent: {data.get('agent_name', 'N/A')}")
                except:
                    pass
    
    print("\n=== Analysis Complete ===")
    print("\n🔍 Key Findings:")
    print("   1. Individual agents with session_id DO create cache entries")
    print("   2. Simple workflows may NOT be passing session_id to agent executions")
    print("   3. Check SimpleWorkflowExecutor.execute() to see if it passes session_id")
    print("\n💡 Next Step: Review the simple_workflow.py code to see if session_id is being passed to facade.run_agent()")


if __name__ == "__main__":
    asyncio.run(main())
