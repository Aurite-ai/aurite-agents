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
    | `system_prompt` | `string` | No | The primary system prompt for the agent. This can be overridden by the `system_prompt` in the `llm` block. |

=== ":material-tools: Capability Management"

    These fields control which tools and resources the agent can access.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `mcp_servers` | `list[string]` | `[]` | A list of `mcp_server` component names this agent can use. The agent gains access to all tools, prompts, and resources from these servers. |
    | `exclude_components` | `list[string]` | `None` | A list of component names (tools, prompts, resources) to explicitly exclude, even if provided by allowed `mcp_servers`. |
    | `auto` | `boolean` | `false` | If `true`, an LLM dynamically selects the most appropriate `mcp_servers` at runtime based on the user's prompt. |

=== ":simple-amd: LLM Configuration"

    These fields control the Large Language Model that powers the agent's reasoning.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `llm_config_id` | `string` | `None` | The `name` of an `llm` component to use. This is the recommended way to assign an LLM, allowing for reusable configurations. |
    | `llm` | `object` | `None` | An object containing LLM parameters to override the base `LLMConfig`. See details below. |

    !!! abstract "LLM Overrides"
        The `llm` block allows you to fine-tune the model's behavior for a specific agent. It accepts any field from the [LLM Configuration](llm.md), including:
        - `model` (string): A different model name (e.g., `"gpt-3.5-turbo"`).
        - `temperature` (float): A different sampling temperature.
        - `max_tokens` (integer): A different max token limit.
        - `system_prompt` (string): A more specific system prompt for this agent.
        - `api_base`, `api_key`, `api_version` for custom endpoints.
        - Any other provider-specific parameters.

=== ":material-cogs: Behavior Control"

    These fields fine-tune how the agent executes its tasks.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `max_iterations` | `integer` | `50` | The maximum number of conversational turns before stopping automatically. This is a safeguard to prevent infinite loops. |
    | `include_history` | `boolean` | `None` | If `true`, the entire conversation history is included in each turn. If `false` or `None`, the agent is stateless and only sees the latest message. |

=== ":material-flask: Advanced & Experimental"

    These fields are for advanced use cases like validation and testing.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `config_validation_schema` | `dict` | `None` | A JSON schema for validating agent-specific configurations. |
    | `evaluation` | `string` | `None` | Optional runtime evaluation. Can be a prompt describing expected output or the name of a file in `config/testing`. |

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
      "mcp_servers": [
        "pylint-server",
        "file-system-server"
      ],
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
      "llm": {
        "model": "gpt-4-1106-preview",
        "temperature": 0.9
      }
    }
    ```

=== "Stateless Agent"
This agent is configured to be stateless (`include_history` is `false`), making it suitable for simple, single-turn tasks where context is not needed.

    ```json
    {
      "type": "agent",
      "name": "simple-calculator-agent",
      "description": "A stateless agent that performs a single calculation.",
      "mcp_servers": ["calculator-tool-server"],
      "llm_config_id": "gpt-3.5-turbo",
      "include_history": false
    }
