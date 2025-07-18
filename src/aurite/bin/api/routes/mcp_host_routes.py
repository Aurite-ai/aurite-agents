from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel

from ....config.config_manager import ConfigManager
from ....config.config_models import ClientConfig
from ....errors import MCPServerTimeoutError
from ....host.host import MCPHost
from ...dependencies import get_api_key, get_config_manager, get_host

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


class ToolCallArgs(BaseModel):
    args: Dict[str, Any]


class ServerRuntimeInfo(BaseModel):
    """Runtime information about a registered MCP server."""

    name: str
    status: str = "active"
    transport_type: str
    tools_count: int
    registration_time: datetime


class ServerDetailedStatus(BaseModel):
    """Detailed runtime status for a specific MCP server."""

    name: str
    registered: bool
    status: str
    transport_type: Optional[str]
    tools: List[str]
    registration_time: Optional[datetime]
    session_active: bool


class ToolDetails(BaseModel):
    """Detailed information about a specific tool."""

    name: str
    description: str
    server_name: str
    inputSchema: Dict[str, Any]


class ServerTestResult(BaseModel):
    """Result of testing an MCP server configuration."""

    status: str  # "success" or "failed"
    server_name: str
    connection_time: Optional[float]
    tools_discovered: Optional[List[str]]
    test_tool_result: Optional[Dict[str, Any]]
    error: Optional[str]


# Track server registration times (in-memory for now)
_server_registration_times: Dict[str, datetime] = {}


@router.get("/status")
async def get_host_status(api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)):
    """
    Get the status of the MCPHost.
    """
    return {"status": "active", "tool_count": len(host.tools)}


@router.get("/", response_model=List[Dict[str, Any]])
async def list_tools(api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)):
    """
    List all available tools from the MCPHost.
    """
    return [tool.model_dump() for tool in host.tools.values()]


@router.get("/servers", response_model=List[ServerRuntimeInfo])
async def list_registered_servers(api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)):
    """
    List all currently registered MCP servers with runtime information.

    Returns runtime information about each registered server including:
    - Server name
    - Transport type
    - Number of tools provided
    - Registration time
    """
    servers = []
    for server_name in host.registered_server_names:
        # Get session info from private attribute (careful access)
        session = host._sessions.get(server_name)
        if session:
            # Count tools from this server
            tools_count = sum(1 for tool_name, sess in host._tool_to_session.items() if sess == session)

            # Get transport type from session config if available
            transport_type = "unknown"
            # Try to infer transport type from session attributes
            if hasattr(session, "_read_stream"):
                transport_type = "stdio"
            elif hasattr(session, "_http_client"):
                transport_type = "http_stream"

            servers.append(
                ServerRuntimeInfo(
                    name=server_name,
                    status="active",
                    transport_type=transport_type,
                    tools_count=tools_count,
                    registration_time=_server_registration_times.get(server_name, datetime.now()),
                )
            )

    return servers


@router.get("/servers/{server_name}", response_model=ServerDetailedStatus)
async def get_server_status(server_name: str, api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)):
    """
    Get detailed runtime status for a specific MCP server.

    Returns detailed information including:
    - Registration status
    - Transport type
    - List of tool names provided by this server
    - Session status
    """
    is_registered = server_name in host.registered_server_names

    if not is_registered:
        return ServerDetailedStatus(
            name=server_name,
            registered=False,
            status="not_registered",
            transport_type=None,
            tools=[],
            registration_time=None,
            session_active=False,
        )

    # Get session info
    session = host._sessions.get(server_name)
    session_active = session is not None

    # Get tools from this server
    server_tools = []
    if session:
        server_tools = [tool_name for tool_name, sess in host._tool_to_session.items() if sess == session]

    # Determine transport type
    transport_type = "unknown"
    if session:
        if hasattr(session, "_read_stream"):
            transport_type = "stdio"
        elif hasattr(session, "_http_client"):
            transport_type = "http_stream"

    return ServerDetailedStatus(
        name=server_name,
        registered=True,
        status="active" if session_active else "inactive",
        transport_type=transport_type,
        tools=server_tools,
        registration_time=_server_registration_times.get(server_name),
        session_active=session_active,
    )


@router.post("/register/config")
async def register_server_by_config(
    server_config: ClientConfig,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
):
    """
    Register a new MCP server with the host using a provided configuration.
    """
    try:
        await host.register_client(server_config)
        # Track registration time
        _server_registration_times[server_config.name] = datetime.now()
        return {"status": "success", "name": server_config.name}
    except MCPServerTimeoutError:
        # Let timeout errors propagate to the main exception handler
        raise
    except Exception as e:
        logger.error(f"Failed to register server '{server_config.name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/register/{server_name}")
