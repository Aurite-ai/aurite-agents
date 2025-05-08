"""
Core Agent implementation for interacting with MCP Hosts and executing tasks.
"""

import logging

# APIConnectionError and RateLimitError might be raised by the LLMClient, so keep them if used in try-except blocks.
# For now, assuming LLMClient handles these and agent only catches generic Exception or specific LLMClient exceptions.
# If Agent needs to catch these specific Anthropic errors directly from LLMClient, this import might need adjustment.
from typing import TYPE_CHECKING

from ..config.config_models import AgentConfig  # Updated import path

# Import the LLM base class directly for runtime checks
from ..llm.base_client import BaseLLM

# Import StorageManager for type hinting only if needed
if TYPE_CHECKING:
    # We still need this for StorageManager hint if used elsewhere,
    # but BaseLLM is now imported above.
    pass  # Keep the block if other type-only imports might be added

logger = logging.getLogger(__name__)


# _serialize_content_blocks function removed from here.


class Agent:
    """
    Represents an agent capable of executing tasks using an MCP Host.

    The agent is configured via an AgentConfig object and interacts with
    the LLM and tools provided by the specified MCPHost instance during execution.
    """

    def __init__(self, config: AgentConfig, llm_client: "BaseLLM"):
        """
        Initializes the Agent instance.

        Args:
            config: The configuration object for this agent.
            llm_client: An initialized instance of a BaseLLM subclass.
        """
        if not isinstance(config, AgentConfig):
            raise TypeError("config must be an instance of AgentConfig")
        if not isinstance(llm_client, BaseLLM):  # Add type check for llm_client
            raise TypeError("llm_client must be an instance of BaseLLM or its subclass")

        self.config = config
        self.llm = llm_client  # Store the passed LLM client instance

        # The Anthropic client (self.anthropic_client) is no longer initialized here.
        # The agent relies on the self.llm (BaseLLM instance) passed to it.

        logger.info(
            f"Agent '{self.config.name or 'Unnamed'}' initialized with LLM client: {type(self.llm).__name__}"
        )

    # execute_agent and _prepare_agent_result methods are removed.
    # The logic is now handled by ConversationManager.
