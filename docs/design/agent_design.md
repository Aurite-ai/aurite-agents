# Agent, Client, and LLM Design Document

## 1. Introduction

This document outlines the current design of the `Agent` class, its configuration (`AgentConfig`), and related components within the Aurite Agents framework. It also proposes a new Pydantic model for standardizing agent execution results and explores a refactoring strategy to introduce a dedicated `LLM` configuration and class for managing Large Language Model interactions.

The goals of this design discussion are to:
- Improve the clarity and maintainability of the `Agent` class.
- Provide a more robust and developer-friendly way to handle agent outputs.
- Enhance the modularity and extensibility of the framework, particularly for supporting different LLM providers and configurations.

## 2. Current State

### 2.1. `AgentConfig` (`src/host/models.py`)

-   **Purpose:** Defines the configuration for an individual `Agent` instance. It specifies agent-specific settings, LLM parameters, and its relationship with the MCP Host for accessing tools and resources.
-   **Key Fields:**
    -   `name: Optional[str]`: An optional name for the agent instance.
    -   `client_ids: Optional[List[str]]`: A list of MCP `ClientConfig` IDs that this agent is allowed to use. This filters the tools and resources available to the agent via the `MCPHost`.
    -   `system_prompt: Optional[str]`: The default system prompt for the agent.
    -   `schema: Optional[dict]`: A JSON schema used to validate the agent's output if provided. The agent will attempt to ensure its responses conform to this schema.
    -   `model: Optional[str]`: The specific LLM model to be used (e.g., "claude-3-opus-20240229").
    -   `temperature: Optional[float]`: The sampling temperature for the LLM.
    -   `max_tokens: Optional[int]`: The maximum number of tokens the LLM should generate.
    -   `max_iterations: Optional[int]`: The maximum number of turns in a conversation loop (LLM call -> tool use -> LLM call) before the agent stops.
    -   `include_history: Optional[bool]`: If `True`, the agent attempts to load and save conversation history using a `StorageManager`.
    -   `exclude_components: Optional[List[str]]`: A list of specific component names (tools, prompts, resources) to exclude for this agent, even if provided by its allowed `client_ids`.
    -   `evaluation: Optional[str]`: (Currently used by prompt validation) Specifies an evaluation mechanism.
-   **Usage:** An `AgentConfig` instance is passed to the `Agent` class during its initialization.

### 2.2. `Agent` Class (`src/agents/agent.py`)

-   **Purpose:** The `Agent` class is the core component responsible for orchestrating interactions with an LLM, managing conversation flow, handling tool execution via an `MCPHost`, and managing conversation history (if configured).
-   **Initialization (`__init__`)**:
    -   Takes an `AgentConfig` object.
    -   Initializes an `AsyncAnthropic` client using the `ANTHROPIC_API_KEY` environment variable.
