#!/usr/bin/env python3
"""
Test script for MCP Host routes - demonstrates current vs desired state.

This script tests both existing and missing endpoints to help with implementation.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

# Configuration
API_KEY = os.getenv("API_KEY", "test-api-key")
BASE_URL = "http://localhost:8000"


class MCPHostRouteTester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
        self.results = []

    async def test_endpoint(
        self,
        method: str,
        path: str,
        description: str,
        body: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
    ):
        """Test a single endpoint and record the result."""
        url = f"{self.base_url}{path}"
        print(f"\n{'='*60}")
        print(f"Testing: {description}")
        print(f"Method: {method} {path}")

        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, headers=self.headers)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=body)
                elif method == "PUT":
                    response = await client.put(url, headers=self.headers, json=body)
                elif method == "DELETE":
                    response = await client.delete(url, headers=self.headers)

                status = "✓ PASS" if response.status_code == expected_status else "✗ FAIL"
                self.results.append(
                    {
                        "endpoint": f"{method} {path}",
                        "description": description,
                        "status": status,
                        "response_code": response.status_code,
                        "implemented": response.status_code != 404,
                    }
                )

                print(f"Status: {status} (HTTP {response.status_code})")
                if response.status_code == 200:
                    print(f"Response: {json.dumps(response.json(), indent=2)}")
                else:
                    print(f"Response: {response.text}")

        except Exception as e:
            print(f"Error: {str(e)}")
            self.results.append(
                {
                    "endpoint": f"{method} {path}",
                    "description": description,
                    "status": "✗ ERROR",
                    "response_code": None,
                    "implemented": False,
                }
            )

    async def run_all_tests(self):
        """Run tests for all endpoints defined in the API reference."""

        print("\n" + "=" * 60)
        print("MCP HOST ROUTES TEST SUITE")
        print("=" * 60)
        print(f"Testing against: {self.base_url}")
        print(f"Started at: {datetime.now().isoformat()}")

        # Test existing endpoints (actual implementation)
        print("\n\n### TESTING IMPLEMENTED ENDPOINTS ###")

        await self.test_endpoint("GET", "/tools/status", "Get host status")

        await self.test_endpoint(
            "GET", "/tools/", "List all available tools (before registration)", expected_status=200
        )

        # Register servers for testing
        print("\n### REGISTERING TEST SERVERS ###")

        # Register weather server using config with proper ClientConfig structure
        await self.test_endpoint(
            "POST",
            "/tools/register/config",
            "Register weather server by config",
            body={
                "name": "weather_server",
                "transport_type": "stdio",
                "server_path": "src/aurite/init_templates/mcp_servers/weather_server.py",
                "timeout": 15.0,
                "capabilities": ["tools", "prompts", "resources"],
            },
        )

        # Register planning server using config
        await self.test_endpoint(
            "POST",
            "/tools/register/config",
            "Register planning server by config",
            body={
                "name": "planning_server",
                "transport_type": "stdio",
                "server_path": "src/aurite/init_templates/mcp_servers/planning_server.py",
                "timeout": 15.0,
                "capabilities": ["tools", "prompts", "resources"],
            },
        )

        # Register by name (using existing config)
        await self.test_endpoint("POST", "/tools/register/weather-server", "Register weather server by name")

        # List tools after registration
        await self.test_endpoint("GET", "/tools/", "List all available tools (after registration)")

        # Test tool execution
        print("\n### TESTING TOOL EXECUTION ###")

        # First, let's see what tools are available
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/tools/", headers=self.headers)
            if response.status_code == 200:
                tools = response.json()
                if tools:
                    # Try to execute the first available tool
                    tool_name = tools[0].get("name", "get_weather")
                    await self.test_endpoint(
                        "POST",
                        f"/tools/{tool_name}/call",
                        f"Execute tool: {tool_name}",
                        body={"args": {"location": "San Francisco"}},
                    )

        # Test unregistering a server
        await self.test_endpoint("DELETE", "/tools/servers/weather_server", "Unregister weather server")

        # Test API reference endpoints that are NOT implemented yet
        print("\n\n### TESTING DOCUMENTED BUT NOT IMPLEMENTED ENDPOINTS ###")

        # MCP Server Management
        print("\n## MCP Server Management (Not Implemented) ##")

        await self.test_endpoint("GET", "/tools/servers", "List all MCP server configs", expected_status=404)

        await self.test_endpoint(
            "POST",
            "/tools/servers",
            "Create new MCP server config",
            body={
                "name": "new-server",
                "transport_type": "stdio",
                "server_path": "path/to/server.py",
                "description": "Test server",
                "timeout": 30.0,
            },
            expected_status=404,
        )

        await self.test_endpoint(
            "GET", "/tools/servers/weather-server", "Get server config details", expected_status=404
        )

        await self.test_endpoint(
            "PUT",
            "/tools/servers/weather-server",
            "Update server config",
            body={"description": "Updated description", "timeout": 60.0},
            expected_status=404,
        )

        await self.test_endpoint(
            "POST",
            "/tools/servers/weather-server/register",
            "Register server with host (documented endpoint)",
            expected_status=404,
        )

        await self.test_endpoint(
            "DELETE",
            "/tools/servers/weather-server/unregister",
            "Unregister server from host (documented endpoint)",
            expected_status=404,
        )

        await self.test_endpoint(
            "POST", "/tools/servers/weather-server/test", "Test server connection", expected_status=404
        )

        await self.test_endpoint(
            "GET", "/tools/servers/weather-server/status", "Get server runtime status", expected_status=404
        )

        # Tool Discovery & Execution
        print("\n## Tool Discovery & Execution (Partially Implemented) ##")

        await self.test_endpoint("GET", "/tools/get_weather", "Get tool details", expected_status=404)

        await self.test_endpoint(
            "GET", "/tools/servers/weather-server/tools", "List tools from specific server", expected_status=404
        )

        # Host Management
        print("\n## Host Management (Not Implemented) ##")

        await self.test_endpoint(
            "GET", "/tools/host/status", "Get MCPHost status (documented path)", expected_status=404
        )

        await self.test_endpoint(
            "GET", "/tools/host/registered", "List currently registered servers", expected_status=404
        )

        await self.test_endpoint(
            "POST",
            "/tools/host/register/config",
            "Register server by config object (documented path)",
            body={
                "name": "custom-server",
                "transport_type": "http_stream",
                "http_endpoint": "https://api.example.com/mcp",
                "timeout": 30.0,
                "capabilities": ["tools", "prompts", "resources"],
            },
            expected_status=404,
        )

        await self.test_endpoint(
            "POST",
            "/tools/host/register/weather-server",
            "Register server by name (documented path)",
            expected_status=404,
        )

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print a summary of test results."""
        print("\n\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        implemented = [
            r for r in self.results if r["response_code"] not in [404, 405] and r["response_code"] is not None
        ]
        not_implemented = [r for r in self.results if r["response_code"] in [404, 405]]
        errors = [r for r in self.results if r["response_code"] is None]

        print(f"\nTotal endpoints tested: {len(self.results)}")
        print(f"Implemented: {len(implemented)}")
        print(f"Not implemented: {len(not_implemented)}")
        print(f"Errors: {len(errors)}")

        if implemented:
            print("\n### Implemented Endpoints ###")
            for result in implemented:
                print(f"  {result['status']} {result['endpoint']} - {result['description']}")

        if not_implemented:
            print("\n### Not Implemented Endpoints (Need Work) ###")
            for result in not_implemented:
                print(f"  {result['status']} {result['endpoint']} - {result['description']}")

        if errors:
            print("\n### Endpoints with Errors ###")
            for result in errors:
                print(f"  {result['status']} {result['endpoint']} - {result['description']}")

        print("\n" + "=" * 60)

        # Summary of what's actually implemented vs documented
        print("\n### IMPLEMENTATION STATUS ###")
        print("\nCurrently Implemented:")
        print("  - GET /tools/status - Get host status")
        print("  - GET /tools/ - List all available tools")
        print("  - POST /tools/register/config - Register server by config")
        print("  - POST /tools/register/{server_name} - Register server by name")
        print("  - DELETE /tools/servers/{server_name} - Unregister server")
        print("  - POST /tools/{tool_name}/call - Execute tool")

        print("\nDocumented but Not Implemented:")
        print("  - Full CRUD for server configs (/tools/servers/*)")
        print("  - Server status and testing endpoints")
        print("  - Tool details endpoint")
        print("  - Host management endpoints (/tools/host/*)")
        print("  - Server-specific tool listing")


async def main():
    """Main test runner."""
    tester = MCPHostRouteTester(BASE_URL, API_KEY)
    await tester.run_all_tests()


if __name__ == "__main__":
    print("MCP Host Routes Test Script")
    print("Make sure the API server is running on http://localhost:8000")
    print(f"Using API_KEY: {API_KEY[:10]}..." if API_KEY else "No API key set!")
    print("\nSet API_KEY environment variable if needed")
    input("\nPress Enter to start tests...")

    asyncio.run(main())
