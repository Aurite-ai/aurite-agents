from pathlib import Path

import mcp.types as types
import pytest

from aurite.config.config_models import ClientConfig
from aurite.host_manager import Aurite


@pytest.mark.asyncio
async def test_http_server_working(with_test_config):
    """
    Tests that an stdio server can be called successfully
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        host = aurite.kernel.execution._host

        config_manager = aurite.get_config_manager()

        config_manager.refresh()

        await host.register_client(ClientConfig(**config_manager.get_config("mcp_server", "math_http_control")))

        #TODO: Update once tool distinction PR is merged
        tool_result = await host.call_tool("math_http_control-add_numbers", {"a": 1, "b": 2})

        assert tool_result is not None
        assert type(tool_result) is types.CallToolResult
        assert not tool_result.isError
        assert len(tool_result.content) > 0
