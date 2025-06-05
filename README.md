# Aurite Agents Framework

**Aurite Agents** is a Python framework designed for building and orchestrating AI agents. These agents can interact with a variety of external tools, prompts, and resources through the Model Context Protocol (MCP), enabling them to perform complex tasks.

Whether you're looking to create sophisticated AI assistants, automate processes, or experiment with agentic workflows, Aurite Agents provides the building blocks and infrastructure to get you started.

## Getting Started

Follow these steps to set up the Aurite Agents framework on your local machine.

### Prerequisites

*   Python >= 3.12 (if running locally without Docker for all services)
*   `pip` (Python package installer)
*   Node.js (LTS version recommended, for frontend development if run locally without Docker)
*   Yarn (Package manager for frontend, if run locally without Docker)
*   Docker & Docker Compose (for the quickstart script and containerized setup)
*   `redis-server` (Required if you plan to use the asynchronous task worker, whether locally or if you add it to Docker Compose)

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Aurite-ai/aurite-agents.git
    cd aurite-agents
    ```

### Quickstart with Docker (Recommended)

The fastest way to get the entire Aurite Agents environment (Backend API, Frontend UI, and PostgreSQL database) up and running is by using the provided setup script with Docker.

1.  **Ensure Docker is running.**
2.  **Run the appropriate setup script for your operating system:**
    *   **For Linux/macOS:**
        In the project root directory (`aurite-agents`), execute:
        ```bash
        ./setup.sh
        ```
    *   **For Windows:**
        In the project root directory (`aurite-agents`), execute:
        ```bat
        setup.bat
        ```
    These scripts will:
    *   Check for Docker and Docker Compose.
    *   Guide you through creating and configuring your `.env` file (including API keys and project selection).
    *   Ask if you want to install optional ML dependencies for your local Python environment (useful if you plan to run or develop certain MCP Servers locally that require them).
    *   Build and start all services using Docker Compose.

    Once complete, the backend API will typically be available at `http://localhost:8000` and the frontend UI at `http://localhost:5173`. The script will display the generated API key needed for the UI.

    **Note on Initial Startup:** The backend container might take a few moments to start up completely, especially the first time, as it initializes MCP servers. During this time, the frontend UI might show a temporary connection error. Please allow a minute or two for all services to become fully operational.

#### Running Docker Compose Directly (Alternative to Setup Scripts)

If you prefer to manage your `.env` file manually or if the setup scripts encounter issues, you can still use Docker Compose:

1.  **Create/Configure `.env` File:** Ensure you have a valid `.env` file in the project root. You can copy `.env.example` to `.env` and fill in the necessary values (especially `ANTHROPIC_API_KEY`, `API_KEY`, and `PROJECT_CONFIG_PATH`).
2.  **Run Docker Compose:**
    ```bash
    docker compose up --build
    ```
    (Use `docker-compose` if you have an older standalone version).

### Manual Installation & Backend Setup

If you prefer to set up and run components manually or without Docker for all services:

1.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

2.  **Install Dependencies:**
    The project uses `pyproject.toml` for dependency management. Install the framework and its dependencies (the `[dev]` is for dev dependencies like pytest) in editable mode:
    ```bash
    pip install -e .[dev]
    ```
    This command allows you to make changes to the source code and have them immediately reflected without needing to reinstall.

