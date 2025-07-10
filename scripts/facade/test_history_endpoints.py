#!/usr/bin/env python3
"""
Test script for the new history endpoints.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_BASE_URL = "http://localhost:8000/execution"
API_KEY = os.getenv("API_KEY", "test-api-key")

headers = {"X-API-Key": API_KEY}


async def test_history_endpoints():
    """Test the new history endpoints."""
    async with httpx.AsyncClient() as client:
        print("Testing History Endpoints")
        print("=" * 50)

        # Test 1: List all sessions
        print("\n1. Testing GET /history (list all sessions)")
        try:
            response = await client.get(f"{API_BASE_URL}/history", headers=headers, params={"limit": 10, "offset": 0})
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Total sessions: {data['total']}")
                print(f"Sessions returned: {len(data['sessions'])}")
                if data["sessions"]:
                    print("\nFirst session:")
                    print(json.dumps(data["sessions"][0], indent=2))
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

        # Test 2: Get specific session history
        print("\n2. Testing GET /history/{session_id}")
        session_id = "test-session-debug"  # Use a known session ID
        try:
            # Test simplified format (default)
            response = await client.get(f"{API_BASE_URL}/history/{session_id}", headers=headers)
            print(f"Status (simplified): {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Agent: {data['agent_name']}")
                print(f"Messages: {len(data['messages'])}")
                if data["messages"]:
                    print("\nFirst message (simplified):")
                    print(json.dumps(data["messages"][0], indent=2))
            elif response.status_code == 404:
                print(f"Session not found: {session_id}")
            else:
                print(f"Error: {response.text}")

            # Test raw format
            response = await client.get(
                f"{API_BASE_URL}/history/{session_id}", headers=headers, params={"raw_format": True}
            )
            print(f"\nStatus (raw): {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if data["messages"]:
                    print("First message (raw):")
                    print(json.dumps(data["messages"][0], indent=2))
        except Exception as e:
            print(f"Error: {e}")

        # Test 3: Get agent-specific history
        print("\n3. Testing GET /agents/{agent_name}/history")
        agent_name = "Conversation History Weather Agent"
        try:
            response = await client.get(
                f"{API_BASE_URL}/agents/{agent_name}/history", headers=headers, params={"limit": 5}
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Total sessions for {agent_name}: {data['total']}")
                print(f"Sessions returned: {len(data['sessions'])}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

        # Test 4: Delete a session
        print("\n4. Testing DELETE /history/{session_id}")
        test_session_id = "test-delete-session"

        # First create a test session by running an agent
        print(f"Creating test session: {test_session_id}")
        try:
            response = await client.post(
                f"{API_BASE_URL}/agents/Conversation History Weather Agent/run",
                headers=headers,
                json={"user_message": "Test message for deletion", "session_id": test_session_id},
            )
            if response.status_code == 200:
                print("Test session created successfully")

                # Now delete it
                response = await client.delete(f"{API_BASE_URL}/history/{test_session_id}", headers=headers)
                print(f"Delete status: {response.status_code}")
                if response.status_code == 204:
                    print("Session deleted successfully")

                    # Verify it's gone
                    response = await client.get(f"{API_BASE_URL}/history/{test_session_id}", headers=headers)
                    if response.status_code == 404:
                        print("Confirmed: Session no longer exists")
                    else:
                        print(f"Unexpected status after deletion: {response.status_code}")
                else:
                    print(f"Delete error: {response.text}")
            else:
                print(f"Failed to create test session: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

        # Test 5: Test pagination
        print("\n5. Testing pagination")
        try:
            # Get first page
            response = await client.get(f"{API_BASE_URL}/history", headers=headers, params={"limit": 2, "offset": 0})
            if response.status_code == 200:
                data1 = response.json()
                print(f"Page 1: {len(data1['sessions'])} sessions")

                # Get second page
                response = await client.get(
                    f"{API_BASE_URL}/history", headers=headers, params={"limit": 2, "offset": 2}
                )
                if response.status_code == 200:
                    data2 = response.json()
                    print(f"Page 2: {len(data2['sessions'])} sessions")
                    print(f"Total available: {data1['total']}")
        except Exception as e:
            print(f"Error: {e}")

        # Test 6: Test cleanup endpoint
        print("\n6. Testing POST /history/cleanup")
        try:
            response = await client.post(
                f"{API_BASE_URL}/history/cleanup", headers=headers, params={"days": 7, "max_sessions": 10}
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Result: {data['message']}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")


async def main():
    """Main function."""
    print("Starting History Endpoints Test")
    print("Make sure the API server is running on http://localhost:8000")
    print()

    await test_history_endpoints()

    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
