from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel

from ....config.config_manager import ConfigManager
from ....config.config_models import ClientConfig
from ....host.host import MCPHost
from ...dependencies import get_api_key, get_config_manager, get_host

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


class ToolCallArgs(BaseModel):
    args: Dict[str, Any]


@router.get("/status")
async def get_host_status(api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)):
    """
    Get the status of the MCPHost.
    """
    return {"status": "active", "tool_count": len(host.tools)}


@router.get("/tools", response_model=List[Dict[str, Any]])
async def list_tools(api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)):
    """
    List all available tools from the MCPHost.
    """
    return [tool.model_dump() for tool in host.tools.values()]


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
        return {"status": "success", "name": server_config.name}
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
    server_config_dict = config_manager.get_config("mcp_servers", server_name)
    if not server_config_dict:
        raise HTTPException(
            status_code=404,
            detail=f"Server '{server_name}' not found in configuration.",
        )

    try:
        server_config = ClientConfig(**server_config_dict)
        await host.register_client(server_config)
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
        return {"status": "success", "name": server_name}
    except Exception as e:
        logger.error(f"Failed to unregister server '{server_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tools/{tool_name}/call")
async def call_tool(
    tool_name: str,
    tool_call_args: ToolCallArgs,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
):
    """
    Execute a specific tool by name with the given arguments.
    """
    try:
        if tool_name not in host.tools:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")
        result = await host.call_tool(tool_name, tool_call_args.args)
        return result.model_dump()
    except KeyError as e:
        # This is now redundant, but kept for safety.
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.") from e
    except Exception as e:
        logger.error(f"Error calling tool '{tool_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
