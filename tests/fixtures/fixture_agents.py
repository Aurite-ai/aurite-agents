"""
Pytest fixtures related to Agent configuration and setup.
"""

import pytest

from aurite.lib.models.config.components import AgentConfig


@pytest.fixture
def minimal_agent_config() -> AgentConfig:
    """Provides a minimal AgentConfig with only a name."""
    return AgentConfig(name="TestAgentMinimal")


@pytest.fixture
def agent_config_with_mcp_servers() -> AgentConfig:
    """AgentConfig with specific mcp_servers."""
    return AgentConfig(name="TestAgentWithServers", mcp_servers=["weather_server", "planning_server"])


@pytest.fixture
def agent_config_with_llm() -> AgentConfig:
    """AgentConfig with LLM config and overrides."""
    return AgentConfig(
        name="TestAgentLLM",
        llm_config_id="anthropic_claude_3_haiku",
        system_prompt="You are a test agent.",
        max_iterations=3,
        include_history=True,
        mcp_servers=["weather_server"],
    )


@pytest.fixture
def agent_config_with_exclusions() -> AgentConfig:
    """AgentConfig with excluded components."""
    return AgentConfig(
        name="TestAgentExclusions",
        mcp_servers=["planning_server"],
        exclude_components=["save_plan", "create_plan_prompt"],
    )
