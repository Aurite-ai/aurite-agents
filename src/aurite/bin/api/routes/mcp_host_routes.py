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
async def get_host_status(
    api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)
):
    """
    Get the status of the MCPHost.
    """
    return {"status": "active", "tool_count": len(host.tools)}


@router.get("/tools", response_model=List[Dict[str, Any]])
async def list_tools(
    api_key: str = Security(get_api_key), host: MCPHost = Depends(get_host)
):
    """
    List all available tools from the MCPHost.
    """
    return [tool.model_dump() for tool in host.tools.values()]


@router.post("/register")
async def register_server(
    server_config: ClientConfig,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
):
    """
    Register a new MCP server with the host.
    """
    try:
        await host.register_client(server_config)
        return {"status": "success", "name": server_config.name}
    except Exception as e:
        logger.error(
            f"Failed to register server '{server_config.name}': {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/{tool_name}/call")
async def call_tool(
    tool_name: str,
    tool_call_args: ToolCallArgs,
    api_key: str = Security(get_api_key),
    host: MCPHost = Depends(get_host),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Execute a specific tool by name with the given arguments.
    If the tool is not found, it will attempt to register all configured MCP servers and retry.
    """
    try:
        # First attempt
        if tool_name in host.tools:
            result = await host.call_tool(tool_name, tool_call_args.args)
            return result.model_dump()

        # If tool not found, register all servers and retry
        logger.info(
            f"Tool '{tool_name}' not found. Attempting to register all configured servers."
        )
        all_configs = config_manager.get_all_configs()
        server_configs = all_configs.get("mcp_servers", {})
        logger.debug(f"Found {len(server_configs)} server configurations to process.")
        for server_name, server_config_dict in server_configs.items():
            logger.debug(f"Processing server: {server_name}")
            try:
                # A simple check to see if a server might already be registered.
                if server_name not in [
                    tool.split(".")[0] for tool in host.tools.keys()
                ]:
                    logger.debug(
                        f"Server '{server_name}' not found in host, attempting registration."
                    )
                    server_config = ClientConfig(**server_config_dict)
                    logger.debug(
                        f"Successfully created ClientConfig for '{server_name}'."
                    )
                    await host.register_client(server_config)
                    logger.info(
                        f"Successfully registered client for server: {server_name}"
                    )
                else:
                    logger.debug(
                        f"Server '{server_name}' appears to be already registered, skipping."
                    )
            except Exception as e:
                logger.error(
                    f"Failed to register server '{server_name}': {e}", exc_info=True
                )

        # Retry the tool call
        if tool_name in host.tools:
            result = await host.call_tool(tool_name, tool_call_args.args)
            return result.model_dump()
        else:
            raise KeyError(
                f"Tool '{tool_name}' not found after attempting to register all servers."
            )

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found after attempting to register all servers.",
        )
    except Exception as e:
        logger.error(f"Error calling tool '{tool_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
