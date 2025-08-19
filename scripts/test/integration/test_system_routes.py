#!/usr/bin/env python3
"""
Test script for System Management API routes.
Tests all /system/* endpoints with proper error handling.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY", "test-api-key")
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": API_KEY}


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")


def print_result(name: str, result: Dict[str, Any], error: str | None = None):
    """Print test result in a consistent format."""
    if error:
        print(f"❌ {name}: ERROR - {error}")
    else:
        print(f"✅ {name}: SUCCESS")
        if isinstance(result, dict) or isinstance(result, list):
            print(f"   Response: {json.dumps(result, indent=2)[:200]}...")
        else:
            print(f"   Response: {result}")


async def test_system_info(client: httpx.AsyncClient):
    """Test GET /system/info endpoint."""
    try:
        response = await client.get(f"{BASE_URL}/system/info", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        # Verify expected fields
        expected_fields = ["platform", "platform_version", "python_version", "hostname", "cpu_count", "architecture"]
        missing = [f for f in expected_fields if f not in data]

        if missing:
            print_result("System Info", data, f"Missing fields: {missing}")
        else:
            print_result("System Info", data)
            print(f"   Platform: {data['platform']} {data['platform_version']}")
            print(f"   Python: {data['python_version']} ({data['python_implementation']})")
            print(f"   CPUs: {data['cpu_count']}, Architecture: {data['architecture']}")

    except Exception as e:
        print_result("System Info", {}, str(e))


async def test_framework_version(client: httpx.AsyncClient):
    """Test GET /system/version endpoint."""
    try:
        response = await client.get(f"{BASE_URL}/system/version", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        print_result("Framework Version", data)
        print(f"   Version: {data['version']}")
        print(f"   Name: {data['name']}")
        print(f"   Authors: {', '.join(data['authors'])}")

    except Exception as e:
        print_result("Framework Version", {}, str(e))


async def test_capabilities(client: httpx.AsyncClient):
    """Test GET /system/capabilities endpoint."""
    try:
        response = await client.get(f"{BASE_URL}/system/capabilities", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        print_result("System Capabilities", data)
        print(f"   MCP Support: {data['mcp_support']}")
        print(f"   Available Transports: {', '.join(data['available_transports'])}")
        print(f"   LLM Providers: {len(data['supported_llm_providers'])} supported")

        # Show optional features
        optional = data.get("optional_features", {})
        enabled = [k for k, v in optional.items() if v]
        disabled = [k for k, v in optional.items() if not v]

        if enabled:
            print(f"   Enabled Features: {', '.join(enabled)}")
        if disabled:
            print(f"   Disabled Features: {', '.join(disabled)}")

    except Exception as e:
        print_result("System Capabilities", {}, str(e))


async def test_environment_variables(client: httpx.AsyncClient):
    """Test GET /system/environment endpoint."""
    try:
        response = await client.get(f"{BASE_URL}/system/environment", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        # Show summary
        total = len(data)
        sensitive = len([v for v in data if v["is_sensitive"]])

        print_result("Environment Variables", {"total": total, "sensitive": sensitive})
        print(f"   Total Variables: {total}")
        print(f"   Sensitive (masked): {sensitive}")

        # Show a few examples
        examples = data[:3] if len(data) > 3 else data
        for var in examples:
            value = var["value"][:50] + "..." if len(var["value"]) > 50 else var["value"]
            print(f"   - {var['name']}: {value}")

    except Exception as e:
        print_result("Environment Variables", {}, str(e))


async def test_update_environment(client: httpx.AsyncClient):
    """Test PUT /system/environment endpoint."""
    try:
        # Try to update a test variable
        test_vars = {
            "AURITE_TEST_VAR": f"test_{datetime.now().isoformat()}",
            "API_KEY": "should_fail",  # This should be rejected
        }

        response = await client.put(f"{BASE_URL}/system/environment", headers=HEADERS, json={"variables": test_vars})
        response.raise_for_status()
        data = response.json()

        print_result("Update Environment", data)
        print(f"   Updated: {data['updated']}")
        print(f"   Errors: {data['errors']}")
        print(f"   Status: {data['status']}")

    except Exception as e:
        print_result("Update Environment", {}, str(e))


async def test_dependencies(client: httpx.AsyncClient):
    """Test GET /system/dependencies endpoint."""
    try:
        response = await client.get(f"{BASE_URL}/system/dependencies", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        # Show summary
        total = len(data)

        print_result("Dependencies List", {"total": total})
        print(f"   Total Packages: {total}")

        # Show key dependencies
        key_deps = ["fastapi", "pydantic", "mcp", "litellm", "sqlalchemy"]
        for dep_name in key_deps:
            dep = next((d for d in data if d["name"] == dep_name), None)
            if dep:
                print(f"   - {dep['name']}: {dep['version']}")

    except Exception as e:
        print_result("Dependencies List", {}, str(e))


async def test_dependency_health(client: httpx.AsyncClient):
    """Test POST /system/dependencies/check endpoint."""
    try:
        response = await client.post(f"{BASE_URL}/system/dependencies/check", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        # Analyze results
        total = len(data)
        installed = len([d for d in data if d["installed"]])
        importable = len([d for d in data if d["importable"]])

        print_result("Dependency Health", {"total": total, "installed": installed, "importable": importable})

        # Show any missing dependencies
        missing = [d for d in data if not d["installed"]]
        if missing:
            print("   Missing Dependencies:")
            for dep in missing:
                print(f"   - {dep['name']}: {dep['error']}")

        # Show any import errors
        import_errors = [d for d in data if d["installed"] and not d["importable"]]
        if import_errors:
            print("   Import Errors:")
            for dep in import_errors:
                print(f"   - {dep['name']}: {dep['error']}")

    except Exception as e:
        print_result("Dependency Health", {}, str(e))


async def test_system_metrics(client: httpx.AsyncClient):
    """Test GET /system/monitoring/metrics endpoint."""
    try:
        response = await client.get(f"{BASE_URL}/system/monitoring/metrics", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        print_result("System Metrics", data)
        print(f"   Timestamp: {data['timestamp']}")
        print(f"   CPU: {data['cpu_percent']}%")

        mem = data.get("memory_usage", {})
        if "percent" in mem:
            print(f"   Memory: {mem['percent']}%")

        disk = data.get("disk_usage", {})
        if "percent" in disk:
            print(f"   Disk: {disk['percent']}%")

        proc = data.get("process_info", {})
        if "pid" in proc:
            print(f"   Process PID: {proc['pid']}")

    except Exception as e:
        print_result("System Metrics", {}, str(e))


async def test_active_processes(client: httpx.AsyncClient):
    """Test GET /system/monitoring/active endpoint."""
    try:
        response = await client.get(f"{BASE_URL}/system/monitoring/active", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        print_result("Active Processes", {"count": len(data)})

        for proc in data:
            print(f"   - {proc['name']} (PID: {proc['pid']}, Status: {proc['status']})")
            print(f"     CPU: {proc['cpu_percent']}%, Memory: {proc['memory_percent']}%")

    except Exception as e:
        print_result("Active Processes", {}, str(e))


async def test_health_check(client: httpx.AsyncClient):
    """Test GET /system/health endpoint."""
    try:
        response = await client.get(f"{BASE_URL}/system/health", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        print_result("Health Check", data)
        print(f"   Overall Status: {data['status']}")
        print(f"   Timestamp: {data['timestamp']}")

        # Show component status
        print("   Components:")
        for name, info in data["components"].items():
            status = info.get("status", "unknown")
            emoji = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
            print(f"   {emoji} {name}: {status}")

            # Show additional info
            if "error" in info:
                print(f"      Error: {info['error']}")
            elif name == "api" and "uptime" in info:
                print(f"      Uptime: {info['uptime']:.1f}s")
            elif name == "mcp_host" and "registered_servers" in info:
                print(f"      Servers: {info['registered_servers']}, Tools: {info['available_tools']}")

        # Show issues if any
        if data.get("issues"):
            print("   Issues:")
            for issue in data["issues"]:
                print(f"   - {issue}")

    except Exception as e:
        print_result("Health Check", {}, str(e))


async def test_log_streaming(client: httpx.AsyncClient):
    """Test GET /system/monitoring/logs endpoint (SSE)."""
    print_section("Testing Log Streaming (SSE)")
    print("⏳ Testing log stream connection (5 seconds)...")

    try:
        # Test SSE connection briefly
        log_count = 0
        heartbeat_count = 0

        async with client.stream("GET", f"{BASE_URL}/system/monitoring/logs", headers=HEADERS) as response:
            response.raise_for_status()

            # Read for 5 seconds
            start_time = asyncio.get_event_loop().time()
            async for line in response.aiter_lines():
                if asyncio.get_event_loop().time() - start_time > 5:
                    break

                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data["type"] == "connected":
                            print(f"✅ Connected: {data['message']}")
                        elif data["type"] == "log":
                            log_count += 1
                        elif data["type"] == "heartbeat":
                            heartbeat_count += 1
                    except json.JSONDecodeError:
                        pass

        print("✅ Log Streaming: SUCCESS")
        print(f"   Received {log_count} logs and {heartbeat_count} heartbeats in 5 seconds")

    except Exception as e:
        print(f"❌ Log Streaming: ERROR - {str(e)}")


async def main():
    """Run all system route tests."""
    print("\nTesting System Management Routes")
    print(f"API URL: {BASE_URL}")
    print(f"API Key: {'*' * (len(API_KEY) - 4) + API_KEY[-4:]}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # System Information
        print_section("System Information")
        await test_system_info(client)
        await test_framework_version(client)
        await test_capabilities(client)

        # Environment Management
        print_section("Environment Management")
        await test_environment_variables(client)
        await test_update_environment(client)

        # Dependency Management
        print_section("Dependency Management")
        await test_dependencies(client)
        await test_dependency_health(client)

        # Monitoring
        print_section("System Monitoring")
        await test_system_metrics(client)
        await test_active_processes(client)

        # Health Check
        print_section("Health Check")
        await test_health_check(client)

        # Log Streaming (SSE)
        await test_log_streaming(client)

    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
