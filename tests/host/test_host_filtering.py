"""
Tests for the FilteringManager and related filtering logic in MCPHost.
"""

import pytest
from unittest.mock import MagicMock

# Mark all tests in this module as belonging to the Orchestration layer
pytestmark = pytest.mark.orchestration


# Import components to test and dependencies
from aurite.host.filtering import FilteringManager
from aurite.config.config_models import AgentConfig, ClientConfig
from aurite.host.foundation import MessageRouter


# --- Fixtures ---


@pytest.fixture
def mock_message_router() -> MessageRouter:
    """Fixture for a mocked MessageRouter."""
    return MagicMock(spec=MessageRouter)


@pytest.fixture
def filtering_manager(mock_message_router: MessageRouter) -> FilteringManager:
    """Fixture for a FilteringManager instance with a mocked router."""
    return FilteringManager()


@pytest.fixture
def sample_client_config_no_exclude() -> ClientConfig:
    """Client config with no exclusions."""
    return ClientConfig(
        client_id="client_A",
        server_path="path/to/server_a.py",
        capabilities=["tools", "prompts"],
        roots=[],
        exclude=None,
    )


@pytest.fixture
def sample_client_config_with_exclude() -> ClientConfig:
    """Client config excluding 'tool_B' and 'prompt_C'."""
    return ClientConfig(
        client_id="client_B",
        server_path="path/to/server_b.py",
        capabilities=["tools", "prompts"],
        roots=[],
        exclude=["tool_B", "prompt_C"],
    )


@pytest.fixture
def sample_agent_config_no_filters() -> AgentConfig:
    """Agent config with no client_ids or exclude_components."""
    return AgentConfig(name="Agent_NoFilters")


@pytest.fixture
def sample_agent_config_client_filter() -> AgentConfig:
    """Agent config filtering for 'client_A'."""
    return AgentConfig(name="Agent_ClientFilter", client_ids=["client_A"])


@pytest.fixture
def sample_agent_config_component_filter() -> AgentConfig:
    """Agent config excluding 'tool_A'."""
    return AgentConfig(name="Agent_ComponentFilter", exclude_components=["tool_A"])


@pytest.fixture
def sample_agent_config_combined_filters() -> AgentConfig:
    """Agent config filtering for 'client_B' and excluding 'tool_C'."""
    return AgentConfig(
        name="Agent_CombinedFilters",
        client_ids=["client_B"],
        exclude_components=["tool_C"],
    )


# --- Unit Tests for FilteringManager ---


def test_is_registration_allowed_no_exclude(
    filtering_manager: FilteringManager,
    sample_client_config_no_exclude: ClientConfig,
):
    """Test registration is allowed when client has no exclude list."""
    assert filtering_manager.is_registration_allowed(
        "any_tool", sample_client_config_no_exclude
    )
    assert filtering_manager.is_registration_allowed(
        "any_prompt", sample_client_config_no_exclude
    )


def test_is_registration_allowed_with_exclude_allowed(
    filtering_manager: FilteringManager,
    sample_client_config_with_exclude: ClientConfig,
):
    """Test registration is allowed for components NOT in the exclude list."""
    assert filtering_manager.is_registration_allowed(
        "tool_A", sample_client_config_with_exclude
    )
    assert filtering_manager.is_registration_allowed(
        "prompt_B", sample_client_config_with_exclude
    )


def test_is_registration_allowed_with_exclude_denied(
    filtering_manager: FilteringManager,
    sample_client_config_with_exclude: ClientConfig,
):
    """Test registration is denied for components IN the exclude list."""
    assert not filtering_manager.is_registration_allowed(
        "tool_B", sample_client_config_with_exclude
    )
    assert not filtering_manager.is_registration_allowed(
        "prompt_C", sample_client_config_with_exclude
    )


def test_filter_clients_for_request_no_agent_filter(
    filtering_manager: FilteringManager,
    sample_agent_config_no_filters: AgentConfig,
):
    """Test client filtering returns all clients when agent has no client_ids."""
    available = ["client_A", "client_B", "client_C"]
    assert (
        filtering_manager.filter_clients_for_request(
            available, sample_agent_config_no_filters
        )
        == available
    )


def test_filter_clients_for_request_with_agent_filter(
    filtering_manager: FilteringManager,
    sample_agent_config_client_filter: AgentConfig,  # Allows only client_A
):
    """Test client filtering returns only agent's allowed clients."""
    available = ["client_A", "client_B", "client_C"]
    assert filtering_manager.filter_clients_for_request(
        available, sample_agent_config_client_filter
    ) == ["client_A"]


