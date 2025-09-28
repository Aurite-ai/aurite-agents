#!/usr/bin/env python
"""
Test script to verify smart tool name resolution in MCP Host.
This tests that:
1. Unprefixed tool names are resolved correctly when unambiguous
2. Ambiguous tool names throw appropriate errors
3. Direct prefixed names still work
"""

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import mcp.types as types

from aurite.execution.mcp_host.mcp_host import MCPHost
from aurite.lib.models.config.components import AgentConfig

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_tool_name_resolution():
    """Test various tool name resolution scenarios."""
    print("\n" + "=" * 70)
    print("Testing Tool Name Resolution in MCP Host")
    print("=" * 70 + "\n")

    # Create MCP Host
    host = MCPHost()

    # Create mock sessions and tools
    mock_session1 = MagicMock()
    mock_session2 = MagicMock()

    # Simulate tool registration from two different servers
    # Server 1: gmail_server with send_draft and create_draft tools
    tool1 = types.Tool(
        name="gmail_server-send_draft",
        title="send_draft",  # The actual tool name without prefix
        description="Send a draft email",
        meta={"timeout": 30},
    )
    tool2 = types.Tool(
        name="gmail_server-create_draft", title="create_draft", description="Create a draft email", meta={"timeout": 30}
    )

    # Server 2: another_server with a different send_draft tool (ambiguous case)
    tool3 = types.Tool(
        name="another_server-send_draft",
        title="send_draft",
        description="Another server's send_draft",
        meta={"timeout": 30},
    )

    # Server 3: unique_server with unique_tool
    tool4 = types.Tool(
        name="unique_server-unique_tool", title="unique_tool", description="A unique tool", meta={"timeout": 30}
    )

    # Register tools in host (simulating registration)
    host._tools = {
        "gmail_server-send_draft": tool1,
        "gmail_server-create_draft": tool2,
        "unique_server-unique_tool": tool4,
    }
    host._tool_to_session = {
        "gmail_server-send_draft": mock_session1,
        "gmail_server-create_draft": mock_session1,
        "unique_server-unique_tool": mock_session2,
    }

    # Mock the session call_tool method
    async def mock_call_tool(name, args):
        return {"result": f"Called {name} with args {args}"}

    mock_session1.call_tool = mock_call_tool
    mock_session2.call_tool = mock_call_tool

    # Test cases
    test_results = []

    # Test 1: Direct prefixed name should work
    print("Test 1: Direct prefixed name...")
    try:
        await host.call_tool("gmail_server-send_draft", {"draft_id": "123"})
        print("✅ PASSED: Direct prefixed name works")
        test_results.append(True)
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results.append(False)

    # Test 2: Unprefixed name with single match should resolve
    print("\nTest 2: Unprefixed name with single match...")
    try:
        await host.call_tool("unique_tool", {"param": "value"})
        print("✅ PASSED: Unprefixed name resolved to unique_server-unique_tool")
        test_results.append(True)
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results.append(False)

    # Test 3: Unprefixed name with single match (create_draft)
    print("\nTest 3: Another unprefixed name with single match...")
    try:
        await host.call_tool("create_draft", {"to": "test@example.com"})
        print("✅ PASSED: Unprefixed create_draft resolved to gmail_server-create_draft")
        test_results.append(True)
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results.append(False)

    # Test 4: Ambiguous unprefixed name should fail with helpful error
    print("\nTest 4: Ambiguous unprefixed name (multiple servers have send_draft)...")
    # Add the ambiguous tool
    host._tools["another_server-send_draft"] = tool3
    host._tool_to_session["another_server-send_draft"] = mock_session2

    try:
        await host.call_tool("send_draft", {"draft_id": "456"})
        print("❌ FAILED: Should have thrown an ambiguity error")
        test_results.append(False)
    except KeyError as e:
        if "ambiguous" in str(e).lower():
            print(f"✅ PASSED: Correctly threw ambiguity error: {e}")
            test_results.append(True)
        else:
            print(f"❌ FAILED: Wrong error type: {e}")
            test_results.append(False)
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        test_results.append(False)

    # Test 5: Non-existent tool should fail
    print("\nTest 5: Non-existent tool...")
    try:
        await host.call_tool("non_existent_tool", {})
        print("❌ FAILED: Should have thrown a not found error")
        test_results.append(False)
    except KeyError as e:
        if "not found" in str(e).lower():
            print(f"✅ PASSED: Correctly threw not found error: {e}")
            test_results.append(True)
        else:
            print(f"❌ FAILED: Wrong error message: {e}")
            test_results.append(False)
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        test_results.append(False)

    # Test 6: Security check with agent config
    print("\nTest 6: Security check with agent config...")
    agent_config = AgentConfig(
        name="test_agent",
        mcp_servers=["gmail_server"],  # Only has access to gmail_server
    )
    try:
        # This should work (agent has access to gmail_server)
        await host.call_tool("create_draft", {"to": "test@example.com"}, agent_config)
        print("✅ PASSED: Agent can access allowed server's tool")
        test_results.append(True)
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results.append(False)

    # Test 7: Security check should block unauthorized access
    print("\nTest 7: Security check blocks unauthorized access...")
    try:
        # This should fail (agent doesn't have access to unique_server)
        await host.call_tool("unique_tool", {"param": "value"}, agent_config)
        print("❌ FAILED: Should have thrown a permission error")
        test_results.append(False)
    except PermissionError as e:
        print(f"✅ PASSED: Correctly blocked unauthorized access: {e}")
        test_results.append(True)
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        test_results.append(False)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY:")
    print(f"Tests passed: {sum(test_results)}/{len(test_results)}")
    if all(test_results):
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70 + "\n")

    return all(test_results)


if __name__ == "__main__":
    success = asyncio.run(test_tool_name_resolution())
    sys.exit(0 if success else 1)
