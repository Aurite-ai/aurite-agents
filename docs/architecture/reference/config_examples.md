# Configuration Examples Reference

This document contains comprehensive configuration examples and patterns referenced by the architecture documentation.

> 📋 **Configuration Schema Reference**: All configuration examples in this document are based on the Pydantic models defined in `src/aurite/lib/models/config/components.py`. Refer to this file for the complete schema definitions, validation rules, and field descriptions.

## Component Configuration Examples

=== "Agents"

    **Basic Agent Configuration**:
    ```json title="config/agents/agents.json"
    [
      {
        "name": "weather_agent",
        "type": "agent",
        "llm_config_id": "gpt4",
        "system_prompt": "You are a weather assistant with access to real-time weather data.",
        "mcp_servers": ["weather_server", "location_server"],
        "include_history": true,
        "max_iterations": 50,
        "description": "Weather information and forecasting agent"
      },
      {
        "name": "data_analyst",
        "type": "agent",
        "llm_config_id": "claude_sonnet",
        "system_prompt": "You are a data analyst specializing in business intelligence.",
        "mcp_servers": ["database_server", "visualization_server"],
        "include_history": false,
        "max_iterations": 30,
        "description": "Business data analysis and reporting agent"
      }
    ]
    ```

    **Advanced Agent Configuration**:
    ```json title="config/agents/advanced_agents.json"
    [
      {
        "name": "customer_support",
        "type": "agent",
        "llm_config_id": "gpt4",
        "system_prompt": "You are a helpful customer support agent. Be polite and professional.",
        "mcp_servers": ["ticket_system", "knowledge_base"],
        "include_history": true,
        "max_iterations": 25,
        "exclude_components": ["admin_tools", "sensitive_data"],
        "description": "Customer support and ticket management agent"
      },
      {
        "name": "auto_agent",
        "type": "agent",
        "llm_config_id": "claude_sonnet",
        "system_prompt": "You are an intelligent agent that can dynamically select tools.",
        "auto": true,
        "max_iterations": 40,
        "description": "Agent with automatic MCP server selection"
      }
    ]
    ```

    **Agent with LLM Overrides**:
    ```json title="config/agents/specialized_agents.json"
    [
      {
        "name": "creative_writer",
        "type": "agent",
        "llm_config_id": "gpt4",
        "system_prompt": "You are a creative writing assistant.",
        "llm": {
          "temperature": 1.2,
          "max_tokens": 8000,
          "system_prompt": "Override: You are an expert creative writer with a flair for storytelling."
        },
        "mcp_servers": ["research_tools", "writing_tools"],
        "include_history": true,
        "description": "Creative writing agent with custom LLM parameters"
      }
    ]
    ```

=== "LLMs"

    **OpenAI Configuration**:
    ```json title="config/llms/openai_llms.json"
    [
      {
        "name": "gpt4",
        "type": "llm",
        "provider": "openai",
        "model": "gpt-4-turbo-preview",
        "temperature": 0.7,
        "max_tokens": 4000,
        "api_base": "https://api.openai.com/v1",
        "api_version": "2024-02-01",
        "description": "OpenAI GPT-4 for general tasks"
      },
      {
        "name": "gpt4_creative",
        "type": "llm",
        "provider": "openai",
        "model": "gpt-4-turbo-preview",
        "temperature": 1.0,
        "max_tokens": 8000,
        "default_system_prompt": "You are a creative writing assistant.",
        "description": "GPT-4 configured for creative writing tasks"
      }
    ]
    ```

    **Anthropic Configuration**:
    ```json title="config/llms/anthropic_llms.json"
    [
      {
        "name": "claude_sonnet",
        "type": "llm",
        "provider": "anthropic",
        "model": "claude-3-sonnet-20240229",
        "temperature": 0.5,
        "max_tokens": 8000,
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "description": "Anthropic Claude for analytical tasks"
      },
      {
        "name": "claude_haiku",
        "type": "llm",
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "temperature": 0.3,
        "max_tokens": 4000,
        "default_system_prompt": "You are a fast, efficient assistant.",
        "description": "Fast Claude model for quick responses"
      }
    ]
    ```

    **Local/Self-Hosted LLMs**:
    ```json title="config/llms/local_llms.json"
    [
      {
        "name": "local_llama",
        "type": "llm",
        "provider": "ollama",
        "model": "llama2:13b",
        "api_base": "http://localhost:11434",
        "temperature": 0.7,
        "max_tokens": 2000,
        "description": "Local Llama2 model via Ollama"
      },
      {
        "name": "custom_model",
        "type": "llm",
        "provider": "openai_compatible",
        "model": "custom-model-v1",
        "api_base": "http://localhost:8000/v1",
        "temperature": 0.5,
        "max_tokens": 4000,
        "description": "Custom self-hosted model"
      }
    ]
    ```