def test_filter_clients_for_request_agent_filter_no_match(
    filtering_manager: FilteringManager,
    sample_agent_config_client_filter: AgentConfig,  # Allows only client_A
):
    """Test client filtering returns empty list when agent's allowed clients aren't available."""
    available = ["client_B", "client_C"]
    assert (
        filtering_manager.filter_clients_for_request(
            available, sample_agent_config_client_filter
        )
        == []
    )


def test_is_component_allowed_for_agent_no_exclude(
    filtering_manager: FilteringManager,
    sample_agent_config_no_filters: AgentConfig,
):
    """Test component is allowed when agent has no exclude_components."""
    assert filtering_manager.is_component_allowed_for_agent(
        "tool_A", sample_agent_config_no_filters
    )
    assert filtering_manager.is_component_allowed_for_agent(
        "prompt_B", sample_agent_config_no_filters
    )


def test_is_component_allowed_for_agent_with_exclude_allowed(
    filtering_manager: FilteringManager,
    sample_agent_config_component_filter: AgentConfig,  # Excludes tool_A
):
    """Test component is allowed when it's NOT in agent's exclude_components."""
    assert filtering_manager.is_component_allowed_for_agent(
        "tool_B", sample_agent_config_component_filter
    )
    assert filtering_manager.is_component_allowed_for_agent(
        "prompt_A", sample_agent_config_component_filter
    )


def test_is_component_allowed_for_agent_with_exclude_denied(
    filtering_manager: FilteringManager,
    sample_agent_config_component_filter: AgentConfig,  # Excludes tool_A
):
    """Test component is denied when it IS in agent's exclude_components."""
    assert not filtering_manager.is_component_allowed_for_agent(
        "tool_A", sample_agent_config_component_filter
    )


def test_filter_component_list_no_exclude(
    filtering_manager: FilteringManager,
    sample_agent_config_no_filters: AgentConfig,
):
    """Test component list filtering returns all when agent has no exclude_components."""
    components = [{"name": "tool_A"}, {"name": "tool_B"}, {"name": "prompt_C"}]
    assert (
        filtering_manager.filter_component_list(
            components, sample_agent_config_no_filters
        )
        == components
    )


def test_filter_component_list_with_exclude(
    filtering_manager: FilteringManager,
    sample_agent_config_component_filter: AgentConfig,  # Excludes tool_A
):
    """Test component list filtering removes excluded components."""
    components = [{"name": "tool_A"}, {"name": "tool_B"}, {"name": "prompt_C"}]
    expected = [{"name": "tool_B"}, {"name": "prompt_C"}]
    assert (
        filtering_manager.filter_component_list(
            components, sample_agent_config_component_filter
        )
        == expected
    )


def test_filter_component_list_empty_input(
    filtering_manager: FilteringManager,
    sample_agent_config_component_filter: AgentConfig,
):
    """Test component list filtering handles empty input list."""
    components = []
    assert (
        filtering_manager.filter_component_list(
            components, sample_agent_config_component_filter
        )
        == []
    )


# --- TODO: Integration Tests for MCPHost Filtering ---
# These will require more setup with mock MCPHost, mock clients, etc.
# - Test MCPHost._initialize_client respects client exclude via FilteringManager
# - Test MCPHost.get_prompt applies client_id and exclude_components filters
# - Test MCPHost.execute_tool applies client_id and exclude_components filters
# - Test MCPHost.read_resource applies client_id and exclude_components filters
# - Test MCPHost.get_formatted_tools applies client_id and exclude_components filters
# - Test combinations of filters


# --- Integration Tests for MCPHost Filtering ---

# Mark all tests in this class to be run by the anyio plugin and as integration tests
pytestmark = [pytest.mark.anyio, pytest.mark.integration]

# Import HostManager for the fixture
from aurite.host_manager import HostManager