-   **Key External Method (`execute_agent`)**:
    -   **Inputs:**
        -   `user_message: str`: The user's input to the agent.
        -   `host_instance: MCPHost`: The MCPHost instance providing access to tools and resources.
        -   `storage_manager: Optional["StorageManager"]`: (Optional) For loading/saving conversation history.
        -   `system_prompt: Optional[str]`: (Optional) Allows overriding the agent's default system prompt for a specific execution.
        -   `session_id: Optional[str]`: (Optional) Used as a key for loading/saving conversation history.
    -   **Outputs:** Returns a Python dictionary with the following keys:
        -   `"conversation"`: A list of message dictionaries representing the full conversation history. The content of these messages (especially assistant messages) is serialized from Anthropic Pydantic models into plain Python dictionaries/lists using `_serialize_content_blocks`.
        -   `"final_response"`: A Python dictionary representing the serialized form of the final `anthropic.types.Message` object from the LLM (or `None` if an error occurred before a final response). This serialization is done by `_serialize_content_blocks`.
        -   `"tool_uses"`: A list of dictionaries detailing any tools used in the last turn of the conversation that led to the `final_response`.
        -   `"error"`: An error message string if an agent execution error occurred, otherwise `None`.
    -   **Core Logic:**
        1.  Validates the `host_instance`.
        2.  Determines LLM parameters (model, temperature, max_tokens, system_prompt) from its `AgentConfig`, allowing overrides from the `system_prompt` argument.
        3.  Retrieves formatted tool definitions from the `host_instance` using `host_instance.get_formatted_tools(agent_config=self.config)`, which respects `client_ids` and `exclude_components` from the `AgentConfig`.
        4.  Initializes the message history. If `include_history` is true and `storage_manager` and `session_id` are provided, it attempts to load past messages.
        5.  Appends the current `user_message` to the history.
        6.  Enters a conversation loop (up to `max_iterations`):
            a.  Calls `_make_llm_call` to get a response from the LLM.
            b.  Appends the LLM's raw response (as `MessageParam`) to the history for the next turn.
            c.  Checks the LLM response's `stop_reason`:
                i.  If not `"tool_use"`:
                    -   Extracts text content.
                    -   If `self.config.schema` is defined, it attempts to parse the text as JSON and validate it against the schema. If parsing or validation fails, it appends a corrective message to the history and continues the loop to ask the LLM to fix its output.
                    -   If schema validation passes (or no schema is defined), this response is considered the `final_response`, and the loop breaks.
                ii. If `"tool_use"`:
                    -   Iterates through `ToolUseBlock`s in the LLM response.
                    -   For each tool call, it executes the tool using `host_instance.execute_tool()`.
                    -   Appends the tool results (or error messages if tool execution failed) to the message history for the next LLM call.
        7.  If `include_history` is true and `storage_manager` and `session_id` are provided, it attempts to save the full (serialized) conversation history.
        8.  Constructs and returns the output dictionary, ensuring `conversation` and `final_response` contents are serialized using `_serialize_content_blocks`.
-   **Key Internal Method (`_make_llm_call`)**:
    -   **Inputs:** `messages`, `system_prompt`, `tools` (Anthropic format), `model`, `temperature`, `max_tokens`.
    -   **Outputs:** An `anthropic.types.Message` object.
    -   **Core Logic:**
        -   If `self.config.schema` is present, it injects the JSON schema definition and instructions for JSON output into the `system_prompt`.
        -   Constructs the arguments for the `self.anthropic_client.messages.create()` call.
        -   Makes the asynchronous API call to Anthropic.
-   **Helper Function (`_serialize_content_blocks`)**:
    -   **Purpose:** Recursively traverses nested structures (lists, dicts) and converts Anthropic Pydantic model instances (like `Message`, `TextBlock`, `ToolUseBlock`) into their JSON-serializable dictionary representations using their `.model_dump(mode="json")` method. Handles primitive types directly.
-   **Dependencies:** `AgentConfig`, `MCPHost`, `StorageManager` (optional), `anthropic` SDK (AsyncAnthropic, Message, MessageParam, ToolUseBlock), `jsonschema` (if schema validation is used).

## 3. Proposed `AgentExecutionResult` Pydantic Model

To provide a more stable and developer-friendly contract for agent outputs, we propose introducing a set of Pydantic models specific to the Aurite framework.

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

# --- Agent Output Models ---

class AgentOutputContentBlock(BaseModel):
    """Represents a single block of content within an agent's message."""
    type: str = Field(description="The type of content block (e.g., 'text', 'tool_use').")

    # Fields for 'text' type
    text: Optional[str] = Field(None, description="The text content, if the block is of type 'text'.")

    # Fields for 'tool_use' type (mirroring Anthropic's ToolUseBlock for consistency if needed)
    id: Optional[str] = Field(None, description="The ID of the tool use, if the block is of type 'tool_use'.")
    input: Optional[Dict[str, Any]] = Field(None, description="The input provided to the tool, if the block is of type 'tool_use'.")
    name: Optional[str] = Field(None, description="The name of the tool used, if the block is of type 'tool_use'.")

    # Fields for 'tool_result' type (mirroring Anthropic's ToolResultBlock for consistency if needed)
    tool_use_id: Optional[str] = Field(None, description="The ID of the tool use this result corresponds to, if block is 'tool_result'.")
    # content for tool_result can be a string (e.g. error) or structured data.
    # For simplicity here, we might keep it as a string or a list of further content blocks if complex.
    # Let's assume for now tool_result content is primarily text or a simple JSON structure.
    # If tool_result content can itself be complex (list of blocks), this model might need adjustment
    # or content: Union[str, List['AgentOutputContentBlock'], None] = None
    # For now, let's assume tool results are primarily textual or simple dicts when serialized.
    # The _serialize_content_blocks already handles .model_dump() for these.

    # Allow other fields for future extensibility or other block types
    class Config:
        extra = 'allow'

