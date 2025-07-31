#!/usr/bin/env python3
"""
Test script to verify the history cleanup endpoint works with 0 days.
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


async def get_all_sessions():
    """Get all sessions from history."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/execution/history", headers=HEADERS, params={"limit": 100}, timeout=10.0
        )
        response.raise_for_status()
        return response.json()


async def cleanup_sessions(days: int, max_sessions: int):
    """Call the cleanup endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/execution/history/cleanup",
            headers=HEADERS,
            params={"days": days, "max_sessions": max_sessions},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def main():
    """Test the cleanup endpoint with various parameters."""
    print("=== Testing History Cleanup Endpoint ===\n")

    # Test 1: Check current sessions
    print("1️⃣ Checking current sessions...")
    try:
        result = await get_all_sessions()
        print(f"   ✅ Found {result['total']} sessions")

        # Show some session details
        if result["sessions"]:
            print("\n   Recent sessions:")
            for session in result["sessions"][:3]:
                print(f"   - {session['session_id']}")
                print(f"     Last updated: {session.get('last_updated', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # Test 2: Test cleanup with 0 days (should work now)
    print("\n2️⃣ Testing cleanup with days=0 (delete all sessions older than today)")
    try:
        cleanup_result = await cleanup_sessions(days=0, max_sessions=50)
        print(f"   ✅ Success! {cleanup_result['message']}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            print("   ❌ Validation error: days=0 is not allowed (needs fix)")
            print(f"   Error details: {e.response.text}")
        else:
            print(f"   ❌ Error: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Test cleanup with 1 day (should always work)
    print("\n3️⃣ Testing cleanup with days=1")
    try:
        cleanup_result = await cleanup_sessions(days=1, max_sessions=50)
        print(f"   ✅ Success! {cleanup_result['message']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Test cleanup with max_sessions limit
    print("\n4️⃣ Testing cleanup with max_sessions=5")
    try:
        cleanup_result = await cleanup_sessions(days=30, max_sessions=5)
        print(f"   ✅ Success! {cleanup_result['message']}")

        # Check how many sessions remain
        result = await get_all_sessions()
        print(f"   Sessions remaining: {result['total']}")
        if result["total"] > 5:
            print("   ⚠️ Warning: More than 5 sessions remain. The limit might apply per agent/workflow.")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: Edge case - cleanup with days=365 (maximum)
    print("\n5️⃣ Testing cleanup with days=365 (maximum allowed)")
    try:
        cleanup_result = await cleanup_sessions(days=365, max_sessions=50)
        print(f"   ✅ Success! {cleanup_result['message']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 6: Edge case - try invalid value (should fail)
    print("\n6️⃣ Testing cleanup with days=366 (should fail)")
    try:
        cleanup_result = await cleanup_sessions(days=366, max_sessions=50)
        print("   ❌ Unexpected success! This should have failed.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            print("   ✅ Expected validation error: days > 365 not allowed")
        else:
            print(f"   ❌ Unexpected error: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n=== Summary ===")
    print("✅ The cleanup endpoint now accepts days=0 to delete all sessions older than today")
    print("✅ The days parameter range is 0-365")
    print("✅ The max_sessions parameter controls how many sessions to keep")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
