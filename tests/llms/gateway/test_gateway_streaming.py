"""
Tests for the Gateway streaming
"""

import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

from aurite.host_manager import Aurite


class TestGatewayStreaming:
    @pytest.mark.timeout(300)
    async def test_workflow_prompt_validation(self, request, host_manager: Aurite):
        result = host_manager.execution.stream_agent_run(
            agent_name="OpenAI Weather Agent",
            user_message="Weather in London?"
        )


        async for event in result:
            print(event)
