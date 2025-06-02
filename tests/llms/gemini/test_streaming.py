"""
Tests for the HostManager class.
"""

import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

from src.host_manager import HostManager


class TestPromptValidation:
    @pytest.mark.timeout(300)
    async def test_workflow_prompt_validation(self, request, host_manager: HostManager):
        async for event in host_manager.execution.stream_agent_run("Mapping Agent", "What is the distance between Alice and Bob's houses?"):
            print(event)
