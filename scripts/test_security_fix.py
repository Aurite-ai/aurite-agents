#!/usr/bin/env python3
"""
Test script to verify the MCP Host security fix.

This script tests that agents with empty mcp_servers lists cannot access tools.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aurite.execution.mcp_host.mcp_host import MCPHost
from aurite.lib.models.config.components import AgentConfig, ClientConfig


async def test_security_fix():
    """Test that agents with empty mcp_servers cannot access tools."""
    print("🔒 Testing MCP Host Security Fix")
    print("=" * 50)

    # Create MCP Host
    host = MCPHost()

    # Register a test server (weather_server)
    weather_server_config = ClientConfig(
        name="weather_server",
        transport_type="stdio",
        server_path=Path(__file__).parent.parent
        / "src"
        / "aurite"
        / "lib"
        / "init_templates"
        / "mcp_servers"
        / "weather_server.py",
        capabilities=["tools"],  # This server provides tools
        timeout=30.0,
        registration_timeout=10.0,
    )

    try:
        await host.register_client(weather_server_config)
        print("✅ Successfully registered weather_server")

        # Test 1: Agent with empty mcp_servers list should get NO tools
        print("\n🧪 Test 1: Agent with empty mcp_servers")
        agent_with_no_servers = AgentConfig(
            name="test_agent_no_servers",
            type="agent",
            mcp_servers=[],  # Empty list - should have NO access
            system_prompt="Test agent",
        )

        tools = host.get_formatted_tools(agent_config=agent_with_no_servers)
        print(f"   Tools available: {len(tools)}")
        if len(tools) == 0:
            print("   ✅ PASS: Agent with empty mcp_servers gets no tools")
        else:
            print("   ❌ FAIL: Agent with empty mcp_servers got tools!")
            for tool in tools:
                print(f"      - {tool.get('name', 'unknown')}")

        # Test 2: Agent with weather_server access should get tools
        print("\n🧪 Test 2: Agent with weather_server access")
        agent_with_weather = AgentConfig(
            name="test_agent_with_weather",
            type="agent",
            mcp_servers=["weather_server"],  # Has access to weather_server
            system_prompt="Test agent",
        )

        tools = host.get_formatted_tools(agent_config=agent_with_weather)
        print(f"   Tools available: {len(tools)}")
        if len(tools) > 0:
            print("   ✅ PASS: Agent with weather_server access gets tools")
            for tool in tools:
                print(f"      - {tool.get('name', 'unknown')}")
        else:
            print("   ❌ FAIL: Agent with weather_server access got no tools!")

        # Test 3: Try to call tool with agent that has no access
        print("\n🧪 Test 3: Tool call security check")
        try:
            result = await host.call_tool(
                name="weather_server-weather_lookup",
                args={"location": "San Francisco"},
                agent_config=agent_with_no_servers,
            )
            print("   ❌ FAIL: Agent with no access was able to call tool!")
            print(f"      Result: {result}")
        except PermissionError as e:
            print("   ✅ PASS: Tool call correctly blocked with PermissionError")
            print(f"      Error: {e}")
        except Exception as e:
            print(f"   ⚠️  UNEXPECTED: Got different error: {type(e).__name__}: {e}")

        # Test 4: Agent with access should be able to call tool
        print("\n🧪 Test 4: Authorized tool call")
        try:
            result = await host.call_tool(
                name="weather_server-weather_lookup",
                args={"location": "San Francisco"},
                agent_config=agent_with_weather,
            )
            print("   ✅ PASS: Agent with access successfully called tool")
            print(f"      Result type: {type(result)}")
        except Exception as e:
            print(f"   ❌ FAIL: Authorized agent couldn't call tool: {type(e).__name__}: {e}")

    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False

    finally:
        # Cleanup
        await host.unregister_client("weather_server")
        print("\n🧹 Cleanup completed")

    print("\n" + "=" * 50)
    print("🔒 Security test completed!")
    return True


if __name__ == "__main__":
    asyncio.run(test_security_fix())
