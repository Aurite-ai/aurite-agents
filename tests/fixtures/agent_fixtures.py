"""
Pytest fixtures related to Agent configuration and setup.
"""

import pytest

# Use relative imports assuming tests run from aurite-mcp root
from src.config.config_models import AgentConfig


@pytest.fixture
def minimal_agent_config() -> AgentConfig:
    """Provides a minimal AgentConfig with no client filter."""
    return AgentConfig(name="TestAgentMinimal", client_ids=None)


@pytest.fixture
def agent_config_filtered() -> AgentConfig:
    """Provides an AgentConfig with specific client_ids for filtering."""
    return AgentConfig(name="TestAgentFiltered", client_ids=["client-a", "client-c"])


@pytest.fixture
def agent_config_with_llm_params() -> AgentConfig:
    """Provides an AgentConfig with specific LLM parameters."""
    return AgentConfig(
        name="TestAgentLLM",
        model="test-model-override",
        temperature=0.5,
        max_tokens=100,
        max_iterations=5,
        system_prompt="Test system prompt override.",
        client_ids=["client-b"],  # Example filter for this config
    )


# Removed agent_config_with_mock_host as it's no longer relevant
# since AgentConfig doesn't directly hold HostConfig anymore.
