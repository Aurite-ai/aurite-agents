# Agent Configuration

Agents are the primary actors in the Aurite framework. The `agent.md` configuration file defines an agent's identity, its capabilities, and its behavior. This document details all the available fields for configuring an agent.

An agent configuration is a JSON or YAML object with a `type` field set to `"agent"`.

## Full Example

Here is an example of a complete agent configuration:

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
  "max_iterations": 10
}
```

## Core Fields

These fields define the fundamental properties of the agent.

### `name`
**Type:** `string` (Required)

**Description:** A unique identifier for the agent. This name is used to reference the agent in workflows and commands.

```json
  "name": "customer-support-agent"
```


### `type`
**Type:** `string` (Required)

**Description:** You must specify the component type as `agent`
```json
  "type": "agent"
```


### `system_prompt`
**Type:** `string` (Optional)

**Description:** The system prompt for the agent.

```json
  "system_prompt": "You are a..."
```




## Capability & Server Management

These fields control which tools and resources the agent can access.

### `mcp_servers`
**Type:** `list[string]` (Optional)
**Default:** `[]` (empty list)

**Description:** A list of `mcp_server` component names that this agent is allowed to use. The agent will have access to all tools, prompts, and resources provided by the specified servers.

```json
  "mcp_servers": ["knowledge-base-server", "ticket-system-server"]
```

### `exclude_components`
**Type:** `list[string]` (Optional)

**Description:** A list of specific component names (tools, prompts, or resources) to explicitly exclude from this agent's capabilities, even if they are provided by one of its allowed `mcp_servers`. This is useful for creating a more restricted or specialized version of an agent without needing to redefine the underlying servers.

```json
  "exclude_components": ["delete_ticket_tool"]
```


## LLM Configuration

These fields control the Large Language Model that powers the agent's reasoning and decision-making.

### `llm_config_id`
**Type:** `string` (Optional)

**Description:** The `name` of an `llm` component configuration to use for this agent. This is the recommended way to assign an LLM to an agent, as it allows you to reuse and manage LLM configurations centrally.

```json
  "llm_config_id": "gpt-4-turbo"
```

### llm override parameters

(Optional)

**Description:** LLM parameters that will override the settings from the `llm` component specified by `llm_config_id`. This allows for fine-tuning the LLM's behavior for a specific agent.

You can override the following fields:
-   `model` (string): A different model name (e.g., `"gpt-3.5-turbo"`).
-   `temperature` (float): A different sampling temperature.
-   `max_tokens` (integer): A different max token limit.

```json
    "model": "gpt-3.5-turbo",
    "max_tokens": 2048,
    "temperature": 0.5,
```


## Behavior Control

These fields fine-tune how the agent executes its tasks.

### `max_iterations`
**Type:** `integer` (Optional)
```json
  "max_iterations": 10
```
**Description:** The maximum number of conversational turns (user message -> agent response) the agent will execute before stopping automatically. This is a safeguard to prevent infinite loops.

### `include_history`
**Type:** `boolean` (Optional)

**Description:** If set to `true`, the entire conversation history is included. By default, the agent will only consider the most recent user message in each turn, effectively making it stateless.

```json
  "include_history": "true"
```

## Other Features

### `description`
**Type:** `string` (Optional)

**Description:** A brief, human-readable description of what the agent does.

```json
  "description": "An agent that answers customer questions using a knowledge base."
```

### `auto`
**Type:** `boolean` (Optional)
**Default:** `false`

**Description:** If set to `true`, the framework will use an LLM to dynamically select the most appropriate `mcp_servers` for the agent at runtime based on the user's prompt. This is an advanced feature that allows for more flexible and intelligent tool selection.

```json
  "auto": true
```