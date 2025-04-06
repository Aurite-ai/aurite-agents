"""
Unit tests for the Weather MCP Server fixture.

These tests directly invoke the functions within the weather server
script (`tests/fixtures/servers/weather_mcp_server.py`) to verify
its internal logic, routing, and response formatting.
"""

import pytest
from unittest.mock import patch, AsyncMock
import pytz
from datetime import datetime

# Use relative imports assuming tests run from aurite-mcp root
# Adjust path as necessary if test structure changes
from tests.fixtures.servers.weather_mcp_server import (
    create_server,
    weather_lookup,
    current_time,
    WEATHER_ASSISTANT_PROMPT,
)
import mcp.types as types


@pytest.mark.unit
class TestWeatherMCPServerUnit:
    """Unit tests for the weather MCP server fixture."""

    @pytest.fixture
    def weather_server_app(self):
        """Provides an instance of the weather server app."""
        return create_server()

    # --- Test Tool Logic Directly ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "location, units, expected_temp_fragment, expected_cond_fragment",
        [
            ("San Francisco", "metric", "18°C", "Foggy"),
            ("New York", "metric", "22°C", "Partly Cloudy"),
            ("London", "metric", "15°C", "Rainy"),
            ("Tokyo", "metric", "25°C", "Sunny"),
            ("Unknown City", "metric", "20°C", "Clear"),  # Test default case
            ("San Francisco", "imperial", "64°F", "Foggy"),  # Test imperial units
            ("New York", None, "22°C", "Partly Cloudy"),  # Test default units (metric)
        ],
    )
    async def test_weather_lookup_logic(
        self, location, units, expected_temp_fragment, expected_cond_fragment
    ):
        """Verify the weather_lookup function returns correct mock data."""
        args = {"location": location}
        if units:
            args["units"] = units

        result = await weather_lookup(args)

        assert isinstance(result, list)
        assert len(result) == 1
        content = result[0]
        assert isinstance(content, types.TextContent)
        assert content.type == "text"
        assert f"Weather for {location}" in content.text
        assert expected_temp_fragment in content.text
        assert expected_cond_fragment in content.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "timezone, expect_error",
        [
            ("America/New_York", False),
            ("Europe/London", False),
            ("Asia/Tokyo", False),
            ("Invalid/Timezone", True),
        ],
    )
    async def test_current_time_logic(self, timezone, expect_error):
        """Verify the current_time function returns correct time or error."""
        args = {"timezone": timezone}

        # Mock datetime.now for predictable results within the test
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        if not expect_error:
            try:
                tz = pytz.timezone(timezone)
                mock_now = tz.localize(mock_now)
            except pytz.exceptions.UnknownTimeZoneError:
                pytest.fail(
                    f"Test setup error: Invalid timezone '{timezone}' used in parametrization."
                )

        with patch(
            "tests.fixtures.servers.weather_mcp_server.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(
                *args, **kw
            )  # Allow constructor

            result = await current_time(args)

            assert isinstance(result, list)
            assert len(result) == 1
            content = result[0]
            assert isinstance(content, types.TextContent)
            assert content.type == "text"

            if expect_error:
                assert f"Error: Unknown timezone: {timezone}" in content.text
            else:
                assert f"Current time in {timezone}:" in content.text
                # Check if the mocked date/time is roughly in the output
                assert "2024-01-01 12:00:00" in content.text

    # --- Test Server Handler Routing ---

    @pytest.mark.asyncio
    async def test_call_tool_routing(self, weather_server_app):
        """Verify the server's call_tool handler routes correctly."""
        # Patch the underlying implementation functions to check if they are called
        with (
            patch(
                "tests.fixtures.servers.weather_mcp_server.weather_lookup",
                new_callable=AsyncMock,
            ) as mock_lookup,
            patch(
                "tests.fixtures.servers.weather_mcp_server.current_time",
                new_callable=AsyncMock,
            ) as mock_time,
        ):
            # Test routing to weather_lookup
            await weather_server_app.call_tool(
                name="weather_lookup", arguments={"location": "London"}
            )
            mock_lookup.assert_called_once_with({"location": "London"})
            mock_time.assert_not_called()

            mock_lookup.reset_mock()

            # Test routing to current_time
            await weather_server_app.call_tool(
                name="current_time", arguments={"timezone": "Europe/Paris"}
            )
            mock_time.assert_called_once_with({"timezone": "Europe/Paris"})
            mock_lookup.assert_not_called()

            # Test unknown tool
            with pytest.raises(ValueError, match="Unknown tool: unknown_tool"):
                await weather_server_app.call_tool(name="unknown_tool", arguments={})

    # --- Test List Handlers ---

    @pytest.mark.asyncio
    async def test_list_tools_handler(self, weather_server_app):
        """Verify the list_tools handler returns the expected tools."""
        result = await weather_server_app.list_tools()
        assert isinstance(result, list)
        assert len(result) == 2
        tool_names = {tool.name for tool in result}
        assert tool_names == {"weather_lookup", "current_time"}
        for tool in result:
            assert isinstance(tool, types.Tool)

    @pytest.mark.asyncio
    async def test_list_prompts_handler(self, weather_server_app):
        """Verify the list_prompts handler returns the expected prompts."""
        result = await weather_server_app.list_prompts()
        assert isinstance(result, list)
        assert len(result) == 1
        prompt = result[0]
        assert isinstance(prompt, types.Prompt)
        assert prompt.name == "weather_assistant"

    # --- Test Get Prompt Handler ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "args, expected_substrings",
        [
            ({}, [WEATHER_ASSISTANT_PROMPT]),  # No args
            (
                {"user_name": "Ryan"},
                ["Hello Ryan!", WEATHER_ASSISTANT_PROMPT],
            ),  # Name only
            (
                {"preferred_units": "imperial"},
                ["Preferred units: IMPERIAL", WEATHER_ASSISTANT_PROMPT],
            ),  # Units only
            (
                {"user_name": "Gemini", "preferred_units": "metric"},
                ["Hello Gemini!", "Preferred units: METRIC", WEATHER_ASSISTANT_PROMPT],
            ),  # Both args
        ],
    )
    async def test_get_prompt_handler(
        self, weather_server_app, args, expected_substrings
    ):
        """Verify the get_prompt handler returns personalized prompts."""
        result = await weather_server_app.get_prompt(
            name="weather_assistant", arguments=args
        )

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 1
        message = result.messages[0]
        assert isinstance(message, types.PromptMessage)
        assert message.role == "user"
        assert isinstance(message.content, types.TextContent)
        prompt_text = message.content.text

        for substring in expected_substrings:
            assert substring in prompt_text

    @pytest.mark.asyncio
    async def test_get_prompt_handler_unknown(self, weather_server_app):
        """Verify get_prompt handler raises error for unknown prompt."""
        with pytest.raises(ValueError, match="Unknown prompt: unknown_prompt"):
            await weather_server_app.get_prompt(name="unknown_prompt", arguments={})