class AgentOutputMessage(BaseModel):
    """Represents a single message in the agent's conversation or its final response."""
    role: str = Field(description="The role of the message sender (e.g., 'user', 'assistant').")
    content: List[AgentOutputContentBlock] = Field(description="A list of content blocks comprising the message.")

    # Optional fields that might be present in a final response message
    id: Optional[str] = Field(None, description="The unique ID of the message, if applicable (e.g., from LLM provider).")
    model: Optional[str] = Field(None, description="The model that generated this message, if applicable.")
    stop_reason: Optional[str] = Field(None, description="The reason the LLM stopped generating tokens, if applicable.")
    stop_sequence: Optional[str] = Field(None, description="The specific sequence that caused the LLM to stop, if applicable.")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information for this message generation, if applicable.")

class AgentExecutionResult(BaseModel):
    """
    Standardized Pydantic model for the output of Agent.execute_agent().
    """
    conversation: List[AgentOutputMessage] = Field(description="The complete conversation history, with all messages and their content.")
    final_response: Optional[AgentOutputMessage] = Field(None, description="The final message from the assistant, if one was generated.")
    tool_uses_in_final_turn: List[Dict[str, Any]] = Field(default_factory=list, description="Details of tools used in the turn that led to the final_response.")
    error: Optional[str] = Field(None, description="An error message if the agent execution failed at some point.")

    @property
    def primary_text(self) -> Optional[str]:
        """Helper property to get the primary text from the final_response."""
        if self.final_response and self.final_response.content:
            for block in self.final_response.content:
                if block.type == "text" and block.text is not None:
                    return block.text
        return None

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def final_tool_calls(self) -> List[Dict[str, Any]]: # Kept for direct access if needed
        """Returns the tool_uses_in_final_turn list."""
        return self.tool_uses_in_final_turn
```

-   **Modification to `Agent.execute_agent()`:**
    -   The method would first construct the current output dictionary (with serialized `conversation` and `final_response` as it does now).
    -   Then, it would parse this dictionary into an `AgentExecutionResult` instance using `AgentExecutionResult.model_validate(output_dict)`.
    -   The method would then return this `AgentExecutionResult` Pydantic object.
-   **Benefits:**
    -   Consumers receive a type-safe, validated object.
    -   Easier and safer access to data (e.g., `result.primary_text`, `result.final_response.role`).
    -   Clear contract for agent outputs, self-documenting.
    -   FastAPI can directly serialize these Pydantic models for API responses.

## 4. Proposed `LLM` Configuration and Class Refactoring

To improve modularity and support for various LLM providers, we propose abstracting LLM-specific logic into a dedicated configuration and class.

### 4.1. `LLMConfig` (New Pydantic Model)

To be defined in `src/host/models.py` or a new `src/llm/models.py`.

```python
# Example LLMConfig
class LLMConfig(BaseModel):
    llm_id: str = Field(description="Unique identifier for this LLM configuration.")
    provider: str = Field(default="anthropic", description="The LLM provider (e.g., 'anthropic', 'openai', 'gemini').")
    model_name: str = Field(description="The specific model name for the provider.")

    # Common LLM parameters
    temperature: Optional[float] = Field(None, description="Default sampling temperature.")
    max_tokens: Optional[int] = Field(None, description="Default maximum tokens to generate.")
    default_system_prompt: Optional[str] = Field(None, description="A default system prompt for this LLM configuration.")

    # Provider-specific settings (could be a flexible Dict or union of specific config objects)
    # For Anthropic, API key is typically via env var. Other providers might need explicit keys here.
    # api_key_env_var: Optional[str] = Field(None, description="Environment variable name for the API key.")
    # credentials_path: Optional[Path] = Field(None, description="Path to credentials file for some providers.")

    class Config:
        extra = 'allow' # Allow provider-specific fields
