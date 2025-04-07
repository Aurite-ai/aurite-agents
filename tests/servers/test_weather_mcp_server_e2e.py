"""
E2E tests for the Weather MCP Server fixture using a real host.

These tests utilize the `real_mcp_host` fixture (configured via
`config/agents/testing_config.json` to run the weather server)
to verify the server's tool and prompt functionality through host interactions.
"""

import pytest
import logging

# Use relative imports assuming tests run from aurite-mcp root
from src.host.host import MCPHost
import mcp.types as types

# Configure logging for debugging E2E tests if needed
logger = logging.getLogger(__name__)

# Define the client ID used in testing_config.json for the weather server
WEATHER_CLIENT_ID = "weather_server_test"


@pytest.mark.e2e
# Apply xfail due to the known host shutdown issue with the fixture
@pytest.mark.xfail(
    reason="Known issue with real_mcp_host teardown async complexity", strict=False
)
class TestWeatherMCPServerE2E:
    """E2E tests for the weather MCP server fixture via the host."""

    @pytest.fixture(autouse=True)
    def check_client_exists(self, real_mcp_host: MCPHost):
        """Fixture to ensure the weather client is loaded before tests run."""
        if WEATHER_CLIENT_ID not in real_mcp_host.clients:
            pytest.skip(
                f"Weather server client '{WEATHER_CLIENT_ID}' not found in host config. "
                "Ensure it's defined in config/agents/testing_config.json"
            )
        logger.info(f"Host fixture confirmed client '{WEATHER_CLIENT_ID}' is loaded.")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "location, units, expected_temp_fragment, expected_cond_fragment",
        [
            ("San Francisco", "metric", "18°C", "Foggy"),
            ("New York", "metric", "22°C", "Partly Cloudy"),
            ("London", "imperial", "59°F", "Rainy"),  # 15C -> 59F
            ("Tokyo", None, "25°C", "Sunny"),  # Default units
            ("Unknown City", "metric", "20°C", "Clear"),
        ],
    )
    async def test_weather_lookup_tool_e2e(
        self,
        real_mcp_host: MCPHost,
        location,
        units,
        expected_temp_fragment,
        expected_cond_fragment,
    ):
        """Verify the weather_lookup tool via host.tools.execute_tool."""
        host = real_mcp_host
        args = {"location": location}
        if units:
            args["units"] = units

        logger.info(f"Calling weather_lookup tool with args: {args}")
        result = await host.tools.execute_tool(
            client_name=WEATHER_CLIENT_ID, tool_name="weather_lookup", arguments=args
        )

        assert isinstance(result, list)
        assert len(result) == 1
        content = result[0]
        assert isinstance(content, types.TextContent)
        assert content.type == "text"
        logger.debug(f"Received weather_lookup response: {content.text}")
        assert f"Weather for {location}" in content.text
        assert expected_temp_fragment in content.text
        assert expected_cond_fragment in content.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "timezone, expect_error, expected_fragment",
        [
            ("America/New_York", False, "Current time in America/New_York:"),
            ("Europe/London", False, "Current time in Europe/London:"),
            ("Invalid/Timezone", True, "Error: Unknown timezone: Invalid/Timezone"),
        ],
    )
    async def test_current_time_tool_e2e(
        self, real_mcp_host: MCPHost, timezone, expect_error, expected_fragment
    ):
        """Verify the current_time tool via host.tools.execute_tool."""
        host = real_mcp_host
        args = {"timezone": timezone}

        logger.info(f"Calling current_time tool with args: {args}")
        result = await host.tools.execute_tool(
            client_name=WEATHER_CLIENT_ID, tool_name="current_time", arguments=args
        )

        assert isinstance(result, list)
        assert len(result) == 1
        content = result[0]
        assert isinstance(content, types.TextContent)
        assert content.type == "text"
        logger.debug(f"Received current_time response: {content.text}")
        assert expected_fragment in content.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "args, expected_substrings",
        [
            ({}, ["You are a helpful weather assistant"]),  # Base prompt
            (
                {"user_name": "Ryan"},
                ["Hello Ryan!", "You are a helpful weather assistant"],
            ),
            ({"preferred_units": "imperial"}, ["Preferred units: IMPERIAL"]),
            (
                {"user_name": "Gemini", "preferred_units": "metric"},
                ["Hello Gemini!", "Preferred units: METRIC"],
            ),
        ],
    )
    async def test_get_prompt_e2e(
        self, real_mcp_host: MCPHost, args, expected_substrings
    ):
        """Verify the get_prompt for weather_assistant via host.prompts.get_prompt."""
        host = real_mcp_host

        logger.info(f"Calling host.get_prompt with args: {args}")
        # Call the host's get_prompt method, which handles discovery/execution
        # Note: The weather server's _get_prompt_handler actually returns GetPromptResult
        # So, although host.get_prompt usually returns Prompt definition, in this E2E
        # test against this specific server, we expect GetPromptResult back.
        # This highlights a slight inconsistency, but the test should work as is.
        result = await host.get_prompt(  # Call host method
            client_name=WEATHER_CLIENT_ID,  # Pass client_name
            prompt_name="weather_assistant",
            arguments=args,  # Pass arguments
        )

        # The weather server's handler returns GetPromptResult, so assert that
        assert isinstance(result, types.GetPromptResult), (
            f"Expected GetPromptResult, but got {type(result)}"
        )
        assert len(result.messages) == 1
        message = result.messages[0]
        assert isinstance(message, types.PromptMessage)
        assert message.role == "user"
        assert isinstance(message.content, types.TextContent)
        prompt_text = message.content.text
        logger.debug(f"Received get_prompt response text: {prompt_text}")

        for substring in expected_substrings:
            assert substring in prompt_text
