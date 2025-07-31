from pathlib import Path

import mcp.types as types
import pytest

from aurite.aurite import Aurite
from aurite.config.config_models import ClientConfig


@pytest.mark.asyncio
async def test_local_server_working(with_test_config):
    """
    Tests that an local server can be called successfully
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        await host.register_client(ClientConfig(**config_manager.get_config("mcp_server", "duckduckgo_local_control")))

        tool_result = await host.call_tool("duckduckgo_local_control-search", {"query": "London", "max_results": 1})

        assert tool_result is not None
        assert type(tool_result) is types.CallToolResult
        assert not tool_result.isError
        assert len(tool_result.content) > 0


@pytest.mark.asyncio
async def test_local_server_wrong_tool_args(with_test_config):
    """
    Tests that an local server handles incorrect tool arguments
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        await host.register_client(ClientConfig(**config_manager.get_config("mcp_server", "duckduckgo_local_control")))

        tool_result = await host.call_tool("duckduckgo_local_control-search", {"sdfsdf": "sdffsdfsdf"})

        assert tool_result is not None
        assert type(tool_result) is types.CallToolResult
        assert tool_result.isError


@pytest.mark.asyncio
async def test_local_server_wrong_keys(with_test_config):
    """
    Tests that an local server handles incorrect arguments
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        with pytest.raises(Exception):
            await host.register_client(
                ClientConfig(**config_manager.get_config("mcp_server", "duckduckgo_local_invalid_both"))
            )