3.  **Environment Variables Setup:**
    Before running the system, you need to set up your environment variables.

    a.  **Copy the Example File:** In the project root, copy the `.env.example` file to a new file named `.env`:
        ```bash
        cp .env.example .env
        ```
    b.  **Edit `.env`:** Open the newly created `.env` file and fill in your specific configurations and secrets. Pay close attention to comments like `#REPLACE` indicating values you must change.

    Key variables you'll need to configure in your `.env` file include:

    *   `PROJECT_CONFIG_PATH`: **Crucial!** Set this to the absolute path of the main JSON project configuration file you want the server to load on startup (e.g., `config/projects/default.json`).
    *   `API_KEY`: A secret key to secure the FastAPI endpoints. Generate a strong random key.
    *   `ANTHROPIC_API_KEY` (or other LLM provider keys): Required if your agents use specific LLMs like Anthropic's Claude.

    The `.env` file also contains settings for Redis, optional database persistence (`AURITE_ENABLE_DB`, `AURITE_DB_URL`, etc.), and other service configurations. Review all entries marked with `#REPLACE`.

    **Important Security Note: Encryption Key**

    *   **`AURITE_MCP_ENCRYPTION_KEY`**: This environment variable is used by the framework's `SecurityManager` to encrypt sensitive data.
        *   If not set, a key will be **auto-generated on startup**. This is convenient for quick local testing.
        *   **However, for any persistent deployment, or if you intend to use features that rely on encrypted storage (even for development), it is critical to set this to a strong, persistent, URL-safe base64-encoded 32-byte key.**
        *   Relying on an auto-generated key means that any encrypted data may become inaccessible if the application restarts and generates a new key.
        *   Please refer to `SECURITY.md` (to be created) for detailed information on generating, managing, and understanding the importance of this key. You can find `AURITE_MCP_ENCRYPTION_KEY` commented out in your `.env.example` file as a reminder.

4.  **Running the Backend API Server:**
    The primary way to interact with the framework is through its FastAPI server:
    ```bash
    python -m src.bin.api.api
    ```
    or use the `pyproject.toml` script:
    ```bash
    start-api
    ```
    (This script is available after running `pip install -e .[dev]` as described in the Manual Installation section. If using Docker, the API starts automatically within its container.)

    By default, it starts on `http://0.0.0.0:8000`. You can then send requests to its various endpoints to execute agents, register components, etc. (e.g., using Postman or `curl`).

### Frontend UI Setup

To set up and run the frontend developer UI for interacting with the Aurite Agents Framework:

**Note:** Ensure the backend API server (Step 4 in Manual Setup above) is running before starting the frontend if you are not using the Docker quickstart.

1.  **Navigate to the Frontend Directory:**
    Open a new terminal or use your existing one to change into the `frontend` directory:
    ```bash
    cd frontend
    ```

2.  **Install Frontend Dependencies:**
    If you don't have Yarn installed, you can install it by following the instructions on the [official Yarn website](https://classic.yarnpkg.com/en/docs/install).

    Inside the `frontend` directory, install the necessary Node.js packages using Yarn:
    ```bash
    yarn install
    ```

3.  **Start the Frontend Development Server:**
    Once dependencies are installed, start the Vite development server:
    ```bash
    yarn dev
    ```
    The frontend UI will typically be available in your web browser at `http://localhost:5173`.

## Architecture Overview

The framework follows a layered architecture, illustrated below:

```mermaid
graph TD
    A["Layer 1: Entrypoints <br/> (API, CLI, Worker)"] --> B{"Layer 2: Orchestration <br/> (HostManager, ExecutionFacade)"};
    B --> C["Layer 3: Host Infrastructure <br/> (MCPHost)"];
    C --> D["Layer 4: External Capabilities <br/> (MCP Servers)"];

    style A fill:#D1E8FF,stroke:#3670B3,stroke-width:2px,color:#333333
    style B fill:#C2F0C2,stroke:#408040,stroke-width:2px,color:#333333
    style C fill:#FFE0B3,stroke:#B37700,stroke-width:2px,color:#333333
    style D fill:#FFD1D1,stroke:#B33636,stroke-width:2px,color:#333333
```

For a comprehensive understanding of the architecture, component interactions, and design principles, please see [`docs/framework_overview.md`](docs/framework_overview.md). Detailed information on each specific layer can also be found in the `docs/layers/` directory.

## Core Concepts for Users

Understanding these concepts will help you configure and use the Aurite Agents framework effectively.

### 1. Projects

A **Project** in Aurite Agents is defined by a JSON configuration file (e.g., `config/projects/default.json`). This file acts as a central manifest for your agentic application, specifying:
*   The name and description of the project.
*   Which LLM configurations to use (`llm_configs`).
*   Which MCP Servers (Clients) to connect to (`clients`).
*   Which Agents, Simple Workflows, and Custom Workflows are part of this project.

