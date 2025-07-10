# Aurite Agents Framework

<p align="center">
  <img src="docs/images/aurite_logo.png" alt="Aurite Logo" width="200"/>
</p>

<p align="center">
  <strong>A Python framework for building, testing, and running AI agents.</strong>
</p>

---

**Aurite Agents** is a powerful, configuration-driven framework designed for building and orchestrating sophisticated AI agents. It enables agents to interact with a variety of external tools, prompts, and resources through the Model Context Protocol (MCP), allowing them to perform complex, multi-step tasks.

Whether you're creating advanced AI assistants, automating processes, or experimenting with agentic workflows, Aurite provides the modular building blocks and robust infrastructure you need.

## Key Features

-   **Hierarchical Configuration:** Organize your components with a powerful **Workspace -> Project** system that allows for shared configurations and clear separation of concerns.
-   **Declarative Components:** Define agents, LLMs, tools, and workflows in simple JSON or YAML files.
-   **Interactive CLI & TUIs:** A rich command-line interface (`aurite`) and two built-in Textual User Interfaces (TUIs) for interactive chat and configuration editing.
-   **Extensible Tooling:** Connect to any tool or service using the **Model Context Protocol (MCP)**, with built-in support for local and remote servers.
-   **Flexible Orchestration:** Chain agents together in `simple_workflows` for sequential tasks or write custom Python logic in `custom_workflows` for complex orchestration.
-   **REST API:** A comprehensive FastAPI server that exposes all framework functionality for programmatic access and UI development.

## Getting Started

The best way to start with Aurite is by installing the Python package and using the interactive initializer.

1.  **Install the package:**
    ```bash
    pip install aurite
    ```
2.  **Initialize your first project:**
    ```bash
    aurite init
    ```
    This command will launch an interactive wizard to set up your workspace and first project.

For a complete walkthrough, see the [**Package Installation Guide**](docs/getting-started/installation_guides/package_installation_guide.md).

Developers who wish to contribute to the framework should follow the [**Repository Installation Guide**](docs/getting-started/installation_guides/repository_installation_guide.md).

## Core Concepts

### 1. Workspaces & Projects

Aurite uses a hierarchical system to organize your work, defined by a special `.aurite` file.

-   **Workspace:** A top-level container that can manage multiple projects and share common configurations (e.g., a standard set of LLMs).
-   **Project:** A self-contained directory holding all the configurations for a specific application or task.

This structure allows for clean separation and promotes reusable components. Learn more in the [**Projects and Workspaces Guide**](docs/config/projects_and_workspaces.md).

### 2. Components

Your application is built by defining and combining different types of components in `.json` or `.yaml` files.

-   **[Agents](docs/config/agent.md):** The core actors, powered by an LLM and capable of using tools.
-   **[LLMs](docs/config/llm.md):** Configurations for different language models (e.g., GPT-4, Claude 3).
-   **[MCP Servers](docs/config/mcp_server.md):** Connections to external tools and resources.
-   **[Simple Workflows](docs/config/simple_workflow.md):** A sequence of agents to be executed in order.
-   **[Custom Workflows](docs/config/custom_workflow.md):** Complex orchestration logic defined in your own Python code.

### 3. Interfaces

Aurite provides multiple ways to interact with the framework:

-   [**Command-Line Interface (CLI)**](docs/usage/cli_reference.md): The primary tool for managing your projects. Use it to `init`, `list`, `show`, `run`, and `edit` your components.
-   [**Textual User Interfaces (TUIs)**](docs/usage/tui_guide.md): Rich, in-terminal applications for interactive chat with agents (`aurite run <agent_name>`) and live configuration editing (`aurite edit`).
-   [**REST API**](docs/usage/api_reference.md): A complete FastAPI server (`aurite api`) that exposes all framework functionality for UIs and programmatic control.

## Architecture Overview

The framework is built on a layered architecture that separates concerns from the user-facing entrypoints down to the external tool connections.

![Aurite Architecture](docs/images/architecture_diagram.svg)

For a deep dive into the framework's design, see the [**Architecture Overview**](docs/architecture/overview.md).

## Documentation

-   **Getting Started**
    -   [Package Installation](docs/getting-started/installation_guides/package_installation_guide.md)
    -   [Repository Installation](docs/getting-started/installation_guides/repository_installation_guide.md)
    -   [Tutorials](docs/getting-started/tutorials/Tutorials_Overview.md)
-   **Usage Guides**
    -   [CLI Reference](docs/usage/cli_reference.md)
    -   [TUI Guide](docs/usage/tui_guide.md)
    -   [API Reference](docs/usage/api_reference.md)
-   **Configuration**
    -   [Projects and Workspaces](docs/config/projects_and_workspaces.md)
    -   [Agent Config](docs/config/agent.md)
    -   [LLM Config](docs/config/llm.md)
    -   [MCP Server Config](docs/config/mcp_server.md)
    -   [Simple Workflow Config](docs/config/simple_workflow.md)
    -   [Custom Workflow Config](docs/config/custom_workflow.md)
-   **Architecture**
    -   [Architecture Overview](docs/architecture/overview.md)

## Contributing

Contributions are welcome! Please follow standard fork/pull request workflows. Ensure tests pass and documentation is updated for any changes.
