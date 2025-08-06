from pathlib import Path

import pytest

from aurite.aurite import Aurite
from aurite.lib.models.config.components import ClientConfig
from aurite.utils.errors import MCPServerTimeoutError


@pytest.mark.asyncio
async def test_stdio_server_working(with_test_config):
    """
    Tests that a stdio server will handle a tool timeout properly
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        await host.register_client(ClientConfig(**config_manager.get_config("mcp_server", "error_stdio_server")))

        with pytest.raises(MCPServerTimeoutError):
            await host.call_tool("error_stdio_server-timeout", {"a": 1, "b": 2})


@pytest.mark.asyncio
@pytest.mark.parametrize("start_http_server", ["tests/fixtures/mcp_servers/error_http_server.py"], indirect=True)
async def test_http_server_error(with_test_config, start_http_server):
    """
    Tests that an http server will handle a tool timeout properly
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        await host.register_client(ClientConfig(**config_manager.get_config("mcp_server", "error_http_server")))

        with pytest.raises(MCPServerTimeoutError):
            await host.call_tool("error_http_server-timeout", {"a": 1, "b": 2})
