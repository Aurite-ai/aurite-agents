"""
Pytest fixtures related to Agent configuration and setup.
"""

import pytest

# Use relative imports assuming tests run from aurite-mcp root
from src.host.models import AgentConfig


@pytest.fixture
def minimal_agent_config() -> AgentConfig:
    """Provides a minimal AgentConfig."""
    return AgentConfig(name="TestAgentMinimal")


@pytest.fixture
def agent_config_with_llm_params() -> AgentConfig:
    """Provides an AgentConfig with specific LLM parameters."""
    return AgentConfig(
        name="TestAgentLLM",
        model="test-model-override",
        temperature=0.5,
        max_tokens=100,
        max_iterations=5,  # Add example value
        system_prompt="Test system prompt override.",
    )


# Note: This fixture depends on mock_host_config, which will be moved
# to host_fixtures.py. Pytest will discover and inject it correctly.
@pytest.fixture
def agent_config_with_mock_host(mock_host_config) -> AgentConfig:
    """
    Provides an AgentConfig linked to a mock HostConfig.
    Requires the mock_host_config fixture (defined in host_fixtures.py).
    """
    return AgentConfig(name="TestAgentWithHostCfg", host=mock_host_config)