The active project configuration tells the `HostManager` what components to load and make available.

### 2. Agentic Components

These are the primary building blocks you'll work with:

*   **Agents (`src/agents/agent.py`):**
    *   LLM-powered entities that can engage in conversations, use tools, and optionally maintain history.
    *   Configured via `AgentConfig` models, typically stored in JSON files (e.g., `config/agents/my_weather_agent.json`) and referenced in your project file.
    *   Key settings include the LLM to use, system prompts, and rules for accessing tools/clients.

    ```mermaid
    graph TD
        Agent["Agent <br/> (src/agents/agent.py)"] --> LLM["LLM <br/> (e.g., Claude, GPT)"];
        Agent --> Clients["MCP Clients <br/> (Connections to Servers)"];

        Clients --> MCP1["MCP Server 1 <br/> (e.g., Weather Tool)"];
        Clients --> MCP2["MCP Server 2 <br/> (e.g., Database)"];
        Clients --> MCP3["MCP Server 3 <br/> (e.g., Custom API)"];

        style Agent fill:#ADD8E6,stroke:#00008B,stroke-width:2px,color:#333333
        style LLM fill:#FFFFE0,stroke:#B8860B,stroke-width:2px,color:#333333
        style Clients fill:#E6E6FA,stroke:#483D8B,stroke-width:2px,color:#333333
        style MCP1 fill:#90EE90,stroke:#006400,stroke-width:2px,color:#333333
        style MCP2 fill:#90EE90,stroke:#006400,stroke-width:2px,color:#333333
        style MCP3 fill:#90EE90,stroke:#006400,stroke-width:2px,color:#333333
    ```

*   **Simple Workflows (`src/workflows/simple_workflow.py`):**
    *   Define a sequence of Agents to be executed one after another.
    *   Configured via `WorkflowConfig` models (e.g., `config/workflows/my_simple_sequence.json`).
    *   Useful for straightforward, multi-step tasks where the output of one agent becomes the input for the next.

    ```mermaid
    graph LR
        Agent1["Agent A"] -->|Input/Output| Agent2["Agent B"];
        Agent2 -->|Input/Output| Agent3["Agent C"];

        style Agent1 fill:#ADD8E6,stroke:#00008B,stroke-width:2px,color:#333333
        style Agent2 fill:#ADD8E6,stroke:#00008B,stroke-width:2px,color:#333333
        style Agent3 fill:#ADD8E6,stroke:#00008B,stroke-width:2px,color:#333333
    ```

*   **Custom Workflows (`src/workflows/custom_workflow.py`):**
    *   Allow you to define complex orchestration logic using custom Python classes.
    *   Configured via `CustomWorkflowConfig` models, pointing to your Python module and class.
    *   Provide maximum flexibility for intricate interactions and conditional logic. Here's a conceptual example of what a custom workflow class might look like:
    ```python
    # Example: src/my_custom_workflows/my_orchestrator.py class definition
    class MyCustomOrchestrator:
        async def execute_workflow(
            self,
            initial_input: Any,
            executor: "ExecutionFacade", # Type hint for the passed executor
            session_id: Optional[str] = None # Optional session_id
        ) -> Any:

            # --- Your custom Python orchestration logic here ---
            # You can call other agents, simple workflows, or even other custom workflows
            # using the 'executor' instance.

            # Example: Call an agent
            agent_result = await executor.run_agent(
                agent_name="MyProcessingAgent",
                user_message=str(initial_input), # Ensure message is a string
            )

            processed_data = agent_result.final_response.content[0].text

            # Example: Call a simple workflow
            simple_workflow_result = await executor.run_simple_workflow(
                workflow_name="MyFollowUpWorkflow",
                initial_input=processed_data
            )
            simple_workflow_output = simple_workflow_result.get("final_message")

            # Example: Call a custom workflow
            custom_workflow_result = await executor.run_custom_workflow(custom_workflow_name="MyCustomWorkflow", initial_input=simple_workflow_output)

            return custom_workflow_result
    ```
    To use this custom workflow:
      1. Save this code into a Python file (e.g., in src/my_custom_workflows/basic_executor_example.py).
      2. In your project's JSON configuration (e.g., config/projects/default.json), add or update a custom_workflow entry like this:
    ```json
    {
      "custom_workflows": [
        {
          "name": "MyBasicWorkflowExample",
          "module_path": "src.my_custom_workflows.basic_executor_example",
          "class_name": "BasicExecutorExampleWorkflow",
          "description": "A basic example demonstrating custom workflow executor usage."
        }
        // ... any other custom workflows
      ]
    }
    ```
    * (Ensure this fits into your overall project JSON structure, typically under a "custom_workflows" key)
    3. Ensure the agent named "YourConfiguredAgentName" (or whatever name you use in the code) is also defined in the 'agents' section of your project configuration.

