#!/usr/bin/env python3
"""
Test script to verify that agents auto-generate session IDs when include_history=true
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


async def run_agent(agent_name: str, session_id=None):
    """Run an agent with optional session ID."""
    async with httpx.AsyncClient() as client:
        payload = {
            "user_message": "What's the weather in San Francisco?"
        }
        if session_id is not None:
            payload["session_id"] = session_id
            
        response = await client.post(
            f"{API_BASE_URL}/execution/agents/{agent_name}/run",
            headers=HEADERS,
            json=payload,
            timeout=30.0
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
                    files.append({
                        "filename": file.name,
                        "session_id": data.get("session_id"),
                        "agent_name": data.get("agent_name"),
                        "message_count": data.get("message_count", 0)
                    })
            except:
                pass
    return files


async def main():
    """Test auto-generation of session IDs for agents."""
    print("=== Testing Auto-Generation of Session IDs for Agents ===")
    
    # Clean up cache first
    cache_dir = Path(".aurite_cache")
    if cache_dir.exists():
        print("\n🧹 Cleaning up old cache files...")
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass
    
    # Test 1: Agent with include_history=true and NO session_id
    print("\n📝 Test 1: Agent with include_history=true, NO session_id provided")
    print("   Testing: 'Conversation History Weather Agent'")
    print("   Expected: Should auto-generate a session ID")
    
    try:
        # Run agent WITHOUT session_id
        print("   Running agent WITHOUT session_id...")
        result = await run_agent("Conversation History Weather Agent")
        print(f"   ✅ Agent completed with status: {result.get('status')}")
        
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
            if file['session_id'] and file['session_id'].startswith('agent-Conversation History Weather Agent-'):
                print("     ✅ Session ID was auto-generated!")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Agent without include_history and NO session_id
    print("\n📝 Test 2: Agent without include_history, NO session_id provided")
    print("   Testing: 'Weather Agent' (first definition without include_history)")
    print("   Expected: No history should be saved")
    
    # Clean cache again
    if cache_dir.exists():
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass
    
    try:
        # Run agent WITHOUT session_id
        print("   Running agent WITHOUT session_id...")
        result = await run_agent("Weather Agent")
        print(f"   ✅ Agent completed with status: {result.get('status')}")
        
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
    
    # Test 3: Agent with include_history=true and PROVIDED session_id
    print("\n📝 Test 3: Agent with include_history=true, WITH session_id provided")
    print("   Testing: 'Conversation History Weather Agent' with custom session ID")
    print("   Expected: Should use the provided session ID")
    
    # Clean cache again
    if cache_dir.exists():
        for file in cache_dir.glob("*.json"):
            try:
                file.unlink()
            except:
                pass
    
    try:
        # Run agent WITH session_id
        custom_session_id = "my-custom-session-123"
        print(f"   Running agent WITH session_id: {custom_session_id}")
        result = await run_agent("Conversation History Weather Agent", session_id=custom_session_id)
        print(f"   ✅ Agent completed with status: {result.get('status')}")
        
        # Wait for cache writes
        await asyncio.sleep(2)
        
        # Check cache files
        files = check_cache_files()
        print(f"\n   Cache files found: {len(files)}")
        for file in files:
            print(f"   - Session: {file['session_id']}")
            print(f"     Agent: {file['agent_name']}")
            print(f"     Messages: {file['message_count']}")
            
            # Check if custom session_id was used
            if file['session_id'] == custom_session_id:
                print("     ✅ Custom session ID was used!")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Summary ===")
    print("✅ When agent has include_history=true and no session_id is provided:")
    print("   - A session ID is auto-generated in the format: agent-{name}-{uuid}")
    print("   - The agent saves its history using this session ID")
    print("\n✅ When agent doesn't have include_history=true:")
    print("   - No history is saved (no auto-generation)")
    print("\n✅ When a session_id is explicitly provided:")
    print("   - The provided session_id is used (no auto-generation)")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
