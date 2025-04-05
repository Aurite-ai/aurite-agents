"""
Global pytest configuration and fixtures for Aurite MCP testing.

This module provides shared fixtures and configurations for testing the Aurite MCP
framework, with special attention to agent and workflow testing fixtures.
"""

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import mcp.types as types
from mcp import ClientSession

# Import Aurite components
from src.host.host import MCPHost, HostConfig, ClientConfig
from src.host.resources.tools import ToolManager
from src.host.foundation import RootManager, SecurityManager
from src.host.communication import MessageRouter

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Global Setup and Teardown ---


def pytest_configure(config):
    """Configure pytest environment."""
    logger.info("Setting up test environment")
    # Setup can be expanded as needed


def pytest_unconfigure(config):
    """Clean up after all tests have run."""
    logger.info("Tearing down test environment")
    # Cleanup can be expanded as needed


# --- Host Testing Infrastructure ---


@pytest.fixture
async def mock_mcp_host():
    """
    Create a mock MCPHost for testing agent functionality.

    Returns a configured but not initialized host for testing.
    """
    # Mock the clients for tool and prompt servers
    mock_clients = [
        ClientConfig(
            client_id="test-client",
            server_path=Path("dummy_path"),
            roots=[],
            capabilities=["tools", "prompts"],
            timeout=5.0,
        )
    ]

    # Create host config
    config = HostConfig(clients=mock_clients)

    # Create host with mocked managers
    host = MCPHost(config)

    # Replace internal managers with mocks
    host._tool_manager = MagicMock(spec=ToolManager)
    host._prompt_manager = MagicMock()
    host._resource_manager = MagicMock()
    host._security_manager = MagicMock(spec=SecurityManager)
    host._root_manager = MagicMock(spec=RootManager)
    host._message_router = MagicMock(spec=MessageRouter)

    # Mock the tool manager's execute_tool method
    async def mock_execute_tool(tool_name, arguments):
        """Mock tool execution with predefined responses."""
        return [
            types.TextContent(
                type="text", text=f"Executed {tool_name} with {arguments}"
            )
        ]

    host._tool_manager.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    host.tools.execute_tool = AsyncMock(side_effect=mock_execute_tool)

    # Mock prepare_prompt_with_tools
    async def mock_prepare_prompt(*args, **kwargs):
        return {
            "system": "You are an AI assistant for testing.",
            "tools": [],
            "model": "claude-3-opus-20240229",
            "max_tokens": 1000,
            "temperature": 0.7,
        }

    host.prepare_prompt_with_tools = AsyncMock(side_effect=mock_prepare_prompt)

    # Mock execute_prompt_with_tools
    async def mock_execute_prompt_with_tools(*args, **kwargs):
        """Mock execute_prompt_with_tools to return test responses."""
        # Create a mock response structure similar to real Anthropic API response
        return {
            "conversation": [
                {"role": "user", "content": kwargs.get("user_message", "Test message")},
                {"role": "assistant", "content": "This is a test response."},
            ],
            "final_response": {
                "content": [{"type": "text", "text": "This is a test response."}]
            },
            "tool_uses": [],
        }

    host.execute_prompt_with_tools = AsyncMock(
        side_effect=mock_execute_prompt_with_tools
    )

    # Skip actual initialization, mocking it instead
    host.initialize = AsyncMock()
    host.shutdown = AsyncMock()

    # Return the mocked host
    return host


@pytest.fixture
def mock_tool_manager():
    """Create a mock tool manager for testing."""
    tool_manager = MagicMock(spec=ToolManager)

    # Mock the execute_tool method
    async def mock_execute_tool(tool_name, arguments):
        """Mock tool execution with predefined responses."""
        if tool_name == "evaluate_agent":
            criteria = arguments.get("criteria", {})
            agent_output = arguments.get("agent_output", "")
            expected_output = arguments.get("expected_output", "")

            # Generate a mock evaluation response
            score = 0.85  # Default score
            feedback = "This agent output meets most of the criteria."

            # Return structured response
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "score": score,
                            "feedback": feedback,
                            "criteria_scores": {
                                "accuracy": 0.9,
                                "coherence": 0.8,
                                "relevance": 0.85,
                            },
                        }
                    ),
                )
            ]

        # Default response for unknown tools
        return [
            types.TextContent(
                type="text", text=f"Executed {tool_name} with {arguments}"
            )
        ]

    # Set up the mocked methods
    tool_manager.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    tool_manager.has_tool = MagicMock(return_value=True)

    return tool_manager


