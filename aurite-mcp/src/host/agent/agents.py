"""
Agent management for MCP Host.

This module provides an AgentManager class that handles:
1. Agent prompt preparation and execution
2. Tool integration with LLM agents
3. Integration with the host system

This is part of Layer 4 (Agent Layer) in the Host architecture.
"""

from typing import Dict, List, Optional, Any
import logging
import os
import anthropic
from anthropic.types import MessageParam, ToolUseBlock

from ..config import (
    ConfigurableManager,
    AgentConfig,
    ClientConfig,
    ConfigurationManager,
)

logger = logging.getLogger(__name__)


class AgentManager(ConfigurableManager[AgentConfig]):
    """
    Manages agent interactions, prompt execution, and tool integration.
    Part of the agent layer of the Host system.

    This manager allows the host to prepare and execute prompts with tools
    using LLM APIs like Anthropic's Claude.
    """

    def __init__(self, host):
        """
        Initialize the agent manager.

        Args:
            host: The host instance for access to all services
        """
        super().__init__("agents")
        self._host = host

    def _config_model_class(self):
        return AgentConfig

    def _validate_config_structure(self, config: Dict[str, Any]) -> bool:
        return ConfigurationManager.validate_config_structure(
            config, ["agents"], "agents"
        )

    async def register_agent(
        self, client_config: ClientConfig, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a new agent configuration.

        Args:
            client_config: The agent's client configuration
            metadata: Optional metadata for the agent

        Returns:
            True if registration was successful
        """
        try:
            if not self._config:
                self._config = AgentConfig(agents=[], metadata={})

            # Add to agents list
            self._config.agents.append(client_config)

            # Update metadata if provided
            if metadata:
                self._config.metadata[client_config.client_id] = metadata

            # Save configuration
            return await self.save_config(self._config)

        except Exception as e:
            logger.error(f"Failed to register agent {client_config.client_id}: {e}")
            return False

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents with metadata.

        Returns:
            List of agents with their configurations and metadata
        """
        if not self._config:
            return []

        agents = []
        for agent in self._config.agents:
            agent_info = {
                "client_id": agent.client_id,
                "server_path": str(agent.server_path),
                "capabilities": agent.capabilities,
                "metadata": self._config.metadata.get(agent.client_id, {}),
            }
            agents.append(agent_info)
        return agents

    def get_agent_config(self, client_id: str) -> Optional[ClientConfig]:
        """
        Get an agent's configuration by client ID.

        Args:
            client_id: The client ID of the agent

        Returns:
            The agent's configuration if found, None otherwise
        """
        if not self._config:
            return None

        for agent in self._config.agents:
            if agent.client_id == client_id:
                return agent
        return None

    async def prepare_prompt_with_tools(
        self,
        prompt_name: str,
        prompt_arguments: Dict[str, Any],
        client_id: str,
        user_message: str,
        tool_names: Optional[List[str]] = None,
        model: str = "claude-3-opus-20240229",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Prepare a prompt with tools for execution with Anthropic's API.

        Args:
            prompt_name: Name of the prompt to use
            prompt_arguments: Arguments for the prompt
            client_id: Client ID to use for the prompt
            user_message: The user message to send
            tool_names: Optional list of specific tool names to include
            model: Anthropic model to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            Dictionary containing the prepared prompt and tools data
        """
        # Get prompt result
        prompt_result = await self._host.prompts.get_prompt(
            name=prompt_name,
            client_id=client_id,
            response_data=prompt_arguments,
        )

        # Format tools for LLM
        tools_data = self._host.tools.format_tools_for_llm(tool_names)

        # Return prepared data
        return {
            "prompt": prompt_result,
            "user_message": user_message,
            "tools": tools_data,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    async def execute_prompt_with_tools(
        self,
        prompt_name: str,
        prompt_arguments: Dict[str, Any],
        client_id: str,
        user_message: str,
        tool_names: Optional[List[str]] = None,
        model: str = "claude-3-opus-20240229",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        anthropic_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a prompt with tools using Anthropic's API.

        Args:
            prompt_name: Name of the prompt to use
            prompt_arguments: Arguments for the prompt
            client_id: Client ID to use for the prompt
            user_message: The user message to send
            tool_names: Optional list of specific tool names to include
            model: Anthropic model to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            anthropic_api_key: Optional API key for Anthropic

        Returns:
            Dictionary containing conversation history and tool uses
        """
        # Prepare request data
        request_data = await self.prepare_prompt_with_tools(
            prompt_name=prompt_name,
            prompt_arguments=prompt_arguments,
            client_id=client_id,
            user_message=user_message,
            tool_names=tool_names,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Initialize Anthropic client
        api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key not provided")

        client = anthropic.AsyncAnthropic(api_key=api_key)

        # Initialize conversation
        conversation_history = []
        has_tool_calls = False
        tool_uses = []
        final_response = None

        # Add system prompt and user message
        messages = [
            {"role": "system", "content": request_data["prompt"]},
            {"role": "user", "content": request_data["user_message"]},
        ]

        # Main conversation loop
        while True:
            # Add previous messages to history
            for msg in conversation_history:
                if isinstance(msg["content"], str):
                    messages.append({"role": msg["role"], "content": msg["content"]})
                else:
                    messages.append(msg)

            # Make API call
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
                tools=request_data["tools"],
            )

            # Get the final response
            final_response = response.content[0].text

            # Check for tool calls
            tool_calls = response.tool_calls
            if not tool_calls:
                break

            has_tool_calls = True
            tool_results = []

            # Execute each tool
            for tool_use in tool_calls:
                logger.info(f"Executing tool: {tool_use.name}")
                try:
                    tool_result = await self._host.tools.execute_tool(
                        tool_name=tool_use.name, arguments=tool_use.input
                    )

                    # Use ToolManager to format the tool result
                    tool_results.append(
                        self._host.tools.create_tool_result_blocks(
                            tool_use.id, tool_result
                        )
                    )

                except Exception as e:
                    logger.error(f"Error executing tool {tool_use.name}: {e}")
                    # Create an error result using the same format
                    tool_results.append(
                        self._host.tools.create_tool_result_blocks(
                            tool_use.id,
                            f"Error executing tool {tool_use.name}: {str(e)}",
                        )
                    )

                messages.append({"role": "user", "content": tool_results})

                # Track for return data
                tool_uses = tool_results

        # Return the complete conversation history and final response
        return {
            "conversation": conversation_history,
            "final_response": final_response,
            "tool_uses": tool_uses if has_tool_calls else [],
        }

    async def shutdown(self):
        """Shutdown the agent manager"""
        logger.info("Shutting down agent manager")
        # Clear configurations
        if self._config:
            self._config.agents.clear()
            self._config.metadata.clear()
