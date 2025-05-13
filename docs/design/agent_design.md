# Agent, Client, and LLM Design Document

## 1. Introduction

This document outlines the current design of the `Agent` class, its configuration (`AgentConfig`), and related components within the Aurite Agents framework. It also proposes a new Pydantic model for standardizing agent execution results and explores a refactoring strategy to introduce a dedicated `LLM` configuration and class for managing Large Language Model interactions.

The goals of this design discussion are to:
- Improve the clarity and maintainability of the `Agent` class.
- Provide a more robust and developer-friendly way to handle agent outputs.
- Enhance the modularity and extensibility of the framework, particularly for supporting different LLM providers and configurations.

## 2. Current State (Post Phase 2 Refactoring)

### 2.1. `AgentConfig` (`src/config/config_models.py`)

-   **Purpose:** Defines the configuration for an individual `Agent` instance. It specifies agent-specific settings, LLM parameters (potentially referencing a shared `LLMConfig`), and its relationship with the MCP Host for accessing tools and resources.
-   **Key Fields:**
    -   `name: Optional[str]`: An optional name for the agent instance.
    -   `client_ids: Optional[List[str]]`: A list of MCP `ClientConfig` IDs that this agent is allowed to use. This filters the tools and resources available to the agent via the `MCPHost`.
    -   `llm_config_id: Optional[str]`: (Optional) ID of an `LLMConfig` to use as a base for LLM settings.
    -   `system_prompt: Optional[str]`: Agent-specific system prompt. Overrides `LLMConfig.default_system_prompt` if `llm_config_id` is also set.
    -   `config_validation_schema: Optional[dict]`: (Renamed from `schema`) A JSON schema used to validate the agent's final text output if provided.
    -   `model: Optional[str]`: Agent-specific LLM model. Overrides `LLMConfig.model_name` if `llm_config_id` is also set.
    -   `temperature: Optional[float]`: Agent-specific temperature. Overrides `LLMConfig.temperature` if `llm_config_id` is also set.
    -   `max_tokens: Optional[int]`: Agent-specific max tokens. Overrides `LLMConfig.max_tokens` if `llm_config_id` is also set.
    -   `max_iterations: Optional[int]`: The maximum number of turns in a conversation loop (LLM call -> tool use -> LLM call) before the agent stops.
    -   `include_history: Optional[bool]`: If `True`, the `ExecutionFacade` attempts to load and save conversation history using a `StorageManager`.
    -   `exclude_components: Optional[List[str]]`: A list of specific component names (tools, prompts, resources) to exclude for this agent, even if provided by its allowed `client_ids`.
    -   `evaluation: Optional[str]`: (Currently used by prompt validation) Specifies an evaluation mechanism.
-   **Usage:** An `AgentConfig` instance is passed to the `Agent` class during its initialization by the `ExecutionFacade`. The `ExecutionFacade` resolves the appropriate `LLMClient` and potentially an `LLMConfig` (for overrides) based on the `AgentConfig`.

### 2.2. `Agent` Class (`src/agents/agent.py`)

-   **Purpose:** The `Agent` class orchestrates the multi-turn conversation flow for an agent, managing the message history, loop iterations, and interactions with the `AgentTurnProcessor`. It receives an initialized LLM client and configuration. (This class now incorporates the logic previously in `ConversationManager`).
-   **Initialization (`__init__`)**:
    -   Takes `config: AgentConfig`, `llm_client: BaseLLM`, `host_instance: MCPHost`, `initial_messages: List[MessageParam]`, `system_prompt_override: Optional[str]`, and `llm_config_for_override: Optional[LLMConfig]`.
    -   Stores these parameters. It does **not** initialize the LLM client itself; that is handled by the `ExecutionFacade`.
