# :simple-amd: LLM Configuration

LLM (Large Language Model) configurations are reusable components that define the settings for a specific model from a particular provider. By defining LLMs centrally, you can easily share them across multiple agents and manage your model settings in one place.

An LLM configuration is a JSON or YAML object with a `type` field set to `"llm"`.

!!! tip "Configuration Location"

    LLM configurations can be placed in any directory specified in your project's `.aurite` file (e.g., `config/`, `shared/llms/`). The framework will automatically discover them.

---

## Schema

The `LLMConfig` defines the structure for an LLM configuration. Below are the available fields, categorized for clarity.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields are essential for defining the identity and source of the model.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `name` | `string` | Yes | A unique identifier for the LLM configuration. This name is used in an agent's `llm_config_id` field to link to this configuration. |
    | `provider` | `string` | Yes | The name of the LLM provider, corresponding to a provider supported by the underlying model library (e.g., LiteLLM). Common values include `openai`, `anthropic`, `gemini`, `groq`. |
    | `model` | `string` | Yes | The specific model name as recognized by the provider (e.g., `gpt-4-1106-preview`). |
    | `description` | `string` | No | A brief, human-readable description of the LLM configuration. |

=== ":material-tune: Common Parameters"

    These are standard LLM parameters that can be set as defaults for this configuration. Agents can override these values.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `temperature` | `float` | `None` | The sampling temperature to use (0-2). Higher values (e.g., 0.8) make output more random; lower values (e.g., 0.2) make it more deterministic. |
    | `max_tokens` | `integer` | `None` | The maximum number of tokens to generate in the completion. |
    | `default_system_prompt` | `string` | `None` | A default system prompt for this LLM. An agent's `system_prompt` will override this value. |

=== ":material-api: Provider-Specific Fields"

    These fields are used for connecting to specific APIs, especially for self-hosted or non-standard endpoints.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `api_base` | `string` | `None` | The base URL for the API endpoint. Commonly used for local models (e.g., `http://localhost:8000/v1`) or custom provider endpoints. |
    | `api_key_env_var` | `string` | `None` | The environment variable name for the API key if not using a default (e.g., `ANTHROPIC_API_KEY`). |
    | `api_version` | `string` | `None` | The API version string required by some providers (e.g., Azure OpenAI). |

    !!! info "Dynamic Fields"
        The `LLMConfig` allows for extra, provider-specific fields not explicitly defined in the schema. Any additional key-value pairs will be passed directly to the underlying model library.

---

## :material-file-replace-outline: Agent Overrides

While `LLMConfig` provides a central place for model settings, individual agents can override them at runtime using the `llm` block in their configuration. This provides flexibility for agent-specific needs.

The `LLMConfigOverrides` schema allows an agent to specify its own values for:

- `model`
- `temperature`
- `max_tokens`
- `system_prompt`
- `api_base`
- `api_key`
- `api_version`

!!! example "See the [Agent Configuration](agent.md) documentation for more details on how to apply these overrides."

---

## :material-code-json: Configuration Examples

Here are some practical examples of LLM configurations for different providers.

=== "OpenAI"

    ```json
    {
      "type": "llm",
      "name": "gpt-4-turbo",
      "description": "Configuration for OpenAI's GPT-4 Turbo model.",
      "provider": "openai",
      "model": "gpt-4-1106-preview",
      "temperature": 0.5,
      "max_tokens": 4096
    }
    ```

=== "Anthropic"

    ```json
    {
      "type": "llm",
      "name": "claude-3-sonnet",
      "description": "Configuration for Anthropic's Claude 3 Sonnet model.",
      "provider": "anthropic",
      "model": "claude-3-sonnet-20240229",
      "temperature": 0.7,
      "default_system_prompt": "You are a helpful and friendly assistant."
    }
    ```

=== "Local (Ollama)"

    This example configures a local Llama 3 model served by Ollama.

    ```json
    {
      "type": "llm",
      "name": "local-llama3",
      "description": "Configuration for a local Llama 3 model served by Ollama.",
      "provider": "ollama",
      "model": "llama3",
      "api_base": "http://localhost:11434",
      "temperature": 0.7
    }

    ```