=== "MCP Servers"

    **Local Python Servers** (transport_type inferred as "stdio"):
    ```json title="config/mcp_servers/local_servers.json"
    [
      {
        "name": "weather_server",
        "type": "mcp_server",
        "server_path": "./servers/weather_server.py",
        "capabilities": ["tools"],
        "timeout": 30.0,
        "registration_timeout": 60.0,
        "description": "Local weather data server"
      },
      {
        "name": "file_manager",
        "type": "mcp_server",
        "server_path": "../shared_servers/file_manager.py",
        "capabilities": ["tools", "resources"],
        "timeout": 45.0,
        "registration_timeout": 90.0,
        "description": "File system management server"
      }
    ]
    ```

    **Remote HTTP Servers** (transport_type inferred as "http_stream"):
    ```json title="config/mcp_servers/remote_servers.json"
    [
      {
        "name": "remote_api",
        "type": "mcp_server",
        "http_endpoint": "https://api.example.com/mcp",
        "capabilities": ["tools"],
        "headers": {
          "Authorization": "Bearer {API_TOKEN}",
          "Content-Type": "application/json"
        },
        "timeout": 45.0,
        "sse_timeout": 120.0,
        "description": "Remote API integration server"
      },
      {
        "name": "cloud_storage",
        "type": "mcp_server",
        "http_endpoint": "https://storage.cloudprovider.com/mcp-endpoint",
        "capabilities": ["resources"],
        "headers": {
          "Authorization": "Bearer {CLOUD_TOKEN}"
        },
        "timeout": 60.0,
        "description": "Cloud storage integration"
      }
    ]
    ```

    **Local Command Servers** (transport_type inferred as "local"):
    ```json title="config/mcp_servers/executable_servers.json"
    [
      {
        "name": "node_tools",
        "type": "mcp_server",
        "command": "node",
        "args": ["./servers/tool-server.js", "--port", "{PORT}"],
        "capabilities": ["tools"],
        "timeout": 20.0,
        "registration_timeout": 45.0,
        "description": "Node.js-based tool server"
      },
      {
        "name": "python_tools",
        "type": "mcp_server",
        "command": "python",
        "args": ["-m", "my_tools.server", "--config", "{CONFIG_PATH}"],
        "capabilities": ["tools"],
        "timeout": 30.0,
        "description": "Python module-based tool server"
      }
    ]
    ```

