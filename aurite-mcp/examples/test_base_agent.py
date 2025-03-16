"""
Test the BaseAgent implementation
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Import the agent classes
from src.agents.base_agent import BaseAgent, AgentTool


class MockToolManager:
    """Mock implementation of the tool manager for testing"""

    def __init__(self):
        self.tools = {
            "weather_lookup": {
                "name": "weather_lookup",
                "description": "Look up weather information for a location",
            },
            "current_time": {
                "name": "current_time",
                "description": "Get the current time in a timezone",
            },
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools"""
        return [
            {
                "name": "weather_lookup",
                "description": "Look up weather information for a location",
            },
            {
                "name": "current_time",
                "description": "Get the current time in a timezone",
            },
        ]

    def get_tool(self, name: str) -> Optional[Any]:
        """Get a tool by name"""
        if name in self.tools:
            # Create a tool object with the needed attributes
            tool = MagicMock()
            tool.name = name
            tool.description = self.tools[name]["description"]
            return tool
        return None

    def has_tool(self, name: str) -> bool:
        """Check if a tool exists"""
        return name in self.tools

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Execute a tool"""
        if tool_name == "weather_lookup":
            return [
                {
                    "text": f"Weather for {arguments.get('location', 'Unknown')}: 72°F, Sunny"
                }
            ]
        elif tool_name == "current_time":
            return [
                {
                    "text": f"Current time in {arguments.get('timezone', 'UTC')}: 2025-03-16 12:00:00"
                }
            ]
        return [{"text": "Tool not implemented"}]


class MockHost:
    """Mock implementation of the MCPHost for testing"""

    def __init__(self):
        self.tools = MockToolManager()

    async def execute_prompt_with_tools(
        self,
        prompt_name: str,
        prompt_arguments: Dict[str, Any],
        client_id: str,
        user_message: str,
        tool_names: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Mock implementation of execute_prompt_with_tools"""
        # Simulate a response with tools used
        return {
            "conversation": [
                {"role": "user", "content": user_message},
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Let me help with that."}],
                },
            ],
            "final_response": {
                "content": [
                    {"type": "text", "text": "Based on my analysis, the answer is 42."}
                ]
            },
            "tool_uses": [
                {
                    "role": "tool",
                    "tool_use_id": "123",
                    "tool_name": "weather_lookup",
                    "content": "Weather for New York: 72°F, Sunny",
                }
            ],
        }


# Create a concrete implementation of BaseAgent for testing
class TestAgent(BaseAgent):
    """Test implementation of BaseAgent"""

    async def select_tools(self, task: str, context: Dict[str, Any]) -> List[AgentTool]:
        """Select tools for a task"""
        # Simply return all available tools
        return self.tool_registry.list_tools()

    async def evaluate_result(self, result: Any) -> Dict[str, Any]:
        """Evaluate the result of a task"""
        return {"quality": 0.9, "completeness": 0.8}


async def test_base_agent():
    """Test the BaseAgent implementation"""
    logger.info("Testing BaseAgent implementation")

    # Create a mock host
    host = MockHost()

    # Create the test agent
    agent = TestAgent(host, name="test_agent")
    await agent.initialize()

    # Test executing a task with LLM
    logger.info("Testing execute_with_llm method...")
    result = await agent.execute_with_llm(
        task="What's the weather in New York?",
        prompt_name="assistant",
        prompt_arguments={"user_name": "Tester"},
        client_id="test-client",
    )

    # Check the result
    logger.info(f"Result success: {result.success}")
    logger.info(f"Result output: {result.output}")
    logger.info(f"Execution time: {result.execution_time:.2f} seconds")
    logger.info(f"Tool calls: {result.tool_calls}")

    # Check that memory stored the tool usage
    memory_items = [key for key in agent.memory.items.keys() if "tool_use" in key]
    logger.info(f"Memory items related to tool use: {memory_items}")

    return True


if __name__ == "__main__":
    asyncio.run(test_base_agent())
