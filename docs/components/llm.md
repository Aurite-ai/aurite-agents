# LLM Configurations (LLMConfig)

LLM Configurations define the settings for different Large Language Models (LLMs) that your agents can use. Each configuration specifies the provider, model, and various parameters like temperature and maximum tokens. Agents reference these configurations by their unique `llm_id`.

This document first provides a quickstart example and then details all available fields in an `LLMConfig` object, as defined in `src/aurite/config/config_models.py`.

## Quickstart Example

A minimal LLM configuration requires an `llm_id` and typically a `provider` and `model_name`. Other common parameters like `temperature` and `max_tokens` are often useful.

```json
{
  "llm_id": "my_default_claude_haiku",
  "provider": "anthropic",
  "model_name": "claude-3-haiku-20240307",
  "temperature": 0.7,
  "max_tokens": 2000,
  "default_system_prompt": "You are a concise and helpful AI assistant."
}
```

-   **`llm_id`**: A unique name for this LLM setup.
-   **`provider`**: Specifies the LLM provider (e.g., `"anthropic"`, `"openai"`).
-   **`model_name`**: The specific model from the provider.
-   **`temperature`, `max_tokens`, `default_system_prompt`**: Common operational parameters.

Many fields are optional and have defaults or can be overridden at the agent level.

## Detailed Configuration Fields

An LLM configuration is a JSON object with the following fields:

| Field                   | Type   | Default     | Description                                                                                                                                                                                                                            |
| ----------------------- | ------ | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `llm_id`                | string | Required    | A unique identifier for this specific LLM configuration. Agents will use this ID to select which LLM settings to use.                                                                                                                  |
| `provider`              | string | `"anthropic"` | The LLM provider. Examples: `"anthropic"`, `"openai"`, `"gemini"`. This determines how the framework interacts with the LLM service.                                                                                                    |
| `model_name`            | string | `null`      | The specific model name offered by the provider (e.g., `"claude-3-opus-20240229"`, `"gpt-4-turbo"`). If not provided, the LLM client might use a default model or require it to be set in the `AgentConfig`.                               |
| `temperature`           | number | `null`      | The sampling temperature to use for generating responses. Higher values (e.g., 0.8) make output more random, while lower values (e.g., 0.2) make it more deterministic. If `null`, the LLM client's default or the provider's default will be used. |
| `max_tokens`            | integer| `null`      | The maximum number of tokens to generate in a single response. If `null`, the LLM client's default or the provider's default will be used.                                                                                               |
| `default_system_prompt` | string | `null`      | A default system prompt that will be used for this LLM configuration if an agent using it doesn't specify its own `system_prompt`.                                                                                                      |
| `class Config: extra = "allow"` | N/A    | N/A         | This internal Pydantic setting allows for additional, provider-specific fields to be included in the configuration without causing validation errors. For example, you might add custom parameters required by a specific LLM provider. |

**Note on API Keys and Credentials:**
API keys (e.g., `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) are typically managed through environment variables. The framework's LLM clients (e.g., `AnthropicLLM`) will look for these standard environment variables. While the `LLMConfig` model has commented-out placeholders for `api_key_env_var` or `credentials_path`, the current primary mechanism relies on standard environment variables for API keys.

## Example LLMConfig

LLM configurations are usually stored in a JSON file (e.g., `config/llms/default_llms.json` or a custom file referenced in your project configuration). This file typically contains a list of `LLMConfig` objects.

```json
[
  {
    "llm_id": "anthropic_claude_3_opus",
    "provider": "anthropic",
    "model_name": "claude-3-opus-20240229",
    "temperature": 0.7,
    "max_tokens": 4096,
    "default_system_prompt": "You are a highly capable AI assistant."
  },
  {
    "llm_id": "anthropic_claude_3_haiku_creative",
    "provider": "anthropic",
    "model_name": "claude-3-haiku-20240307",
    "temperature": 0.9,
    "max_tokens": 2048,
    "default_system_prompt": "You are a creative AI assistant, ready to brainstorm."
  },
  {
    "llm_id": "openai_gpt_4_turbo",
    "provider": "openai",
    "model_name": "gpt-4-turbo-preview",
    "temperature": 0.5,
    "max_tokens": 4000
  }
]
```

## How Agents Use LLMConfig

An `AgentConfig` specifies which `LLMConfig` to use via its `llm_config_id` field. This allows for centralized management of LLM settings and easy switching between different models or providers for various agents.

```json
// Example snippet from an AgentConfig
{
  "name": "MyResearchAgent",
  "llm_config_id": "anthropic_claude_3_opus", // References the LLMConfig above
  "system_prompt": "You are a meticulous research assistant."
  // ... other agent settings
}
```

If an `AgentConfig` also defines parameters like `model`, `temperature`, or `max_tokens`, those values will override the ones specified in the `LLMConfig` for that specific agent. The `system_prompt` in `AgentConfig` always takes precedence over `default_system_prompt` in `LLMConfig`.