-   **Key External Method (`run_conversation`)**:
    -   **Inputs:** None (uses initialized state).
    -   **Outputs:** Returns an `AgentExecutionResult` Pydantic model instance.
    -   **Core Logic:**
        1.  Determines the effective system prompt for the conversation (using `system_prompt_override` or `self.config.system_prompt`).
        2.  Retrieves formatted tool definitions from the `host_instance` using `host_instance.get_formatted_tools(agent_config=self.config)`.
        3.  Enters a conversation loop (up to `self.config.max_iterations`):
            a.  Instantiates `AgentTurnProcessor`, passing the current state (`config`, `llm_client`, `host_instance`, current `messages`, `tools_data`, `effective_system_prompt`, `llm_config_for_override`).
            b.  Calls `await turn_processor.process_turn()` to execute one turn (LLM call, optional tool execution).
            c.  Receives the results from the turn processor: `turn_final_response`, `turn_tool_results_params`, `is_final_turn`.
            d.  Updates the internal message list (`self.messages`) for the *next* LLM call by appending the assistant's response (from `turn_processor.get_last_llm_response()`) and any tool results (`turn_tool_results_params`).
            e.  Updates the full conversation log (`self.conversation_history`) with the assistant's response and tool results (as dictionaries).
            f.  Checks `is_final_turn`. If `True`, stores `turn_final_response` as the final result and breaks the loop.
            g.  If `is_final_turn` is `False` and no tool results were returned (indicating a schema validation failure signaled by the turn processor), appends a correction message to `self.messages` and `self.conversation_history` and continues the loop.
        4.  Handles the case where `max_iterations` is reached.
        5.  Calls `_prepare_agent_result` to construct and validate the final `AgentExecutionResult` object.
-   **Key Internal Method (`_prepare_agent_result`)**:
    -   Constructs the `AgentExecutionResult` Pydantic model from the final state (`self.conversation_history`, `self.final_response`, `self.tool_uses_in_last_turn`, `execution_error`).
    -   Handles validation and potential fallback creation if validation fails.
-   **Dependencies:** `AgentConfig`, `LLMConfig`, `BaseLLM`, `MCPHost`, `AgentTurnProcessor`, `AgentExecutionResult`, `AgentOutputMessage`, `MessageParam`.

### 2.3. `AgentTurnProcessor` Class (`src/agents/agent_turn_processor.py`)

-   **Purpose:** Handles the logic for a *single turn* within the agent's loop, including the LLM call, response parsing, schema validation, and tool execution coordination.
-   **Initialization (`__init__`)**: Takes `config`, `llm_client`, `host_instance`, `current_messages`, `tools_data`, `effective_system_prompt`, and `llm_config_for_override`.
-   **Key Method (`process_turn`)**:
    -   Makes the LLM call via `self.llm.create_message()`, passing `llm_config_override`.
    -   Parses the `AgentOutputMessage` response.
    -   If `stop_reason` is `tool_use`, calls `_process_tool_calls` to execute tools via `self.host.execute_tool()` and prepares tool result messages (`List[MessageParam]`). Returns `(None, tool_results, False)`.
    -   If `stop_reason` is not `tool_use`, calls `_handle_final_response`.
        -   `_handle_final_response` performs schema validation if `self.config.config_validation_schema` is set.
        -   If validation passes (or no schema), returns the original LLM response. `process_turn` returns `(validated_response, None, True)`.
        -   If validation fails, returns `None`. `process_turn` returns `(None, None, False)` to signal a correction is needed.
-   **Dependencies:** `AgentConfig`, `LLMConfig`, `BaseLLM`, `MCPHost`, `AgentOutputMessage`, `MessageParam`, `jsonschema`.

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
# Example LLMConfig (Reflects current model in src/config/config_models.py)
class LLMConfig(BaseModel):
    llm_id: str = Field(description="Unique identifier for this LLM configuration.")
    provider: str = Field(default="anthropic", description="The LLM provider (e.g., 'anthropic', 'openai', 'gemini').")
    model_name: Optional[str] = Field(None, description="The specific model name for the provider.") # Now optional

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

### 4.3. `BaseLLM` and Provider Clients (e.g., `src/llm/base_client.py`, `src/llm/providers/anthropic_client.py`)

