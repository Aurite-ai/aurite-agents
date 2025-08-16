"""Test script to verify that blank messages are fixed."""

import asyncio

import httpx

API_KEY = "87a06b293bcbb24573867851dea4820cd819ec1dfb1d4b984393ff783675a515"
BASE_URL = "http://localhost:8000"


async def test_message_content_fix():
    """Test that messages no longer have blank content."""
    async with httpx.AsyncClient() as client:
        # Get the workflow session
        session_id = "826c63d4"  # Using partial ID

        print(f"Testing session: {session_id}")
        print("=" * 60)

        response = await client.get(
            f"{BASE_URL}/execution/history/{session_id}?raw_format=false", headers={"X-API-Key": API_KEY}
        )

        if response.status_code == 200:
            data = response.json()

            print(f"✓ Found session: {data['session_id']}")
            print(f"Total messages: {len(data['messages'])}")
            print("\nChecking for blank messages:")

            blank_messages = []
            for i, msg in enumerate(data["messages"]):
                if msg["content"] == "" or msg["content"] is None:
                    blank_messages.append((i, msg))
                    print(f"  ✗ Message {i} ({msg['role']}): BLANK")
                elif msg["content"] == "[No text content]":
                    print(f"  ⚠ Message {i} ({msg['role']}): No text content placeholder")
                else:
                    # Show first 80 chars of content
                    content_preview = msg["content"].replace("\n", " ")[:80]
                    print(f"  ✓ Message {i} ({msg['role']}): {content_preview}...")

            if blank_messages:
                print(f"\n✗ FAIL: Found {len(blank_messages)} blank messages")
            else:
                print("\n✓ SUCCESS: No blank messages found!")

            # Also test raw format to compare
            print("\n\nTesting raw format:")
            response2 = await client.get(
                f"{BASE_URL}/execution/history/{session_id}?raw_format=true", headers={"X-API-Key": API_KEY}
            )

            if response2.status_code == 200:
                data2 = response2.json()
                print(f"Raw format message count: {len(data2['messages'])}")

        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)


if __name__ == "__main__":
    asyncio.run(test_message_content_fix())
