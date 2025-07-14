from pathlib import Path

import pytest

from aurite.host_manager import Aurite


@pytest.mark.asyncio
async def test_http_agent_working(with_test_config):
    """
    Tests that an http server can be called successfully by an agent
    """
    example_project_path = Path(".aurite").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        execution_facade = aurite.kernel.execution

        result = await execution_facade.run_agent(
            agent_name="Duckduckgo Agent HTTP Control",
            user_message="What is the weather in London?",
        )

        assert result is not None
        assert result.error_message is None
        assert result.final_response is not None
        assert result.conversation_history is not None

        tool_call_found = False
        tool_result_found = False
        for message in result.conversation_history:
            if "tool_calls" in message and message["tool_calls"] is not None:
                if message["tool_calls"][0]["function"]["name"] == 'duckduckgo_http_control-search':
                    tool_call_found = True

            if "role" in message and "name" in message and message["role"] == "tool" and message["name"] == "duckduckgo_http_control-search":
                tool_result_found = True

        assert tool_call_found
        assert tool_result_found
