# Project Rules: Framework Development (aurite-agents)

## 1. Objective

This document outlines the core purpose, architecture, key documentation, and essential file structure for developing within the **Aurite Agents** framework. It serves as a quick reference guide for understanding the project's layout and design principles, complementing the global phase-specific rules.

The project configuration file that the framework will initialize with is `aurite_config.json` located in the root of the repository. This project file is explained in further detail in the Project Configuration document.

## 2. Core Concepts & Architecture

Aurite Agents is a Python framework for building AI agents using the Model Context Protocol (MCP). Key components include:

*   **MCP Host (`src/aurite/host/`):** Manages MCP server connections and component interactions (tools, prompts, resources).
*   **Host Manager (`src/aurite/host_manager.py`):** Orchestrates the Host, Agents, and Workflows, loading project configurations.
*   **Agent Framework (`src/aurite/components/agents/`):** Provides the `Agent` class (`src/aurite/components/agents/agent.py`) for LLM interaction logic, using Pydantic models for inputs/outputs defined in `src/aurite/components/agents/agent_models.py`.
*   **Execution Facade (`src/aurite/execution/`):** Provides a unified interface (`run_agent`, `run_simple_workflow`, etc.) for executing components.
*   **Entrypoints (`src/aurite/bin/`):** API, CLI, and Worker interfaces providing access to the framework's capabilities.
*   **Configuration (`src/aurite/config/` & root `config/`):** Pydantic models defined in `src/config/config_models.py` specify the structure for all configurations (Host, Client, Agent, LLM, Workflow, Project). JSON/YAML files in the root `config/` directory provide the specific configurations loaded by the `HostManager`.
*   **Storage (`src/aurite/storage/`):** Optional database persistence for configurations and agent history.
*   **Package Scripts (`src/aurite/bin/cli`):** Provides the scripts used in the packaged version of the framework, most notably `aurite init` which scaffolds the folders and files used by the framework. These files contain examples copied over from `src/aurite/packaged`.

The framework follows a layered architecture, detailed in `docs/layers/`. Adherence to these layers is crucial for maintaining separation of concerns and ensuring maintainability.

## 3. Key Documentation

For a comprehensive understanding, always refer to the primary sources of truth:

*   **General Overview (`README.md`):** For a high-level introduction to the framework, its core concepts, configuration specifics, installation, and usage examples for the different entrypoints.
    *   **[Read the General Overview](README.md)**

*   **Documentation Guide (`documentation_guide.md`):** To understand how all documentation is organized, which documents to read for specific tasks, and which documents to update after making changes.
    *   **[Read the Documentation Guide](.clinerules/documentation_guide.md)**

*   **Framework Development Workflow (`framework_development_rules.md`):** To understand the structured, multi-phase workflow for development within the framework.
    *   **[Read the Framework Development Workflow](.clinerules/framework_development_rules.md)**

*   **Project and Component Configuration (`docs/components/PROJECT.md`):** To understand how project files (`aurite_config.json`) work and how to configure all the individual components (Agents, LLMs, Clients, etc.).
    *   **[Read the Project & Component Guide](docs/components/PROJECT.md)**

*   **Framework Architecture (`docs/layers/framework_overview.md`):** For a detailed, developer-focused explanation of the layered architecture, how the different parts of the framework interact, and the design principles.
    *   **[Read the Framework Architecture Overview](docs/layers/framework_overview.md)**

*   **Testing Strategy (`tests/README.md`):** To learn how to run tests, understand the testing structure, and see how to add new tests for your contributions.
    *   **[Read the Testing Guide](tests/README.md)**