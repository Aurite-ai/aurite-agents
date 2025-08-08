# :material-robot: Agent Configuration

Agents are the primary actors in the Aurite framework, responsible for executing tasks by interacting with tools and models. The agent configuration defines an agent's identity, its capabilities, and its behavior.

An agent configuration is a JSON or YAML object with a `type` field set to `"agent"`.

!!! tip "Configuration Location"

    Agent configurations can be placed in any directory specified in your project's `.aurite` file (e.g., `config/agents/`, `shared/agents/`). The framework will automatically discover them.

---

## Schema

The `AgentConfig` defines the structure for an agent configuration. Below are the available fields, categorized for clarity.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields define the fundamental properties of the agent.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `name` | `string` | Yes | A unique identifier for the agent. This name is used to reference the agent in workflows and commands. |
    | `description` | `string` | No | A brief, human-readable description of what the agent does. |
    | `llm_config_id` | `string` | `None` | The `name` of an `llm` component to use. This is the recommended way to assign an LLM, allowing for reusable configurations. |
    | `system_prompt` | `string` | No | The primary system prompt for the agent. This can be overridden by the `system_prompt` in the `llm` block. |
    | `mcp_servers` | `list[string]` | `[]` | A list of `mcp_server` component names this agent can use. The agent gains access to all tools, prompts, and resources from these servers. |
    | `config_validation_schema` | `dict` | `None` | A JSON schema for validating agent-specific configurations. |

=== ":material-tools: Tool Management"

    These fields control which tools and resources the agent can access.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `exclude_components` | `list[string]` | `None` | A list of component names (tools, prompts, resources) to explicitly exclude, even if provided by allowed `mcp_servers`. |
    | `auto` | `boolean` | `false` | If `true`, an LLM dynamically selects the most appropriate `mcp_servers` at runtime based on the user's prompt. |

=== ":simple-amd: LLM Overrides"

    These fields control the Large Language Model that powers the agent's reasoning.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `model`          | `string`  | None    | Override the model name (e.g., `"gpt-3.5-turbo"`). |
    | `temperature`    | `float`   | None    | Override the sampling temperature for the agent's LLM. |
    | `max_tokens`     | `integer` | None    | Override the maximum token limit for responses. |
    | `system_prompt`  | `string`  | None    | Provide a more specific system prompt for this agent. |
    | `api_base`       | `string`  | None    | Custom API endpoint base URL for the LLM provider. |
    | `api_key`        | `string`  | None    | Custom API key for the LLM provider. |
    | `api_version`    | `string`  | None    | Custom API version for the LLM provider. |
    | *other fields*   | *various* | None    | Any other provider-specific parameters supported by the [LLM Configuration](llm.md). |

    !!! abstract "LLM Overrides"
        Agent Configurations can include llm variables (See LLM Overrides in the table above). These variables will replace the corresponding values in the LLM Configuration referenced by `llm_config_id`. This allows for agent-specific customization while still using a shared LLM configuration.

=== ":material-cogs: Behavior Control"

    These fields fine-tune how the agent executes its tasks.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `max_iterations` | `integer` | `50` | The maximum number of conversational turns before stopping automatically. This is a safeguard to prevent infinite loops. |
    | `include_history` | `boolean` | `None` | If `true`, the entire conversation history is included in each turn. If `false` or `None`, the agent is stateless and only sees the latest message. |
    | `include_logging` | `boolean` | `None` | If `true`, enables detailed logging to Langfuse for this agent. If `false`, disables it. If `None`, behavior is determined by the parent workflow or the `LANGFUSE_ENABLED` environment variable. |

---

## :material-code-json: Configuration Examples

Here are some practical examples of agent configurations.

=== "Simple Agent"

    A basic agent that uses a centrally-defined LLM and has access to a set of tools.

    ```json
    {
      "type": "agent",
      "name": "code-refactor-agent",
      "description": "An agent that helps refactor Python code by using static analysis tools.",
      "mcp_servers": ["pylint-server", "file-system-server"],
      "llm_config_id": "claude-3-opus",
      "system_prompt": "You are an expert Python programmer. You will be given a file and your goal is to refactor it to improve readability and performance.",
      "max_iterations": 10
    }
    ```

=== "Agent with LLM Overrides"

    This agent uses a base LLM configuration but overrides the model and temperature for its specific task.

    ```json
    {
      "type": "agent",
      "name": "creative-writer-agent",
      "description": "An agent for brainstorming creative ideas.",
      "mcp_servers": ["internet-search-server"],
      "llm_config_id": "gpt-4-base",
      "model": "gpt-4-1106-preview",
      "temperature": 0.9
    }
    ```

=== "Stateful Agent"

    This agent is configured to be stateful (`include_history` is `true`), allowing it to maintain context across multiple turns.

    ```json
    {
      "type": "agent",
      "name": "simple-calculator-agent",
      "description": "A stateless agent that performs a single calculation.",
      "mcp_servers": ["calculator-tool-server"],
      "llm_config_id": "gpt-3.5-turbo",
      "include_history": true
    }
    ```

=== "Agent with Schema"

    This agent includes a custom validation schema to ensure its configuration adheres to specific rules.

    ```json
    {
      "type": "agent",
      "name": "data-validation-agent",
      "description": "An agent that validates data formats.",
      "mcp_servers": ["data-validator-server"],
      "llm_config_id": "gpt-3.5-turbo",
      "config_validation_schema": {
        "type": "object",
        "properties": {
          "input_format": { "type": "string" },
          "output_format": { "type": "string" }
        },
        "required": ["input_format", "output_format"]
      }
    }
    ```

=== "Agent with Logging Disabled"

    This agent explicitly disables Langfuse logging, which can be useful for high-volume or sensitive tasks.

    ```json
    {
      "type": "agent",
      "name": "pii-stripping-agent",
      "description": "An agent that removes personally identifiable information from text.",
      "llm_config_id": "gpt-3.5-turbo",
      "include_logging": false
    }
    ```
