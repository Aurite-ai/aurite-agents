# Project Configurations (ProjectConfig)

Project configurations are the central manifest for an Aurite Agents application. Unlike individual components like Agents or LLMs, a Project file doesn't define a single operational unit. Instead, it **organizes and declares all the components** (LLMs, Clients, Agents, Simple Workflows, and Custom Workflows) that will be loaded and made available by the `HostManager` (via `src/aurite/host_manager.py`) at startup.

This document explains the structure of a Project configuration, how components are specified within it, and its overall role in the framework. The `ProjectConfig` model is defined in `src/aurite/config/config_models.py`.

## Purpose of a Project File

A Project file serves several key purposes:

1.  **Centralized Definition**: It provides a single source of truth for all components that constitute a specific agentic application or setup.
2.  **Component Orchestration**: It dictates which LLMs, clients, agents, and workflows are active and available for execution.
3.  **Environment Configuration**: It allows for different sets of components to be easily swapped by changing the active project file (e.g., for development, testing, or production).

## Active Project File

-   By default, the Aurite framework looks for a project file named `aurite_config.json` in the root directory from which the application is run.
-   This path can be overridden using the `PROJECT_CONFIG_PATH` environment variable, allowing you to point to any valid project JSON file within your workspace.

## Specifying Components

Within a project file, each type of component (LLMs, Clients, Agents, etc.) is declared in its respective array (e.g., `"llms": [], "agents": []`). Components can be specified in two ways:

1.  **Inline Definition**: You can define the complete configuration for a component directly within the project file as a JSON object. This is useful for project-specific configurations or when you want all details in one place.
    *Example (inline LLM definition in a project file):*
    ```json
    {
      "name": "MyProject",
      "llms": [
        {
          "llm_id": "project_specific_claude",
          "provider": "anthropic",
          "model_name": "claude-3-sonnet-20240229",
          "temperature": 0.6
        }
      ]
      // ... other components
    }
    ```

2.  **Reference by ID/Name**: You can reference a component by its unique ID (e.g., `llm_id` for LLMs, `client_id` for Clients, `name` for Agents/Workflows). This ID corresponds to a component defined in a separate JSON file located in the `config/<component_type>/` directory (e.g., `config/llms/my_llm.json`, `config/agents/my_agent.json`). The `ComponentManager` loads all such files from these directories (and also from packaged defaults within Aurite) and makes them available for reference. This method promotes reusability and modularity.
    *Example (referencing an LLM defined elsewhere):*
    ```json
    // In config/llms/shared_claude_opus.json:
    // {
    //   "llm_id": "shared_claude_opus",
    //   "provider": "anthropic",
    //   "model_name": "claude-3-opus-20240229"
    // }

    // In your project file (e.g., aurite_config.json):
    {
      "name": "MyProjectWithSharedLLM",
      "llms": [
        "shared_claude_opus" // Reference by llm_id
      ],
      "agents": [
        {
          "name": "AgentUsingSharedLLM",
          "llm_config_id": "shared_claude_opus", // Agent config references the LLM
          "system_prompt": "You are an agent using a shared LLM."
        }
      ]
      // ... other components
    }
    ```

The `ProjectManager` resolves these references or validates inline definitions when loading the project.

## Project Configuration Fields (ProjectConfig)

The `ProjectConfig` model defines the top-level structure of a project JSON file.

| Field                | Type                                  | Default         | Description                                                                                                                               |
| -------------------- | ------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `name`               | string                                | Required        | A unique name for the project.                                                                                                            |
| `description`        | string                                | Optional (`null`) | A brief description of the project's purpose.                                                                                             |
| `clients`            | dictionary of `string` to `ClientConfig` | `{}` (empty dict) | A dictionary where keys are `client_id`s and values are [Client Configurations](./client.md). Can contain inline definitions or references. |
| `llms`               | dictionary of `string` to `LLMConfig`   | `{}` (empty dict) | A dictionary where keys are `llm_id`s and values are [LLM Configurations](./llm.md). Can contain inline definitions or references.         |
| `agents`             | dictionary of `string` to `AgentConfig` | `{}` (empty dict) | A dictionary where keys are agent `name`s and values are [Agent Configurations](./agent.md). Can contain inline definitions or references.   |
| `simple_workflows`   | dictionary of `string` to `WorkflowConfig` | `{}` (empty dict) | A dictionary where keys are workflow `name`s and values are [Simple Workflow Configurations](./simple_workflow.md). Can contain inline definitions or references. |
| `custom_workflows`   | dictionary of `string` to `CustomWorkflowConfig` | `{}` (empty dict) | A dictionary where keys are workflow `name`s and values are [Custom Workflow Configurations](./custom_workflow.md). Can contain inline definitions or references. |

*Note: While the input JSON file uses arrays for component types (e.g., `"llms": []`), the `ProjectManager` processes these into dictionaries keyed by their respective IDs/names within the `ProjectConfig` model.*

## Example Project File Snippet (`aurite_config.json`)

```json
{
  "name": "MySampleProject",
  "description": "A sample project demonstrating component configuration.",
  "llms": [
    {
      "llm_id": "default_opus",
      "provider": "anthropic",
      "model_name": "claude-3-opus-20240229",
      "temperature": 0.7
    },
    "reference_to_haiku_llm" // Assumes "reference_to_haiku_llm" is defined somewhere in config/llms/
  ],
  "clients": [
    {
      "client_id": "local_weather_service",
      "server_path": "mcp_servers/weather.py",
      "capabilities": ["tools"]
    }
  ],
  "agents": [
    {
      "name": "WeatherInquiryAgent",
      "llm_config_id": "default_opus",
      "system_prompt": "You are a weather bot.",
      "client_ids": ["local_weather_service"]
    },
    {
      "name": "Weather Reporter",
      "llm_config_id": "default_opus",
      "system_prompt": "You are a Weather Reporter. You will be provided with a weather forecast for a specific city. Your job is to use this information to provide an informal weather report."
    }
  ],
  "simple_workflows": [
    {
      "name": "BasicWeatherWorkflow",
      "steps": ["WeatherInquiryAgent", "Weather Reporter"]
    }
  ],
  "custom_workflows": ["my_advanced_orchestrator"] // Assumes my_advanced_orchestrator is defined somewhere in config/custom_workflows/
}
```

## Component Documentation Links

For detailed information on configuring each component type, please refer to their respective documents:

-   [LLM Configurations (LLMConfig)](./llm.md)
-   [Client Configurations (ClientConfig)](./client.md)
-   [Agent Configurations (AgentConfig)](./agent.md)
-   [Simple Workflow Configurations (WorkflowConfig)](./simple_workflow.md) (To be created)
-   [Custom Workflow Configurations (CustomWorkflowConfig)](./custom_workflow.md) (To be created)