-   **Purpose:** Abstract the direct interaction with a specific LLM provider's API.
-   **Current Implementation:**
    -   `BaseLLM` defines the abstract interface (`__init__`, `create_message`).
    -   `AnthropicLLM` implements `BaseLLM`.
    -   `create_message` now accepts an optional `llm_config_override: Optional[LLMConfig]` parameter.
    -   If `llm_config_override` is provided, its values (model, temp, tokens, prompt) take precedence over the client's instance defaults for that specific API call.
    -   The client handles converting the provider's response into the standardized `AgentOutputMessage`.
-   **Structure (Current):**
    ```python
    # In src/llm/base_client.py
    from abc import ABC, abstractmethod
    from src.config.config_models import LLMConfig
    from src.agents.agent_models import AgentOutputMessage

    class BaseLLM(ABC):
        def __init__(self, model_name: str, temperature: Optional[float], max_tokens: Optional[int], system_prompt: Optional[str]):
            # ... initialization with defaults ...

        @abstractmethod
        async def create_message(
            self,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]],
            system_prompt_override: Optional[str] = None,
            schema: Optional[Dict[str, Any]] = None,
            llm_config_override: Optional[LLMConfig] = None, # Added
        ) -> AgentOutputMessage:
            pass

    # In src/llm/providers/anthropic_client.py
    from ..base_client import BaseLLM
    from ...config.config_models import LLMConfig
    from ...agents.agent_models import AgentOutputMessage

    class AnthropicLLM(BaseLLM):
        # ... __init__ ...

        async def create_message(
            self,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]],
            system_prompt_override: Optional[str] = None,
            schema: Optional[Dict[str, Any]] = None,
            llm_config_override: Optional[LLMConfig] = None, # Added
        ) -> AgentOutputMessage:
            # 1. Resolve effective model, temp, tokens, system_prompt using llm_config_override and instance defaults.
            # 2. Inject schema into resolved system_prompt if needed.
            # 3. Make the call using self.anthropic_sdk_client.messages.create(...) with resolved parameters.
            # 4. Convert Anthropic's response into our AgentOutputMessage.
            pass # Placeholder for actual implementation details shown in the file
    ```
-   **LLM Client Instantiation:** Currently handled by `ExecutionFacade.run_agent`, which resolves parameters from `AgentConfig` and `LLMConfig` before creating the `AnthropicLLM` instance. A dedicated factory function or manager (`get_llm_client`) is still a potential future improvement.
    ```python
    # Example Factory (Conceptual - Not yet implemented)
    # def get_llm_client(config: LLMConfig) -> BaseLLM:
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

-   **Impact (of Phase 2 changes):**
    -   `ConversationManager` class removed and logic merged into `Agent`.
    -   `Agent` class signature and responsibilities changed significantly.
    -   `AgentTurnProcessor` introduced to handle single-turn logic.
    -   `BaseLLM` and `AnthropicLLM` updated to support `llm_config_override`.
    -   `ExecutionFacade` updated to instantiate the new `Agent` class and handle `LLMConfig` resolution for overrides.
    -   Consumers of agent execution (like `SimpleWorkflowExecutor`) now interact via `ExecutionFacade.run_agent` which returns a dictionary representation of `AgentExecutionResult`.
    -   Tests updated for `Agent`, `AnthropicLLM`, and `ExecutionFacade` interactions.
-   **Next Steps (Post Phase 2):**
    1.  Proceed with Phase 3: Advanced Configuration Features & Client Lifecycle Management.
    2.  Consider further LLM refactoring (e.g., dedicated `LLMManager`, support for more providers) as outlined in Section 4.
    3.  Refine error handling and reporting throughout the agent execution flow.

## 6. Discussion Points

-   Where should `LLMConfig`s be defined and managed? (e.g., in the main JSON config, separate files, loaded by `HostManager`?)
-   How should API keys and other sensitive LLM credentials be handled by `LLMConfig` / `LLMClient`? (Preferably via environment variables or secure secret management, not directly in config files).
-   The exact interface of `BaseLLMClient.create_message()`: what should be its input message format (e.g., list of our `AgentOutputMessage` models, or a simpler list of dicts)? How does it handle tool formatting for different providers?
-   Error handling strategy within `LLMClient` implementations.
