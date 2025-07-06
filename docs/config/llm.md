# LLM Configuration

LLM (Large Language Model) configurations are reusable components that define the settings for a specific model from a specific provider. By defining LLMs centrally, you can easily share them across multiple agents and manage your model settings in one place.

An LLM configuration is a JSON or YAML object with a `type` field set to `"llm"`.

## Core Fields

### `name`
**Type:** `string` (Required)
**Description:** A unique identifier for the LLM configuration. This name is used in an agent's `llm_config_id` field to link to this configuration.

```json
{
  "name": "Standard GPT4"
}
```

### `provider`
**Type:** `string` (Required)
**Description:** The name of the LLM provider. This typically corresponds to a provider supported by the underlying model library (e.g., LiteLLM). Common values include `openai`, `anthropic`, `gemini`, `groq`, etc.

```json
{
  "provider": "openai"
}
```

### `model`
**Type:** `string` (Required)
**Description:** The specific model name as recognized by the provider.

```json
{
  "model": "gpt-4-1106-preview"
}
```

### `description`
**Type:** `string` (Optional)
**Description:** A brief, human-readable description of the LLM configuration.

```json
{
  "description": "Standard configuration for OpenAI's GPT-4 model with default settings."
}
```

## Common Parameters

These are standard LLM parameters that can be set as defaults for this configuration. Agents can override these values.

### `temperature`
**Type:** `float` (Optional)
**Description:** The sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.

### `max_tokens`
**Type:** `integer` (Optional)
**Description:** The maximum number of tokens to generate in the completion.

### `default_system_prompt`
**Type:** `string` (Optional)
**Description:** A default system prompt to be used with this LLM. An agent's `system_prompt` will override this value.

## Provider-Specific Fields

These fields are used for connecting to specific APIs, especially for self-hosted or non-standard endpoints.

### `api_base`
**Type:** `string` (Optional)
**Description:** The base URL for the API endpoint. This is commonly used for local models (e.g., `http://localhost:8000/v1`) or custom provider endpoints.

### `api_key`
**Type:** `string` (Optional)
**Description:** The API key for the provider. It is **highly recommended** to manage API keys using environment variables instead of placing them directly in configuration files. However, this field is available for convenience or specific use cases.

### `api_version`
**Type:** `string` (Optional)
**Description:** The API version string required by some providers (e.g., Azure OpenAI).

## Full Example

Here is an example of a complete LLM configuration for a local model served via Ollama:

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