### 3. LLM Configurations

*   Define settings for different Large Language Models (e.g., model name, temperature, max tokens).
*   Managed by `LLMConfig` models, typically stored in `config/llms/default_llms.json` or a custom file.
*   Agents reference these LLM configurations by their `llm_id`, allowing you to easily switch or share LLM settings.
*   The core LLM client abstraction is `src/llm/base_client.py`.

### 4. MCP Servers (as Clients)

*   External processes that provide tools, prompts, or resources according to the Model Context Protocol (MCP).
*   The Aurite framework connects to these servers, referring to them as "Clients."
*   Configured via `ClientConfig` models (e.g., `config/clients/default_clients.json`), specifying the server's path, capabilities, and access rules.
*   An example MCP server is `src/packaged_servers/weather_mcp_server.py`.

## Configuration System Overview (User Perspective)

*   **Main Project File:** The system loads its entire configuration based on the project file specified by the `PROJECT_CONFIG_PATH` environment variable. This project file (e.g., `config/projects/default.json`) defines configurations or references other JSON files for specific components like agents, clients, and LLMs. For example, a project file might look like this:
    ```json
    {
        "llms": [
        {
        "llm_id": "anthropic_claude_3_opus",
        "provider": "anthropic",
        "model_name": "claude-3-opus-20240229",
        "temperature": 0.7,
        "max_tokens": 4096,
        "max_iterations": 10
        }
        ],
        "clients": [
            {
            "client_id": "weather_server",
            "server_path": "src/packaged_servers/weather_mcp_server.py",
            "capabilities": ["tools", "prompts"],
            "timeout": 15.0,
            "routing_weight": 1.0,
            "roots": []
            },
            "planning_server",
            "address_server"
        ],
        "agents": [
            {
            "name": "Weather Agent",
            "system_prompt": "Your job is to use the tools at your disposal to learn the weather information needed in order to respond to the user's query appropriately.",
            "client_ids": ["weather_server"],
            "llm_id": "anthropic_claude_3_opus",
            "exclude_components": ["current_time"]
            },
            {
            "name": "Weather Planning Workflow Step 2",
            "system_prompt": "You have been provided with weather information in the user message. Your ONLY task is to use the 'save_plan' tool to create and save a plan detailing what someone should wear based *only* on the provided weather information.",
            "client_ids": ["planning_server"],
            "temperature": 0.7,
            "max_tokens": 4096,
            "max_iterations": 10,
            }
        ],
        "workflows": [
            {
            "name": "A second testing workflow using weather and planning servers",
            "steps": ["Weather Agent", "Weather Planning Workflow Step 2"],
            "description": "Updated workflow to test simple workflow execution using agents."
            }
        ],
        "custom_workflows": [
            {
            "name": "Prompt Validation Workflow",
            "module_path": "src/prompt_validation/prompt_validation_workflow.py",
            "class_name": "PromptValidationWorkflow",
            "description": "A custom workflow built to test agentic components."
            }
        ]
    }
    ```
