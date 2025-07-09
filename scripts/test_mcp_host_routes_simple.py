#!/usr/bin/env python3
"""
Simple test script for currently implemented MCP Host routes.
This script only tests the endpoints that are actually implemented.
"""

import asyncio
import json
import os

import httpx

# Configuration
API_KEY = os.getenv("API_KEY", "test-api-key")
BASE_URL = "http://localhost:8000"


async def test_implemented_endpoints():
    """Test only the currently implemented endpoints."""
    headers = {"X-API-Key": API_KEY}

    async with httpx.AsyncClient() as client:
        print("\n" + "=" * 60)
        print("TESTING IMPLEMENTED MCP HOST ROUTES")
        print("=" * 60)

        # 1. Get host status
        print("\n1. Testing GET /tools/status")
        response = await client.get(f"{BASE_URL}/tools/status", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")

        # 2. List tools (should be empty initially)
        print("\n2. Testing GET /tools/ (before registration)")
        response = await client.get(f"{BASE_URL}/tools/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            tools = response.json()
            print(f"   Tools found: {len(tools)}")

        # 3. Register weather server by config
        print("\n3. Testing POST /tools/register/config (weather server)")
        config = {
            "name": "weather_server",
            "transport_type": "stdio",
            "server_path": "src/aurite/init_templates/mcp_servers/weather_server.py",
            "timeout": 15.0,
            "capabilities": ["tools", "prompts", "resources"],
        }
        response = await client.post(f"{BASE_URL}/tools/register/config", headers=headers, json=config)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text}")

        # 4. Register planning server by name (if config exists)
        print("\n4. Testing POST /tools/register/planning-server (by name)")
        response = await client.post(f"{BASE_URL}/tools/register/planning-server", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text}")

        # 5. List tools again (should have tools now)
        print("\n5. Testing GET /tools/ (after registration)")
        response = await client.get(f"{BASE_URL}/tools/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            tools = response.json()
            print(f"   Tools found: {len(tools)}")
            for tool in tools[:3]:  # Show first 3 tools
                print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")

        # 6. Execute a tool
        if response.status_code == 200 and tools:
            tool_name = tools[0].get("name", "get_weather")
            print(f"\n6. Testing POST /tools/{tool_name}/call")
            tool_args = {"args": {"location": "San Francisco"}}
            response = await client.post(f"{BASE_URL}/tools/{tool_name}/call", headers=headers, json=tool_args)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Result: {json.dumps(result, indent=2)}")
            else:
                print(f"   Error: {response.text}")

        # 7. Unregister a server
        print("\n7. Testing DELETE /tools/servers/weather_server")
        response = await client.delete(f"{BASE_URL}/tools/servers/weather_server", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text}")

        # 8. Final status check
        print("\n8. Final GET /tools/status")
        response = await client.get(f"{BASE_URL}/tools/status", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")

        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)


async def main():
    """Main test runner."""
    print("Simple MCP Host Routes Test")
    print("Make sure the API server is running on http://localhost:8000")
    print(f"Using API_KEY: {API_KEY[:10]}..." if API_KEY else "No API key set!")

    await test_implemented_endpoints()


if __name__ == "__main__":
    asyncio.run(main())
