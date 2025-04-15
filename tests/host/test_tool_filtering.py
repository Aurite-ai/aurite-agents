import pytest
from unittest.mock import MagicMock
from src.host.resources.tools import ToolManager, RootManager, MessageRouter, types

@pytest.fixture
def tool_manager():
    root_manager = MagicMock(spec=RootManager)
    message_router = MagicMock(spec=MessageRouter)
    tm = ToolManager(root_manager, message_router)

    # Register sample tools
    tool1 = MagicMock(spec=types.Tool)
    tool1.description = "Tool 1 description"
    tool1.parameters = {"param1": "string"}
    tool1.name = "tool1"

    tool2 = MagicMock(spec=types.Tool)
    tool2.description = "Tool 2 description"
    tool2.parameters = {"param2": "int"}
    tool2.name = "tool2"

    tool3 = MagicMock(spec=types.Tool)
    tool3.description = "Tool 3 description"
    tool3.parameters = {"param3": "bool"}
    tool3.name = "tool3"

    tm._tools = {
        "tool1": tool1,
        "tool2": tool2,
        "tool3": tool3
    }

    tm._tool_metadata = {
        "tool1": {"client_id": "client1", "description": "Tool 1 description", "parameters": {"param1": "string"}},
        "tool2": {"client_id": "client2", "description": "Tool 2 description", "parameters": {"param2": "int"}},
        "tool3": {"client_id": "client3", "description": "Tool 3 description", "parameters": {"param3": "bool"}}
    }

    return tm

def test_list_tools_all(tool_manager):
    tools = tool_manager.list_tools()
    assert len(tools) == 3
    assert all(tool["name"] in ["tool1", "tool2", "tool3"] for tool in tools)

def test_list_tools_filtered(tool_manager):
    tools = tool_manager.list_tools(allowed_clients=["client1", "client2"])
    assert len(tools) == 2
    assert all(tool["name"] in ["tool1", "tool2"] for tool in tools)

def test_list_tools_single_client(tool_manager):
    tools = tool_manager.list_tools(allowed_clients=["client1"])
    assert len(tools) == 1
    assert tools[0]["name"] == "tool1"

def test_list_tools_no_match(tool_manager):
    tools = tool_manager.list_tools(allowed_clients=["non_existent_client"])
    assert len(tools) == 0

def test_list_tools_empty_allowed_clients(tool_manager):
    tools = tool_manager.list_tools(allowed_clients=[])
    assert len(tools) == 0
    
def test_format_tools_for_llm_all(tool_manager):
    tools = tool_manager.format_tools_for_llm()
    assert len(tools) == 3
    assert all(tool["name"] in ["tool1", "tool2", "tool3"] for tool in tools)
    
def test_format_tools_for_llm_filtered(tool_manager):
    tools = tool_manager.format_tools_for_llm(allowed_clients=["client2", "client3"])
    assert len(tools) == 2
    assert all(tool["name"] in ["tool2", "tool3"] for tool in tools)
    
def test_format_tools_for_llm_filtered_name(tool_manager):
    tools = tool_manager.format_tools_for_llm(allowed_clients=["client2", "client3"], tool_names=["tool2", "tool1"])
    assert len(tools) == 1
    assert all(tool["name"] in ["tool2"] for tool in tools)