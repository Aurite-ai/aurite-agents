# Agents & Agent Configurations (AgentConfig)

Agent Configurations define the behavior, capabilities, and LLM settings for individual AI agents within the Aurite framework. Each agent can be tailored with specific system prompts, access to different MCP clients (tools), and LLM operational parameters.

This document first provides a quickstart example and then details all available fields in an `AgentConfig` object, as defined in `src/aurite/config/config_models.py`.

## Quickstart Example

A basic agent needs a name, an `llm_config_id` to specify which LLM to use, and a `system_prompt`. If the agent needs to use tools, you'll also include `mcp_servers`.

```json
{
  "name": "HelpfulGreeterAgent",
  "llm_config_id": "my_default_claude_haiku", // Assumes an LLMConfig with this ID exists
  "system_prompt": "You are a friendly assistant that greets users and offers help.",
  "mcp_servers": ["optional_tool_server_id"] // Only if tools are needed
}
```

-   **`name`**: A unique name for your agent.
-   **`llm_config_id`**: Points to a pre-defined `LLMConfig`.
-   **`system_prompt`**: The primary instruction for the agent's behavior.
-   **`mcp_servers`** (optional): A list of MCP Server names if the agent needs to use tools from them.

Many other fields are available for more advanced control over LLM parameters, tool access, and conversation flow.

## Detailed Configuration Fields

An Agent configuration is a JSON object with the following fields:

| Field                      | Type                 | Default | Description                                                                                                                                                                                             |
| -------------------------- | -------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                     | string               | `null`  | An optional, human-readable name for this agent instance. Useful for identification in logs and when referencing agents in workflows.                                                                 |
| `mcp_servers`              | array of string      | `null`  | A list of MCP Server names. These names must correspond to `name`s defined in MCP Server configuration objects. This list specifies which MCP servers (and thus their tools/resources) this agent is allowed to use. **Note:** You can reference any of the built-in, packaged servers by name here without needing a project file. For backward compatibility, `client_ids` is also supported. |
| `auto`                     | boolean              | `false` | If `true`, the framework (potentially guided by an LLM) will dynamically select a subset of the `mcp_servers` (and their tools) best suited for the current task or user message during a conversation turn. The `routing_weight` in the MCP Server config can influence this selection. If `false`, the agent considers all tools from all `mcp_servers` it has access to (subject to `exclude_components`). |
| `llm_config_id`            | string               | `null`  | The `llm_id` of an `LLMConfig` to use for this agent. This determines the base LLM provider, model, and default parameters.                                                                                |
| `system_prompt`            | string               | `null`  | A specific system prompt for this agent. This overrides the `default_system_prompt` from the referenced `LLMConfig`. If `null`, the `default_system_prompt` from `LLMConfig` is used.                      |
| `config_validation_schema` | object (JSON Schema) | `null`  | An optional JSON schema. If provided, the agent's final text response (if it's expected to be JSON) will be validated against this schema. If validation fails, the agent may be prompted to correct its response. |
| `llm`                      | object (LLMConfig)   | `null`  | An inline `LLMConfig` object. Any fields set here (`model`, `temperature`, `max_tokens`, etc.) will override the settings from the base `LLMConfig` specified by `llm_config_id`. This is the preferred way to specify agent-specific LLM settings. |
| `max_iterations`           | integer              | `null`  | The maximum number of conversation turns (LLM calls and tool executions) the agent will perform before stopping. If `null`, a default (e.g., 10) is used.                                                 |
| `include_history`          | boolean              | `null`  | If `true`, the entire conversation history is provided to the LLM on each turn. If `false`, only the most recent user message (and potentially tool results) might be sent. Behavior can depend on LLM client implementation. If `null`, defaults to`false`. |
| `exclude_components`       | array of string      | `null`  | A list of specific component names (tools, prompts, or resources) that this agent should NOT be able to use, even if they are provided by the servers listed in `mcp_servers`. This allows for fine-grained control over an agent's capabilities. |
| `evaluation`               | string               | `null`  | Experimental: An optional field for runtime evaluation. Can be the name of a test configuration file (e.g., in `config/testing/`) or a simple prompt describing the expected output for basic evaluation.   |

## Key Features and Usage

### LLM Configuration and Overrides

-   Agents select their primary LLM settings (provider, base model, default temperature, etc.) by referencing an `LLMConfig` via `llm_config_id`.
-   An agent's `LLMConfig` is resolved in two steps:
    1.  The base configuration is loaded via `llm_config_id`.
    2.  Any parameters defined in the agent's own `llm` object are used to override the base configuration.