@pytest.fixture
def mock_client_session():
    """Create a mock ClientSession for testing."""
    session = MagicMock(spec=ClientSession)

    # Mock the send_request method
    async def mock_send_request(request, response_type):
        """Mock send_request to return predefined responses."""
        method = getattr(request, "method", "")

        if method == "tools/list":
            # Mock tools response
            return types.ListToolsResponse(
                tools=[
                    types.Tool(
                        name="evaluate_agent",
                        description="Evaluates agent output against criteria",
                        parameters={
                            "type": "object",
                            "properties": {
                                "agent_output": {"type": "string"},
                                "criteria": {"type": "object"},
                                "expected_output": {"type": "string"},
                            },
                            "required": ["agent_output", "criteria"],
                        },
                    ),
                    types.Tool(
                        name="score_agent",
                        description="Scores agent performance",
                        parameters={
                            "type": "object",
                            "properties": {
                                "agent_output": {"type": "string"},
                                "rubric": {"type": "object"},
                            },
                            "required": ["agent_output", "rubric"],
                        },
                    ),
                ]
            )
        elif method == "prompts/list":
            # Mock prompts response
            return types.ListPromptsResponse(
                prompts=[
                    types.Prompt(
                        name="evaluation_prompt",
                        description="Prompt for agent evaluation",
                        parameters={
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    ),
                ]
            )

        # Default response for unknown requests
        return MagicMock()

    session.send_request = AsyncMock(side_effect=mock_send_request)

    # Mock other commonly used methods
    session.list_tools = AsyncMock(
        side_effect=lambda: mock_send_request(
            types.ListToolsRequest(method="tools/list"), types.ListToolsResponse
        )
    )

    session.list_prompts = AsyncMock(
        side_effect=lambda: mock_send_request(
            types.ListPromptsRequest(method="prompts/list"), types.ListPromptsResponse
        )
    )

    return session


# --- Test Data Fixtures ---


@pytest.fixture
def standard_evaluation_rubric():
    """Provide a standard evaluation rubric for testing."""
    return {
        "criteria": {
            "accuracy": {
                "description": "Correctness of information in the response",
                "weight": 0.3,
                "scoring": {
                    "1": "Contains significant factual errors",
                    "2": "Contains minor factual errors",
                    "3": "Mostly accurate with some imprecisions",
                    "4": "Highly accurate with minimal issues",
                    "5": "Perfectly accurate information",
                },
            },
            "relevance": {
                "description": "How well the response addresses the query",
                "weight": 0.3,
                "scoring": {
                    "1": "Does not address the query at all",
                    "2": "Partially addresses the query with major gaps",
                    "3": "Addresses the main points of the query",
                    "4": "Thoroughly addresses the query",
                    "5": "Comprehensively addresses all aspects of the query",
                },
            },
            "coherence": {
                "description": "Logical structure and flow of the response",
                "weight": 0.2,
                "scoring": {
                    "1": "Incoherent and disorganized",
                    "2": "Poorly structured with logical gaps",
                    "3": "Adequately structured with minor issues",
                    "4": "Well structured and easy to follow",
                    "5": "Exceptionally well structured and engaging",
                },
            },
            "completeness": {
                "description": "Thoroughness of the response",
                "weight": 0.2,
                "scoring": {
                    "1": "Critically incomplete",
                    "2": "Missing important elements",
                    "3": "Covers basic requirements",
                    "4": "Comprehensive coverage",
                    "5": "Exceptionally thorough coverage",
                },
            },
        },
        "scale": {"min": 1, "max": 5, "increment": 1},
        "passing_threshold": 3.0,
    }


@pytest.fixture
def sample_agent_output():
    """Provide sample agent output for testing evaluation."""
    return """I've analyzed the data and here are my findings:

1. Revenue increased by 15% year-over-year, reaching $2.4 million
2. Customer acquisition cost decreased from $52 to $48
3. Retention rate improved from 68% to 72%

The main growth drivers were:
- New product line expansion (+22% revenue impact)
- Improved marketing efficiency (+8% conversion rate)
- Price optimization strategy (+5% margin improvement)

Recommendations:
1. Continue investing in product expansion
2. Allocate more resources to high-converting marketing channels
3. Consider further price optimization in underperforming segments
4. Improve onboarding to boost retention further

Let me know if you need more specific analysis on any of these areas."""


@pytest.fixture
def sample_expected_output():
    """Provide sample expected output for comparison testing."""
    return """Expected analysis results:

1. Revenue increased by 15% year-over-year, reaching $2.4 million
2. Customer acquisition cost decreased from $50 to $45
3. Retention rate improved from 65% to 72%

Key growth drivers:
- New product line expansion (+20% revenue impact)
- Improved marketing efficiency (+10% conversion rate)
- Price optimization strategy (+5% margin improvement)

Recommended actions:
1. Continue investing in product expansion
2. Allocate more resources to high-performing marketing channels
3. Consider price optimization in low-margin segments
4. Improve onboarding to boost retention metrics"""


@pytest.fixture
def csv_test_data():
    """Provide sample CSV data for testing."""
    return """date,region,revenue,customers,cac,retention
2024-01-01,North,580000,1200,52,0.68
2024-01-01,South,420000,950,54,0.65
2024-01-01,East,650000,1350,51,0.70
2024-01-01,West,550000,1100,53,0.67
2024-02-01,North,590000,1250,51,0.69
2024-02-01,South,440000,1000,52,0.66
2024-02-01,East,680000,1400,50,0.71
2024-02-01,West,570000,1150,52,0.68
2024-03-01,North,620000,1300,49,0.70
2024-03-01,South,460000,1050,50,0.68
2024-03-01,East,720000,1450,48,0.73
2024-03-01,West,600000,1200,49,0.71"""


# --- Agent Testing Fixtures ---


@pytest.fixture
def evaluation_test_config():
    """Configuration for evaluation tests."""
    return {
        "num_runs": 3,
        "randomness": 0.1,
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 1000,
        "detailed_feedback": True,
        "save_results": False,
    }


# --- Utility Functions ---


@pytest.fixture
def parse_json_result():
    """Utility function to parse JSON results from tool executions."""

    def _parse(result):
        """Parse JSON from tool result text content."""
        if isinstance(result, list) and len(result) > 0:
            text_content = result[0]
            if hasattr(text_content, "text"):
                try:
                    return json.loads(text_content.text.strip())
                except json.JSONDecodeError:
                    return {"error": "Failed to parse JSON", "raw": text_content.text}
        return {"error": "Invalid result format", "raw": str(result)}

    return _parse