=== "Workflows"

    **Linear Workflows**:
    ```json title="config/workflows/linear_workflows.json"
    [
      {
        "name": "data_pipeline",
        "type": "linear_workflow",
        "steps": ["data_collector", "data_processor", "data_analyst"],
        "include_history": true,
        "description": "Sequential data processing pipeline"
      },
      {
        "name": "content_creation",
        "type": "linear_workflow",
        "steps": [
          {"name": "researcher", "type": "agent"},
          {"name": "writer", "type": "agent"},
          {"name": "editor", "type": "agent"},
          {"name": "publisher", "type": "agent"}
        ],
        "include_history": false,
        "description": "Content creation and publishing workflow"
      }
    ]
    ```

    **Custom Workflows**:
    ```json title="config/workflows/custom_workflows.json"
    [
      {
        "name": "custom_analysis",
        "type": "custom_workflow",
        "module_path": "./workflows/custom_analysis.py",
        "class_name": "CustomAnalysisWorkflow",
        "description": "Custom Python workflow for complex analysis"
      },
      {
        "name": "dynamic_routing",
        "type": "custom_workflow",
        "module_path": "./workflows/dynamic_router.py",
        "class_name": "DynamicRoutingWorkflow",
        "description": "Dynamic agent routing based on input classification"
      }
    ]
    ```

    **Mixed Workflow Steps**:
    ```json title="config/workflows/mixed_workflows.json"
    [
      {
        "name": "complex_pipeline",
        "type": "linear_workflow",
        "steps": [
          "initial_agent",
          {"name": "data_processor", "type": "agent"},
          {"name": "sub_workflow", "type": "linear_workflow"},
          {"name": "final_analysis", "type": "custom_workflow"}
        ],
        "include_history": true,
        "description": "Complex workflow with mixed component types"
      }
    ]
    ```

## ConfigManager Usage Examples

=== "Python API"

    **Basic Operations**:
    ```python
    # Initialize ConfigManager
    config_manager = ConfigManager(start_dir=Path("/path/to/project"))

    # Retrieve component configuration
    agent_config = config_manager.get_config("agent", "weather_agent")
    if agent_config:
        print(f"Found agent: {agent_config['name']}")

    # List all components of a type
    all_llms = config_manager.list_configs("llm")
    print(f"Available LLMs: {[llm['name'] for llm in all_llms]}")
    ```

    **Component CRUD Operations**:
    ```python
    # Create new component
    new_agent = {
        "name": "test_agent",
        "type": "agent",
        "llm_config_id": "gpt4",
        "system_prompt": "You are a helpful assistant"
    }
    result = config_manager.create_component("agent", new_agent, project="my_project")

    # Update component
    updated_agent = {**new_agent, "system_prompt": "Updated prompt"}
    result = config_manager.update_component("agent", "test_agent", updated_agent)

    # Delete component
    result = config_manager.delete_component("agent", "test_agent")
    ```

    **Validation and Testing**:
    ```python
    # Validate component
    is_valid, errors = config_manager.validate_component("agent", "test_agent")
    if not is_valid:
        print(f"Validation errors: {errors}")

    # In-memory registration for testing
    config_manager.register_component_in_memory("agent", {
        "name": "temp_agent",
        "type": "agent",
        "llm_config_id": "test_llm",
        "system_prompt": "Temporary test agent"
    })

    # LLM validation tracking
    config_manager.validate_llm("gpt4")
    validation_time = config_manager.get_llm_validation("gpt4")
    ```

=== "CLI Usage"

    **Basic Commands**:
    ```bash
    # List all available agents
    aurite list agents

    # List all components (shows the component index)
    aurite list

    # Show specific component configuration
    aurite show weather_agent

    # Show all components of a type
    aurite show agent

    # Show full configuration details
    aurite show weather_agent --full
    ```

    **Component Management**:
    ```bash
    # Create new component
    aurite create agent my_new_agent --llm gpt4 --prompt "You are helpful"

    # Update component
    aurite update agent my_agent --prompt "Updated system prompt"

    # Delete component
    aurite delete agent my_agent

    # Validate component
    aurite validate agent weather_agent

    # Validate all components
    aurite validate
    ```

    **Project and Context Operations**:
    ```bash
    # List components in specific project
    aurite list agents --project my_project

    # Create component in specific project
    aurite create agent new_agent --project my_project --llm gpt4

    # Show configuration hierarchy
    aurite show --hierarchy

    # Refresh configuration index
    aurite refresh
    ```
