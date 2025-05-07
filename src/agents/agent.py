"""
Core Agent implementation for interacting with MCP Hosts and executing tasks.
"""

import logging
import json  # Added for schema validation message formatting

# APIConnectionError and RateLimitError might be raised by the LLMClient, so keep them if used in try-except blocks.
# For now, assuming LLMClient handles these and agent only catches generic Exception or specific LLMClient exceptions.
# If Agent needs to catch these specific Anthropic errors directly from LLMClient, this import might need adjustment.
from anthropic.types import (
    MessageParam,
)  # These are for constructing messages/tool results
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import ValidationError  # Import for validation error handling

from ..host.models import AgentConfig
from ..host.host import MCPHost

# Import the new models
from .agent_models import AgentExecutionResult, AgentOutputMessage

# Import the new turn processor
from .agent_turn_processor import AgentTurnProcessor

# Import the LLM base class directly for runtime checks
from ..llm.base_client import BaseLLM

# Import StorageManager for type hinting only if needed
if TYPE_CHECKING:
    # We still need this for StorageManager hint if used elsewhere,
    # but BaseLLM is now imported above.
    pass  # Keep the block if other type-only imports might be added

logger = logging.getLogger(__name__)


# --- Helper Function for Serialization ---
def _serialize_content_blocks(content: Any) -> Any:
    """Recursively converts Anthropic content blocks into JSON-serializable dicts."""
    if isinstance(content, list):
        # Process each item in the list
        return [_serialize_content_blocks(item) for item in content]
    elif isinstance(content, dict):
        # Recursively process dictionary values
        return {k: _serialize_content_blocks(v) for k, v in content.items()}
    elif hasattr(content, "model_dump") and callable(content.model_dump):
        # Use Pydantic's model_dump for TextBlock, ToolUseBlock, etc.
        try:
            # model_dump typically returns a dict suitable for JSON
            return content.model_dump(mode="json")
        except Exception as e:
            logger.warning(
                f"Could not serialize object of type {type(content)} using model_dump: {e}. Falling back to string representation."
            )
            return str(content)  # Fallback if model_dump fails
    # Handle primitive types that are already JSON-serializable
    elif isinstance(content, (str, int, float, bool, type(None))):
        return content
    else:
        # Fallback for any other unknown types
        logger.warning(
            f"Attempting to serialize unknown type {type(content)}. Using string representation."
        )
        return str(content)


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
