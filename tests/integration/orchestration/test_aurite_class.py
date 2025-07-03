import pytest
import json
from unittest.mock import AsyncMock, patch
from pathlib import Path
import tempfile

from aurite.host_manager import Aurite
from aurite.components.agents.agent_models import AgentRunResult
from openai.types.chat import ChatCompletionMessage


@pytest.fixture
def temp_project_root():
    """Creates a temporary directory for a test project."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        (project_root / "config").mkdir()

        config_data = {
            "agents": [
                {
                    "name": "TestAgent",
                    "llm_config_id": "test_llm",
                    "mcp_servers": ["test_server"],
                },
            ],
            "llms": [{"name": "test_llm", "provider": "test", "model": "test"}],
            "mcp_servers": [
                {
                    "name": "test_server",
                    "transport_type": "stdio",
                    "server_path": "/bin/true",
                    "capabilities": ["tools"],
                }
            ],
        }
        with open(project_root / "config" / "project.json", "w") as f:
            json.dump(config_data, f)

        yield project_root


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
@patch("importlib.resources.files")
async def test_aurite_initialization_and_agent_run(mock_files, temp_project_root):
    """
    Tests that the main Aurite class initializes correctly and can run an agent,
    triggering the JIT registration process.
    """
    # Arrange
    mock_files.return_value.joinpath.return_value.is_dir.return_value = False

    # Mock the connect_to_server method to prevent actual network/process calls
    with patch(
        "mcp.client.session_group.ClientSessionGroup.connect_to_server",
        new_callable=AsyncMock,
    ) as mock_connect:
        async with Aurite(project_root=temp_project_root) as aurite:
            # Mock the agent's conversation run
            with patch(
                "aurite.components.agents.agent.Agent.run_conversation",
                new_callable=AsyncMock,
            ) as mock_run_conv:
                mock_run_conv.return_value = AgentRunResult(
                    status="success",
                    final_response=ChatCompletionMessage(
                        role="assistant", content="Success"
                    ),
                    conversation_history=[],
                    error_message=None,
                )

                # Act
                result = await aurite.run_agent("TestAgent", "Hello")

                # Assert
                assert result.status == "success"
                assert result.final_response is not None
                assert result.final_response.content == "Success"

                # Verify that the server was registered via JIT
                mock_connect.assert_awaited_once()

                # Verify the agent's run_conversation was called
                mock_run_conv.assert_awaited_once()