-   This allows for defining a few base LLM configurations (e.g., for different providers) and then fine-tuning specific agents by providing an inline `llm` object with just the parameters you want to change (e.g., a different `system_prompt`, a higher `temperature`, etc.).

### MCP Server and Tool Access

-   **`mcp_servers`**: Defines the pool of MCP servers (and their associated tools/resources) that an agent can access.
-   **`auto` mode**:
    -   When `auto` is `true`, the agent enters a dynamic tool selection mode. In this mode, for each turn, an LLM (or a dedicated routing mechanism) analyzes the current conversation and task, then selects the most relevant subset of tools from the agent's allowed `mcp_servers`. This allows the agent to adapt its available tools based on context, rather than always having all tools from all permitted servers presented to the main LLM. The `routing_weight` in the MCP Server config can influence this selection process.
    -   When `auto` is `false` (the default), the agent's main LLM is presented with all tools from all servers listed in `mcp_servers` (unless filtered by `exclude_components`).
-   **`exclude_components`**: Provides a way to explicitly deny an agent access to certain tools, prompts, or resources, even if those components are offered by a server in its `mcp_servers` list.

### Conversation Flow

-   **`max_iterations`**: Controls how many back-and-forth turns (LLM thinking, tool use, LLM processing tool results) an agent can take.
-   **`include_history`**: Determines if the LLM receives the full conversation history or a more limited context.

### Response Validation

-   **`config_validation_schema`**: If an agent is expected to produce structured JSON output, providing a JSON schema here enables automatic validation of its text responses. If validation fails, the agent can be internally reprompted to correct its output.

## Agent Execution and Results

When an agent is run via the `ExecutionFacade`, it returns a structured `AgentRunResult` object. This object provides detailed information about the outcome of the conversation.

| `AgentRunResult` Field    | Type                               | Description                                                                                                                                  |
| ------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `status`                  | string                             | The final status of the run. Can be `"success"`, `"error"`, or `"max_iterations_reached"`.                                                     |
| `final_response`          | `ChatCompletionMessage` or `null`  | The final message from the assistant if the run was successful. This is an `openai` Pydantic model.                                            |
| `conversation_history`    | list of dict                       | The complete conversation history, with each message represented as a dictionary conforming to the `openai` message format.                      |
| `error_message`           | string or `null`                   | A detailed error message if the `status` is `"error"`.                                                                                       |
| `tool_uses_in_last_turn`  | list of `ToolCall` or `null`       | A list of the tools the agent used in its final turn before responding.                                                                      |

### Handling the Result

```python
# Example of how to run an agent and handle the result
# This code would typically be in a custom workflow or API endpoint.

from aurite.execution.facade import ExecutionFacade
from aurite.components.agents.agent_models import AgentRunResult

async def run_my_agent(facade: ExecutionFacade):
    result: AgentRunResult = await facade.run_agent(
        agent_id="MyAgentName",
        initial_message="What is the weather in Boston?"
    )

    if result.status == "success" and result.final_response:
        print(f"Agent finished successfully!")
        print(f"Final Response: {result.final_response.content}")
    elif result.status == "error":
        print(f"Agent encountered an error: {result.error_message}")
    elif result.status == "max_iterations_reached":
        print("Agent stopped after reaching max iterations.")

    # You can always inspect the full history
    print("\n--- Conversation History ---")
    for message in result.conversation_history:
        print(f"- Role: {message.get('role')}, Content: {message.get('content')}")

```

## Example AgentConfig

Agent configurations are typically stored in JSON files (e.g., `config/agents/my_agent.json`) and referenced by name in the main project configuration or by workflows.

```json
{
  "name": "SmartTaskAutomatorAgent",
  "llm_config_id": "anthropic_claude_3_opus",
  "mcp_servers": ["email_client", "calendar_client", "database_client", "file_system_client"],
  "auto": true,
  "include_history": true,
  "exclude_components": ["database_admin_tool"],
  "llm": {
    "system_prompt": "You are an intelligent assistant that automates tasks by selecting and using the best tools for the job. Analyze the user's request and the available tools to achieve the goal.",
    "temperature": 0.6,
    "max_iterations": 8
  }
}
```

```json
{
  "name": "JsonOutputAgent",
  "llm_config_id": "openai_gpt_4_turbo",
  "mcp_servers": [], // No external tools needed for this example
  "auto": false,
  "system_prompt": "Provide your answer as a JSON object adhering to the specified schema.",
  "config_validation_schema": {
    "type": "object",
    "properties": {
      "summary": { "type": "string" },
      "action_items": {
        "type": "array",
        "items": { "type": "string" }
      },
      "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
    },
    "required": ["summary", "action_items"]
  },
  "max_tokens": 1000
}
```
