from pathlib import Path

import mcp.types as types
import pytest

from aurite.aurite import Aurite
from aurite.lib.models.config.components import ClientConfig


@pytest.mark.anyio
async def test_stdio_server_working(with_test_config):
    """
    Tests that an stdio server can be called successfully
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        await host.register_client(ClientConfig(**config_manager.get_config("mcp_server", "weather_server_control")))

        tool_result = await host.call_tool("weather_server_control-weather_lookup", {"location": "London"})

        assert tool_result is not None
        assert type(tool_result) is types.CallToolResult
        assert not tool_result.isError
        assert len(tool_result.content) > 0


@pytest.mark.anyio
async def test_stdio_server_wrong_args(with_test_config):
    """
    Tests that an stdio server handles incorrect arguments
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        await host.register_client(ClientConfig(**config_manager.get_config("mcp_server", "weather_server_control")))

        tool_result = await host.call_tool("weather_server_control-weather_lookup", {"sdfsdf": "sdffsdfsdf"})

        assert tool_result is not None
        assert type(tool_result) is types.CallToolResult
        assert tool_result.isError


@pytest.mark.anyio
async def test_stdio_server_tool_dne(with_test_config):
    """
    Tests that a error is raised if a nonexistant tool is called
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        await host.register_client(ClientConfig(**config_manager.get_config("mcp_server", "weather_server_control")))

        with pytest.raises(Exception):
            await host.call_tool("asdf", {"sdfsdf": "sdffsdfsdf"})


@pytest.mark.anyio
async def test_stdio_server_incorrect_path(with_test_config):
    """
    Tests that a error is raised if a server is registered with an incorrect path
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        with pytest.raises(Exception):
            await host.register_client(
                ClientConfig(**config_manager.get_config("mcp_server", "weather_server_invalid_server_path"))
            )