async def register_server_by_name(
    server_name: str,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Register a new MCP server with the host by its configured name.
    """
    server_config_dict = config_manager.get_config("mcp_server", server_name)
    if not server_config_dict:
        raise HTTPException(
            status_code=404,
            detail=f"Server '{server_name}' not found in configuration.",
        )

    try:
        server_config = ClientConfig(**server_config_dict)
        await host.register_client(server_config)
        # Track registration time
        _server_registration_times[server_config.name] = datetime.now()
        return {"status": "success", "name": server_config.name}
    except Exception as e:
        logger.error(f"Failed to register server '{server_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/servers/{server_name}")
async def unregister_server(
    server_name: str,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
):
    """
    Unregister an MCP server from the host.
    """
    try:
        await host.unregister_client(server_name)
        # Clean up registration time tracking
        _server_registration_times.pop(server_name, None)
        return {"status": "success", "name": server_name}
    except Exception as e:
        logger.error(f"Failed to unregister server '{server_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/servers/{server_name}/restart")
async def restart_server(
    server_name: str,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Restart a registered MCP server.
    This is a convenience endpoint that unregisters and then re-registers the server.
    """
    logger.info(f"Attempting to restart server: {server_name}")
    try:
        # Unregister
        await host.unregister_client(server_name)
        _server_registration_times.pop(server_name, None)
        logger.info(f"Server '{server_name}' unregistered, proceeding to re-register.")

        # Re-register
        server_config_dict = config_manager.get_config("mcp_server", server_name)
        if not server_config_dict:
            raise HTTPException(
                status_code=404,
                detail=f"Server '{server_name}' not found in configuration for re-registration.",
            )

        server_config = ClientConfig(**server_config_dict)
        await host.register_client(server_config)
        _server_registration_times[server_config.name] = datetime.now()
        logger.info(f"Server '{server_name}' re-registered successfully.")

        return {"status": "success", "name": server_name}
    except HTTPException as e:
        # Re-raise HTTP exceptions directly
        raise e
    except Exception as e:
        logger.error(f"Failed to restart server '{server_name}': {e}", exc_info=True)
        # Provide a detailed error message for failures during the restart process
        raise HTTPException(status_code=500, detail=f"Failed to restart server '{server_name}': {e}") from e


@router.get("/{tool_name}", response_model=ToolDetails)
async def get_tool_details(tool_name: str, api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)):
    """
    Get detailed information about a specific tool.

    Returns:
    - Tool name and description
    - Which server provides the tool
    - Input schema for the tool
    """
    if tool_name not in host.tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")

    tool = host.tools[tool_name]

    # Find which server provides this tool
    session = host._tool_to_session.get(tool_name)
    server_name = "unknown"
    if session:
        # Find server name by matching session
        for srv_name, srv_session in host._sessions.items():
            if srv_session == session:
                server_name = srv_name
                break

    return ToolDetails(
        name=tool.name, description=tool.description or "", server_name=server_name, inputSchema=tool.inputSchema
    )


@router.get("/servers/{server_name}/tools", response_model=List[Dict[str, Any]])
async def get_server_tools(server_name: str, api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)):
    """
    List all tools provided by a specific registered server.

    Returns a list of tools with their full details.
    """
    if server_name not in host.registered_server_names:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' is not registered.")

    # Get session for this server
    session = host._sessions.get(server_name)
    if not session:
        return []

    # Find all tools from this server
    server_tools = []
    for tool_name, tool_session in host._tool_to_session.items():
        if tool_session == session:
            tool = host.tools.get(tool_name)
            if tool:
                server_tools.append(tool.model_dump())

    return server_tools


@router.post("/servers/{server_name}/test", response_model=ServerTestResult)
async def test_server(
    server_name: str,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Test an MCP server configuration by temporarily registering it.

    This endpoint:
    1. Retrieves the server configuration
    2. Temporarily registers the server
    3. Discovers available tools
    4. Optionally tests a tool execution
    5. Unregisters the server
    6. Returns test results
    """
    import time

    # Get server configuration
    server_config_dict = config_manager.get_config("mcp_server", server_name)
    if not server_config_dict:
        raise HTTPException(
            status_code=404,
            detail=f"Server '{server_name}' not found in configuration.",
        )

    start_time = time.time()
    test_result = ServerTestResult(
        status="failed",
        server_name=server_name,
        connection_time=None,
        tools_discovered=None,
        test_tool_result=None,
        error=None,
    )

    try:
        # Create config object
        server_config = ClientConfig(**server_config_dict)

        # Register the server
        await host.register_client(server_config)
        connection_time = time.time() - start_time
        test_result.connection_time = connection_time

        # Get tools from this server
        session = host._sessions.get(server_name)
        if not session:
            test_result.error = "Server registered but no session found"
            return test_result

        # Find all tools from this server
        server_tools = []
        for tool_name, tool_session in host._tool_to_session.items():
            if tool_session == session:
                server_tools.append(tool_name)

        test_result.tools_discovered = server_tools

        # If tools were discovered, try to execute the first one with a test call
        if server_tools:
            test_tool_name = server_tools[0]
            tool = host.tools.get(test_tool_name)

            if tool and tool.inputSchema:
                # Try to create a minimal valid input based on schema
                test_args = {}
                if "properties" in tool.inputSchema:
                    for prop, schema in tool.inputSchema["properties"].items():
                        if schema.get("type") == "string":
                            test_args[prop] = "test"
                        elif schema.get("type") == "number":
                            test_args[prop] = 0
                        elif schema.get("type") == "boolean":
                            test_args[prop] = False

                try:
                    await host.call_tool(test_tool_name, test_args)
                    test_result.test_tool_result = {"tool": test_tool_name, "success": True}
                except Exception as e:
                    test_result.test_tool_result = {"tool": test_tool_name, "success": False, "error": str(e)}

        test_result.status = "success"

    except Exception as e:
        test_result.error = str(e)
        logger.error(f"Error testing server '{server_name}': {e}", exc_info=True)

    finally:
        # Always try to unregister the server
        try:
            await host.unregister_client(server_name)
        except Exception as e:
            logger.warning(f"Failed to unregister test server '{server_name}': {e}")

    return test_result


@router.post("/{tool_name}/call")
async def call_tool(
    tool_name: str,
    tool_call_args: ToolCallArgs,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
):
    """
    Execute a specific tool by name with the given arguments.
    """
    if tool_name not in host.tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")

    try:
        result = await host.call_tool(tool_name, tool_call_args.args)
        return result.model_dump()
    except KeyError as e:
        # This handles the case where the tool was removed between check and call
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.") from e
    except Exception as e:
        logger.error(f"Error calling tool '{tool_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
