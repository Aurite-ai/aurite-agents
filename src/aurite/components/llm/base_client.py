"""
LLM Client Abstraction for interacting with different LLM providers.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator  # Added AsyncGenerator
# Import Pydantic validation error

# Import our standardized output models from the agents module
from ..agents.agent_models import AgentOutputMessage
from ...config.config_models import LLMConfig  # Added import

# Import Anthropic specific types and client

# Import Anthropic specific types and client
logger = logging.getLogger(__name__)

# Default values (consider making these configurable at a higher level later)
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


class BaseLLM(ABC):
    """Abstract Base Class for LLM clients."""

    def __init__(
        self,
        model_name: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initializes the base LLM client.

        Args:
            model_name: The specific model name to use.
            temperature: The sampling temperature. Uses default if None.
            max_tokens: The maximum number of tokens to generate. Uses default if None.
            system_prompt: The default system prompt. Uses default if None.
        """
        self.model_name = model_name
        self.temperature = (
            temperature if temperature is not None else DEFAULT_TEMPERATURE
        )
        self.max_tokens = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
        self.system_prompt = (
            system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
        )
        logger.debug(f"BaseLLM initialized for model: {self.model_name}")

    @abstractmethod
    async def create_message(
        self,
        messages: List[
            Dict[str, Any]
        ],  # Expects standardized message format [{'role': str, 'content': List[Dict]}]
        tools: Optional[List[Dict[str, Any]]],  # Expects standardized tool format
        system_prompt_override: Optional[
            str
        ] = None,  # Allow overriding the default/configured system prompt
        schema: Optional[Dict[str, Any]] = None,  # Pass schema for potential injection
        llm_config_override: Optional[LLMConfig] = None,  # New parameter
    ) -> AgentOutputMessage:  # Returns our standardized message model
        """
        Sends messages to the LLM and returns a standardized response message.

        Args:
            messages: A list of message dictionaries in a standardized format.
                      Example: [{'role': 'user', 'content': [{'type': 'text', 'text': 'Hi'}]}]
            tools: A list of tool definitions in a standardized format (initially Anthropic's format).
            system_prompt_override: An optional system prompt to use instead of the default.
            schema: An optional JSON schema to guide the LLM's output format.
            llm_config_override: An optional LLMConfig object. If provided, its values
                                 (model_name, temperature, max_tokens, default_system_prompt)
                                 take precedence over the client's instance-level defaults
                                 for this specific call. The system prompt resolution hierarchy is:
                                 1. system_prompt_override (this argument)
                                 2. llm_config_override.default_system_prompt
                                 3. self.system_prompt (instance default)

        Returns:
            An AgentOutputMessage Pydantic model instance representing the LLM's response.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            Exception: Propagates exceptions from the underlying LLM API call.
        """
        raise NotImplementedError

    @abstractmethod
    async def stream_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        llm_config_override: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams messages to the LLM and yields events (text chunks, tool calls, etc.).
        The yielded dictionary should be structured to be easily convertible to an SSE data payload.
        Example yield: {"event_type": "text_delta", "data": {"text": "chunk"}}
                       {"event_type": "tool_use_start", "data": {"tool_name": "x", "input_so_far": "..."}}
        """
        raise NotImplementedError
        yield {}  # Placeholder for linter

    @abstractmethod
    async def aclose(self):
        """Closes the underlying client session."""
        raise NotImplementedError


# --- Factory Function (Example) ---
# This would likely live in a manager or registry later
# def get_llm_client(config: LLMConfig) -> BaseLLM:
#     """Creates an LLM client instance based on the configuration."""
#     if config.provider.lower() == "anthropic":
#         # API key handling needs refinement (e.g., check config.api_key_env_var first)
#         api_key = os.environ.get("ANTHROPIC_API_KEY")
#         if not api_key:
#             raise ValueError("ANTHROPIC_API_KEY environment variable not found for Anthropic provider.")
#         return AnthropicLLM(
#             model_name=config.model_name,
#             temperature=config.temperature,
#             max_tokens=config.max_tokens,
#             system_prompt=config.default_system_prompt,
#             api_key=api_key # Pass resolved key
#         )
#     # Add other providers here
#     # elif config.provider.lower() == "openai":
#     #     # ... implementation ...
#     else:
#         raise NotImplementedError(f"LLM provider '{config.provider}' is not currently supported.")
