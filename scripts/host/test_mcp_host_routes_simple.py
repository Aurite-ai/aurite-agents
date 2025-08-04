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

        # 2. List servers (should be empty initially)
        print("\n2. Testing GET /tools/servers (before registration)")
        response = await client.get(f"{BASE_URL}/tools/servers", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            servers = response.json()
            print(f"   Servers found: {len(servers)}")

        # 3. List tools (should be empty initially)
        print("\n3. Testing GET /tools/ (before registration)")
        response = await client.get(f"{BASE_URL}/tools/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            tools = response.json()
            print(f"   Tools found: {len(tools)}")

        # 4. Register weather server by config
        print("\n4. Testing POST /tools/register/config (weather server)")
        config = {
            "name": "weather_server",
            "transport_type": "stdio",
            "server_path": "src/aurite/lib/init_templates/mcp_servers/weather_server.py",
            "timeout": 15.0,
            "capabilities": ["tools", "prompts", "resources"],
        }
        response = await client.post(f"{BASE_URL}/tools/register/config", headers=headers, json=config)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text}")

        # 5. List servers after registration
        print("\n5. Testing GET /tools/servers (after registration)")
        response = await client.get(f"{BASE_URL}/tools/servers", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            servers = response.json()
            print(f"   Servers found: {len(servers)}")
            for server in servers:
                print(
                    f"   - {server.get('name')}: {server.get('transport_type')} transport, {server.get('tools_count')} tools"
                )

        # 6. Get specific server status
        print("\n6. Testing GET /tools/servers/weather_server")
        response = await client.get(f"{BASE_URL}/tools/servers/weather_server", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            server_status = response.json()
            print(f"   Server: {server_status.get('name')}")
            print(f"   Registered: {server_status.get('registered')}")
            print(f"   Status: {server_status.get('status')}")
            print(f"   Tools: {server_status.get('tools', [])[:3]}")  # Show first 3 tools

        # 7. Test non-existent server
        print("\n7. Testing GET /tools/servers/non_existent_server")
        response = await client.get(f"{BASE_URL}/tools/servers/non_existent_server", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            server_status = response.json()
            print(f"   Registered: {server_status.get('registered')}")
            print(f"   Status: {server_status.get('status')}")

        # 8. Register planning server by name (if config exists)
        print("\n8. Testing POST /tools/register/planning-server (by name)")
        response = await client.post(f"{BASE_URL}/tools/register/planning-server", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text}")

        # 9. List tools again (should have tools now)
        print("\n9. Testing GET /tools/ (after registration)")
        response = await client.get(f"{BASE_URL}/tools/", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            tools = response.json()
            print(f"   Tools found: {len(tools)}")
            for tool in tools[:3]:  # Show first 3 tools
                print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")

        # 10. Get tool details
        if tools:
            tool_name = tools[0].get("name", "weather_lookup")
            print(f"\n10. Testing GET /tools/{tool_name} (tool details)")
            response = await client.get(f"{BASE_URL}/tools/{tool_name}", headers=headers)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                tool_details = response.json()
                print(f"   Tool: {tool_details.get('name')}")
                print(f"   Server: {tool_details.get('server_name')}")
                print(f"   Description: {tool_details.get('description')}")
                print(f"   Input Schema: {json.dumps(tool_details.get('inputSchema', {}), indent=2)[:100]}...")

        # 11. Get server tools
        print("\n11. Testing GET /tools/servers/weather_server/tools")
        response = await client.get(f"{BASE_URL}/tools/servers/weather_server/tools", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            server_tools = response.json()
            print(f"   Tools from weather_server: {len(server_tools)}")
            for tool in server_tools:
                print(f"   - {tool.get('name')}: {tool.get('description', 'No description')}")

        # 12. Execute a tool
        if tools:
            tool_name = tools[0].get("name", "get_weather")
            print(f"\n12. Testing POST /tools/{tool_name}/call")
            tool_args = {"args": {"location": "San Francisco"}}
            response = await client.post(f"{BASE_URL}/tools/{tool_name}/call", headers=headers, json=tool_args)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Result: {json.dumps(result, indent=2)}")
            else:
                print(f"   Error: {response.text}")

        # 13. Test server configuration
        print("\n13. Testing POST /tools/servers/weather_server/test")
        response = await client.post(f"{BASE_URL}/tools/servers/weather_server/test", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            test_result = response.json()
            print(f"   Test Status: {test_result.get('status')}")
            print(f"   Connection Time: {test_result.get('connection_time', 0):.3f}s")
            print(f"   Tools Discovered: {test_result.get('tools_discovered', [])}")
            if test_result.get("test_tool_result"):
                print(f"   Tool Test: {test_result['test_tool_result']}")
            if test_result.get("error"):
                print(f"   Error: {test_result['error']}")

        # 14. Unregister a server
        print("\n14. Testing DELETE /tools/servers/weather_server")
        response = await client.delete(f"{BASE_URL}/tools/servers/weather_server", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text}")

        # 15. Final status check
        print("\n15. Final GET /tools/status")
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