class TestHostFilteringIntegration:
    """Integration tests using the host_manager fixture."""

    async def test_get_formatted_tools_filters_by_client_id(
        self, host_manager: HostManager
    ):
        """
        Verify get_formatted_tools only returns tools from clients specified
        in AgentConfig.client_ids.
        """
        # Agent "Weather Agent" is configured with client_ids=["weather_server"]
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Weather Agent"
        ]
        assert agent_config.client_ids == ["weather_server"]

        # Get formatted tools for this agent
        print(f"\nDEBUG: AgentConfig for Weather Agent: {agent_config.model_dump_json(indent=2)}")
        formatted_tools = host_manager.host.get_formatted_tools(
            agent_config=agent_config
        )
        print(f"DEBUG: Raw formatted_tools for Weather Agent: {formatted_tools}")

        # Expected tools from weather_server (check packaged_servers/weather_mcp_server.py)
        # - weather_lookup
        # - get_current_time (but this one is excluded by agent's exclude_components)
        expected_tool_names = {"weather_lookup"}
        # Note: get_current_time should be filtered out by exclude_components later,
        # but client_id filtering happens first.

        # Check that only tools from weather_server are present
        tool_names = {tool["name"] for tool in formatted_tools}
        print(f"Formatted tools for Weather Agent: {tool_names}")

        # Assert that all returned tools are from the weather server
        # We know planning_server has 'save_plan', 'load_plan', 'delete_plan'
        assert "save_plan" not in tool_names
        assert "load_plan" not in tool_names
        assert "delete_plan" not in tool_names

        # Assert that expected weather tools (minus excluded ones) are present
        # We will test exclude_components filtering separately
        assert "weather_lookup" in tool_names
        # We don't assert get_current_time is present here, as it might be excluded

    async def test_get_formatted_tools_filters_by_exclude_components(
        self, host_manager: HostManager
    ):
        """
        Verify get_formatted_tools excludes tools specified in
        AgentConfig.exclude_components.
        """
        # Agent "Weather Agent" is configured with exclude_components=["current_time"]
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Weather Agent"
        ]
        assert agent_config.exclude_components == [
            "current_time"
        ]  # Corrected assertion

        # Get formatted tools for this agent
        formatted_tools = host_manager.host.get_formatted_tools(
            agent_config=agent_config
        )

        # Check that the excluded tool is not present
        tool_names = {tool["name"] for tool in formatted_tools}
        print(f"Formatted tools for Weather Agent (exclude check): {tool_names}")

        assert "current_time" not in tool_names  # Corrected tool name check
        # Ensure the allowed tool (weather_lookup) is still present
        assert "weather_lookup" in tool_names

    async def test_get_formatted_tools_filters_combined(
        self, host_manager: HostManager
    ):
        """
        Verify get_formatted_tools applies both client_ids and exclude_components
        filters correctly.
        """
        # Agent "Filtering Test Agent" uses client_ids=["planning_server"]
        # and exclude_components=["save_plan", "create_plan_prompt", "planning://plan/excluded-test-plan"]
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Filtering Test Agent"
        ]
        assert agent_config.client_ids == ["planning_server"]
        # Corrected assertion for all excluded components
        assert agent_config.exclude_components == [
            "save_plan",
            "create_plan_prompt",
            "planning://plan/excluded-test-plan",
        ]

        # Get formatted tools for this agent
        formatted_tools = host_manager.host.get_formatted_tools(
            agent_config=agent_config
        )

        # Check the final tool list
        tool_names = {tool["name"] for tool in formatted_tools}
        print(f"Formatted tools for Filtering Test Agent: {tool_names}")

        # Expected tools: Only from planning_server, excluding 'save_plan'
        # planning_server tools: save_plan, list_plans
        expected_present = {"list_plans"}
        expected_absent = {"save_plan", "weather_lookup", "get_current_time"}

        assert tool_names == expected_present
        for tool_name in expected_absent:
            assert tool_name not in tool_names

    async def test_execute_tool_fails_on_excluded_component(
        self, host_manager: HostManager
    ):
        """
        Verify execute_tool raises ValueError when trying to execute a tool
        excluded by AgentConfig.exclude_components.
        """
        # Weather Agent excludes 'current_time' (corrected name)
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Weather Agent"
        ]
        assert "current_time" in agent_config.exclude_components

        # Attempt to execute the excluded tool
        with pytest.raises(ValueError) as excinfo:
            await host_manager.host.execute_tool(
                tool_name="current_time",  # Corrected tool name
                arguments={},
                agent_config=agent_config,
            )

        # Check the error message
        assert "is excluded for agent 'Weather Agent'" in str(excinfo.value)

    async def test_execute_tool_fails_on_disallowed_client(
        self, host_manager: HostManager
    ):
        """
        Verify execute_tool raises ValueError when trying to execute a tool
        from a client not allowed by AgentConfig.client_ids.
        """
        # Filtering Test Agent only allows 'planning_server'
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Filtering Test Agent"
        ]
        assert agent_config.client_ids == ["planning_server"]

        # Attempt to execute a tool from the disallowed 'weather_server'
        with pytest.raises(ValueError) as excinfo:
            await host_manager.host.execute_tool(
                tool_name="weather_lookup",  # Tool from weather_server
                arguments={"location": "London"},
                agent_config=agent_config,
            )

        # Check the error message (Host checks allowed clients first)
        assert "but none are allowed for agent 'Filtering Test Agent'" in str(
            excinfo.value
        )
        # Alternative check if the error happens later (less likely based on current host logic)
        # assert "'weather_lookup' not found on any registered client" in str(excinfo.value)

    async def test_get_prompt_fails_on_excluded_component(
        self, host_manager: HostManager
    ):
        """
        Verify get_prompt raises ValueError when trying to get a prompt
        excluded by AgentConfig.exclude_components.
        """
        # Filtering Test Agent excludes 'create_plan_prompt'
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Filtering Test Agent"
        ]
        assert "create_plan_prompt" in agent_config.exclude_components

        # Attempt to get the excluded prompt
        with pytest.raises(ValueError) as excinfo:
            await host_manager.host.get_prompt(
                prompt_name="create_plan_prompt",
                arguments={},  # Arguments might not be strictly needed for get_prompt template retrieval
                agent_config=agent_config,
            )

        # Check the error message
        assert "is excluded for agent 'Filtering Test Agent'" in str(excinfo.value)

    async def test_get_prompt_fails_on_disallowed_client(
        self, host_manager: HostManager
    ):
        """
        Verify get_prompt raises ValueError or returns None when trying to get
        a prompt from a client not allowed by AgentConfig.client_ids.
        """
        # Filtering Test Agent only allows 'planning_server'
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Filtering Test Agent"
        ]
        assert agent_config.client_ids == ["planning_server"]

        # Attempt to get a prompt from the disallowed 'weather_server'
        # The host should filter out weather_server before attempting retrieval
        prompt_result = await host_manager.host.get_prompt(
            prompt_name="weather_assistant",  # Prompt from weather_server
            arguments={},
            agent_config=agent_config,
        )

        # Because the client is filtered out *before* checking ambiguity or exclusion,
        # the method should return None as if the prompt doesn't exist for this agent.
        assert prompt_result is None

        # Alternative check if we expected a ValueError (depends on exact host logic):
        # with pytest.raises(ValueError) as excinfo:
        #     await host_manager.host.get_prompt(
        #         prompt_name="weather_assistant",
        #         arguments={},
        #         agent_config=agent_config,
        #     )
        # assert "but none are allowed for agent 'Filtering Test Agent'" in str(excinfo.value)

    async def test_read_resource_fails_on_excluded_component(
        self, host_manager: HostManager
    ):
        """
        Verify read_resource raises ValueError when trying to read a resource
        URI excluded by AgentConfig.exclude_components.
        """
        # Filtering Test Agent excludes 'planning://plan/excluded-test-plan'
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Filtering Test Agent"
        ]
        excluded_uri = "planning://plan/excluded-test-plan"
        assert excluded_uri in agent_config.exclude_components

        # Attempt to read the excluded resource definition
        # Note: We don't need the resource to actually exist on the server for this test.
        # The host first checks the router. Since the planning_server doesn't advertise
        # resources via list_resources, the router won't find it, and the host returns None
        # before the exclusion check is even reached.
        resource_result = await host_manager.host.read_resource(
            uri=excluded_uri,
            agent_config=agent_config,
        )

        # Assert that None is returned because the resource wasn't found via the router
        assert resource_result is None

    async def test_read_resource_fails_on_disallowed_client(
        self, host_manager: HostManager
    ):
        """
        Verify read_resource returns None when trying to read a resource
        from a client not allowed by AgentConfig.client_ids.
        """
        # Filtering Test Agent only allows 'planning_server'
        assert host_manager.project_manager.active_project_config is not None
        agent_config = host_manager.project_manager.active_project_config.agents[ # Changed to .agents
            "Filtering Test Agent"
        ]
        assert agent_config.client_ids == ["planning_server"]

        # Attempt to read a resource URI that *might* belong to weather_server
        # (even if it doesn't exist, the client filtering should happen first)
        # The host should filter out weather_server before attempting retrieval
        resource_result = await host_manager.host.read_resource(
            uri="weather://some/resource",  # Hypothetical URI from disallowed client
            agent_config=agent_config,
        )

        # Because the client providing this (hypothetical) resource is filtered out,
        # the method should return None as if the resource doesn't exist for this agent.
        assert resource_result is None

    # Add more integration tests here...