*   **Component JSON Files:** You'll typically define your agents, LLM settings, client connections, and workflows in separate JSON files within the `config/` subdirectories (e.g., `config/agents/`, `config/llms/`). You can reference these components by their ID as seen in the `planning_server` and `address_server` references in the `clients` section of the example project json file above.
*   **Pydantic Models:** All configuration files are validated against Pydantic models defined in `src/config/config_models.py`. This ensures your configurations are correctly structured.
*   **Database Persistence (Optional):** If `AURITE_ENABLE_DB` is set to `true` and database connection variables are provided, the framework can persist agent configurations and conversation history.
*

## Other Entrypoints

Besides the main API server, the framework offers other ways to interact:

*   **Command-Line Interface (`src/bin/cli.py`):** For terminal-based interaction.
    The `run-cli` script is available after performing the Manual Installation and running `pip install -e .[dev]`.
    ```bash
    # Example: Execute an agent (ensure API server is running)
    # Assumes API_KEY environment variable is set.
    run-cli execute agent "Weather Agent" "What is the weather in London?"

    # Example: Execute a simple workflow
    run-cli execute workflow "main" "What should I wear in San Francisco today?"

    # Example: Execute a custom workflow (input must be a valid JSON string)
    run-cli execute custom-workflow "ExampleCustomWorkflow" "{\"city\": \"London\"}"
    ```
    **Using CLI with Docker:** If you are using the Docker setup, these CLI commands need to be run *inside* the backend service container. You can do this by first finding your backend container ID or name (e.g., using `docker ps`) and then executing the command:
    ```bash
    docker exec -it <your_backend_container_name_or_id> run-cli execute agent "Weather Agent" "What is the weather in London?"
    ```
    Ensure the `API_KEY` environment variable is set within the container's environment (it should be if you used the setup scripts or configured your `.env` file correctly).

*   **Redis Worker (`src/bin/worker.py`):** For asynchronous task processing (if Redis is set up and `redis-server` is running).
    ```bash
    python -m src.bin.worker
    ```

## Simplified Directory Structure

Key directories for users:

*   **`config/`**: This is where you'll spend most of your time defining configurations.
    *   `config/projects/`: Contains your main project JSON files.
    *   `config/agents/`: JSON files for Agent configurations.
    *   `config/clients/`: JSON files for MCP Server (Client) configurations.
    *   `config/llms/`: JSON files for LLM configurations.
    *   `config/workflows/`: JSON files for Simple Workflow configurations.
    *   `config/custom_workflows/`: JSON files for Custom Workflow configurations.
*   **`src/bin/`**: Entrypoint scripts (API, CLI, Worker).
*   **`src/agents/`**: Core `Agent` class implementation.
*   **`src/workflows/`**: Implementations for `SimpleWorkflowExecutor` and `CustomWorkflowExecutor`.
*   **`src/packaged_servers/`**: Example MCP server implementations.
*   **`docs/`**: Contains all project documentation.
    *   `docs/framework_overview.md`: For a deep dive into the architecture.
    *   `docs/layers/`: Detailed documentation for each architectural layer.
*   **`tests/`**: Automated tests. See `tests/README.md` for instructions on running tests.
*   **`.env`**: (You create this) For environment variables like API keys and `PROJECT_CONFIG_PATH`.

## Further Documentation

*   **Framework Architecture:** For a detailed understanding of the internal architecture, component interactions, and design principles, please see [`docs/framework_overview.md`](docs/framework_overview.md).
*   **Layer-Specific Details:**
    *   [`docs/layers/1_entrypoints.md`](docs/layers/1_entrypoints.md) (API, CLI, Worker)
    *   [`docs/layers/2_orchestration.md`](docs/layers/2_orchestration.md) (HostManager, ExecutionFacade)
    *   [`docs/layers/3_host.md`](docs/layers/3_host.md) (MCPHost System)
*   **Testing:** Information on running tests can be found in `tests/README.md`. Testing strategies for each layer are also detailed within their respective documentation in `docs/layers/`.

## Contributing

Contributions are welcome! Please follow standard fork/pull request workflows. Ensure tests pass and documentation is updated for any changes.
