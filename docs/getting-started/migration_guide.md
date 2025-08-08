# Migration Guide

This guide will help you migrate your existing Aurite framework projects to the latest version, which introduces a new project and workspace system, along with several key renames for consistency.

## 1. New Project Structure: The `.aurite` file

The biggest change is the introduction of a project and workspace system. Your project now requires an `.aurite` file in its root directory to be recognized by the framework.

**Action Required:**

In the root directory of your project (the same folder that contains your `config` directory), create a new file named `.aurite` with the following content:

```toml
# .aurite
[aurite]
type = "project"
include_configs = ["config"]
```

- `type = "project"`: Identifies this directory as an Aurite project.
- `include_configs = ["config"]`: Tells Aurite to load all your component configurations from the `config/` directory. If you store configs in other folders, add their relative paths to this list.

For more details on projects and workspaces, see the [Projects and Workspaces documentation](../config/projects_and_workspaces.md).

## 2. Import Paths Simplification

All major components and models can now be imported directly from the top-level `aurite` package. This simplifies imports and makes them more consistent.

**Action Required:**

Update all your imports from the Aurite framework.

**Before:**

```python
from aurite.lib.models.config.components import LLMConfig
from aurite.execution.aurite_engine import Aurite
```

**After:**

```python
from aurite import LLMConfig, Aurite
```

Simply change your imports to pull directly from `aurite`.

## 3. `Aurite` Class Method Renames

Several methods in the `Aurite` class have been renamed for clarity and consistency.

**Action Required:**

Update your code to use the new method names.

| Old Method Name       | New Method Name            | Description                     |
| --------------------- | -------------------------- | ------------------------------- |
| `register_llm_config` | `register_llm`             | Registers an LLM configuration. |
| `register_workflow`   | `register_linear_workflow` | Registers a linear workflow.    |
| `register_client`     | `register_mcp_server`      | Registers an MCP server.        |
| `run_workflow`        | `run_linear_workflow`      | Runs a linear workflow.         |

**Example:**

**Before:**

```python
from aurite import Aurite, LLMConfig

aurite = Aurite()
my_llm = LLMConfig(llm_id="my-llm", model_name="gpt-4")
aurite.register_llm_config(my_llm)
aurite.run_workflow("my-workflow")
```

**After:**

```python
from aurite import Aurite, LLMConfig

aurite = Aurite()
my_llm = LLMConfig(name="my-llm", model="gpt-4") # Note the model changes too!
aurite.register_llm(my_llm)
aurite.run_linear_workflow("my-workflow")
```

## 4. `LLMConfig` Model Field Renames

The fields in the `LLMConfig` model have been updated to align with the naming convention used by all other components.

**Action Required:**

Update your `LLMConfig` instantiations and any configuration files (`.json` or `.yaml`) where you define LLMs.

| Old Field Name | New Field Name | Description                                 |
| -------------- | -------------- | ------------------------------------------- |
| `llm_id`       | `name`         | The unique identifier for the LLM.          |
| `model_name`   | `model`        | The specific model string (e.g., "gpt-4o"). |

**Example (in Python):**

**Before:**

```python
from aurite import LLMConfig

llm_config = LLMConfig(
    llm_id="openai-gpt4",
    model_name="gpt-4-turbo",
    provider="litellm"
)
```

**After:**

```python
from aurite import LLMConfig

llm_config = LLMConfig(
    name="openai-gpt4",
    model="gpt-4-turbo",
    provider="litellm"
)
```

**Example (in `config/llms.json`):**

**Before:**

```json
{
  "llms": [
    {
      "llm_id": "claude-sonnet",
      "model_name": "claude-3-5-sonnet-20240620",
      "provider": "litellm"
    }
  ]
}
```

**After:**

```json
{
  "llms": [
    {
      "name": "claude-sonnet",
      "model": "claude-3-5-sonnet-20240620",
      "provider": "litellm"
    }
  ]
}
```

By following these steps, your project will be up-to-date with the latest version of the Aurite framework.