```

### 4.2. `AgentConfig` Modifications

-   Add `llm_config_id: Optional[str] = None` to `AgentConfig`.
    -   If `llm_config_id` is provided, the agent will use the corresponding `LLMConfig`.
    -   The existing `model`, `temperature`, `max_tokens`, `system_prompt` fields in `AgentConfig` will then act as **overrides** to the values from the chosen `LLMConfig`.
-   If `llm_config_id` is NOT provided, the agent falls back to using the direct `model`, `temperature`, etc., fields in `AgentConfig` (as it does now), potentially with hardcoded defaults for the provider (e.g., Anthropic).

### 4.3. New `LLMClient` / `LLMService` (e.g., in `src/llm/client.py`)

-   **Purpose:** Abstract the direct interaction with a specific LLM provider's API.
-   **Structure (Conceptual):**
    ```python
    # In src/llm/client.py
    from abc import ABC, abstractmethod
    # from .models import LLMConfig # (if LLMConfig is in src/llm/models.py)
    # from src.host.models import AgentOutputMessage # Or a more generic LLMMessage model

    class BaseLLMClient(ABC):
        def __init__(self, model_name: str, temperature: Optional[float], max_tokens: Optional[int], system_prompt: Optional[str]):
            self.model_name = model_name
            self.temperature = temperature if temperature is not None else 0.7 # Default
            self.max_tokens = max_tokens if max_tokens is not None else 4096 # Default
            self.system_prompt = system_prompt if system_prompt is not None else "You are a helpful assistant." # Default

        @abstractmethod
        async def create_message(
            self,
            messages: List[Dict[str, Any]], # Standardized message format
            tools: Optional[List[Dict[str, Any]]], # Standardized tool format
            system_prompt_override: Optional[str] = None # Allow overriding the default/configured system prompt
        ) -> AgentOutputMessage: # Returns our standardized message model
            pass

    class AnthropicLLMClient(BaseLLMClient):
        def __init__(self, model_name: str, temperature: Optional[float], max_tokens: Optional[int], system_prompt: Optional[str], api_key: str):
            super().__init__(model_name, temperature, max_tokens, system_prompt)
            self.anthropic_sdk_client = AsyncAnthropic(api_key=api_key)

        async def create_message(
            self,
            messages: List[Dict[str, Any]], # Expects list of {'role': ..., 'content': ...}
            tools: Optional[List[Dict[str, Any]]], # Expects Anthropic tool format
            system_prompt_override: Optional[str] = None
        ) -> AgentOutputMessage: # Returns our AgentOutputMessage
            # 1. Determine final system prompt (override or self.system_prompt)
            # 2. Convert input messages and tools to Anthropic's specific format if necessary.
            #    (Our AgentOutputMessage.content might need to be transformed to Anthropic's MessageParam content)
            # 3. Make the call using self.anthropic_sdk_client.messages.create(...)
            # 4. Convert Anthropic's response (anthropic.types.Message)
            #    into our AgentOutputMessage Pydantic model.
            #    This involves mapping fields and serializing content blocks into AgentOutputContentBlock.
            # Example (highly simplified):
            # anthropic_response = await self.anthropic_sdk_client.messages.create(...)
            # return AgentOutputMessage.model_validate(_serialize_content_blocks(anthropic_response)) # Assuming _serialize_content_blocks output matches AgentOutputMessage structure
            pass # Placeholder for actual implementation

    # Factory function or LLMManager to get/create clients based on LLMConfig
    # def get_llm_client(config: LLMConfig) -> BaseLLMClient:
    #     if config.provider == "anthropic":
    #         api_key = os.environ.get("ANTHROPIC_API_KEY") # Or from LLMConfig if designed that way
    #         if not api_key: raise ValueError("Anthropic API key not found")
    #         return AnthropicLLMClient(
    #             model_name=config.model_name,
    #             temperature=config.temperature,
    #             max_tokens=config.max_tokens,
    #             system_prompt=config.default_system_prompt,
    #             api_key=api_key
    #         )
    #     # elif config.provider == "openai": ...
    #     else:
    #         raise NotImplementedError(f"LLM provider {config.provider} not supported.")
    ```

### 4.4. `Agent` Class Modifications for LLM Refactoring

-   **`__init__`**:
    -   Would be responsible for instantiating or obtaining an `LLMClient` instance.
    -   If `AgentConfig.llm_config_id` is set, it would fetch the corresponding `LLMConfig` (perhaps from `HostManager` or a new `LLMConfigRegistry`) and create the client.
    -   The `AgentConfig`'s direct LLM parameters (`model`, `temperature`, etc.) would override those from the fetched `LLMConfig` when initializing the `LLMClient`.
    -   The `self.anthropic_client` would be replaced by `self.llm_client: BaseLLMClient`.
-   **`_make_llm_call` (or its replacement)**:
    -   This method would be significantly simplified or entirely replaced.
    -   It would now delegate the LLM call to `self.llm_client.create_message()`.
    -   It would pass the messages, tools, and the final effective system prompt (agent's config + schema instructions) to the `LLMClient`.
    -   The `LLMClient` would return our standardized `AgentOutputMessage`, so no further complex serialization would be needed here for the direct LLM response.
-   **Schema Injection**: The logic for injecting the `AgentConfig.schema` into the system prompt would remain in the `Agent` class, as it's an agent-specific behavior modifying the prompt before it's sent to the `LLMClient`.

### 4.5. Benefits of LLM Refactoring

-   **Modularity:** Clearly separates agent orchestration (conversation loop, tool handling, history) from direct LLM communication.
-   **Extensibility:** Adding support for new LLM providers (OpenAI, Gemini, local models) becomes a matter of:
    1.  Adding a new `LLMConfig.provider` option.
    2.  Implementing a new `XYZLLMClient` class that conforms to the `BaseLLMClient` interface.
    3.  Updating the factory/manager to instantiate the new client.
-   **Reusability:** `LLMConfig`s can define standard LLM setups (e.g., "fast-creative-claude", "precise-gpt4") that can be reused by multiple `AgentConfig`s.
-   **Simplified `Agent` Class:** The `Agent` class becomes less burdened with LLM provider-specific details.
-   **Support for Non-MCP Agents:** Facilitates creating agents that might only use an LLM without needing MCP tools/prompts/resources, as the `LLMClient` interaction is independent of `MCPHost`.

## 5. Impact and Next Steps

-   **Impact:**
    -   Requires defining new Pydantic models (`AgentExecutionResult`, `LLMConfig`, etc.).
    -   Requires creating the `LLMClient` interface and initial `AnthropicLLMClient` implementation.
    -   Significant changes to `Agent.__init__` and `Agent._make_llm_call` (or its replacement).
    -   `HostManager` might need to be aware of `LLMConfig`s if they are to be centrally managed and referenced by ID.
    -   Configuration files might need updating to include `llm_config_id` in `AgentConfig`s.
    -   All consumers of `Agent.execute_agent()` (including tests and workflows) will need to be updated to handle the new `AgentExecutionResult` Pydantic model instead of a raw dictionary.
-   **Next Steps:**
    1.  Review and refine this design document.
    2.  Prioritize:
        a.  Implement `AgentExecutionResult` and update `Agent.execute_agent()` to return it. (This addresses the immediate need for better output handling).
        b.  Then, proceed with the `LLMConfig` and `LLMClient` refactoring.
    3.  Create detailed implementation plans for each prioritized step.
    4.  Implement the changes iteratively, with testing at each stage.

## 6. Discussion Points

-   Where should `LLMConfig`s be defined and managed? (e.g., in the main JSON config, separate files, loaded by `HostManager`?)
-   How should API keys and other sensitive LLM credentials be handled by `LLMConfig` / `LLMClient`? (Preferably via environment variables or secure secret management, not directly in config files).
-   The exact interface of `BaseLLMClient.create_message()`: what should be its input message format (e.g., list of our `AgentOutputMessage` models, or a simpler list of dicts)? How does it handle tool formatting for different providers?
-   Error handling strategy within `LLMClient` implementations.
