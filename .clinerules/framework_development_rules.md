# Project Rules: Framework Development (aurite-agents)

## 1. Objective

This document outlines the core purpose, architecture, key documentation, and essential file structure for developing within the **Aurite Agents** framework. It serves as a quick reference guide for understanding the project's layout and design principles, complementing the global phase-specific rules.

## 2. Core Concepts & Architecture

Aurite Agents is a Python framework for building AI agents using the Model Context Protocol (MCP). Key components include:

*   **MCP Host (`src/host/`):** Manages MCP server connections and component interactions (tools, prompts, resources).
*   **Host Manager (`src/host_manager.py`):** Orchestrates the Host, Agents, and Workflows, loading project configurations.
*   **Agent Framework (`src/agents/`):** Provides the `Agent` class (`src/agents/agent.py`) for LLM interaction logic, using Pydantic models for inputs/outputs defined in `src/agents/agent_models.py`.
*   **Execution Facade (`src/execution/`):** Provides a unified interface (`run_agent`, `run_simple_workflow`, etc.) for executing components.
*   **Entrypoints (`src/bin/`):** API, CLI, and Worker interfaces providing access to the framework's capabilities.
*   **Configuration (`src/config/` & root `config/`):** Pydantic models defined in `src/config/config_models.py` specify the structure for all configurations (Host, Client, Agent, LLM, Workflow, Project). JSON/YAML files in the root `config/` directory provide the specific configurations loaded by the `HostManager`.
*   **Storage (`src/storage/`):** Optional database persistence for configurations and agent history.

The framework follows a layered architecture, detailed in `docs/layers/`. Adherence to these layers is crucial for maintaining separation of concerns and ensuring maintainability.

## 3. Key Documentation

For a comprehensive understanding, always refer to the primary sources of truth:

*   **`README.md`:** Provides a detailed overview of the framework, core concepts, configuration specifics, installation, and usage examples for the different entrypoints. **(Note: You mentioned this needs updating; please ensure it reflects the latest state).**
*   **`docs/layers/`:** Contains documents describing each layer of the Domain-Driven Design (DDD) architecture (e.g., `1_entrypoints.md`, `2_orchestration.md`, `3_host.md`). These are **essential** reading before modifying code within a specific layer to understand its responsibilities and boundaries.
*   **`docs/architecture_overview.md`:** (As referenced in the README) Provides a higher-level view.
*   **`docs/design/`:** Contains specific design documents for major features or systems (e.g., `configuration_system.md`). Consult these when working on related areas.
*   **`tests/`:** Existing tests serve as executable documentation of expected behavior.

## 4. Core Directory Structure

The primary source code resides within the `src/` directory. Key subdirectories include:

```text
src/
├── agents/       # Agent implementation (agent.py), models (agent_models.py), processors
├── bin/          # Entrypoints: API (api/), CLI (cli.py), Worker (worker.py)
│   └── api/
│       └── routes/ # API route definitions per resource type
├── config/       # Configuration models (config_models.py) and management utilities
├── execution/    # Execution facade (facade.py)
├── host/         # MCP Host infrastructure (host.py), connection handling, security, resource management
│   ├── foundation/ # Core host building blocks (clients, roots, routing, security)
│   └── resources/  # Tool/Prompt/Resource registration and execution logic
├── llm/          # LLM client abstractions (base_client.py) and specific providers
├── packaged_servers/ # Example/Bundled MCP Servers for testing or basic use
├── prompt_validation/ # Utilities and workflows for validating prompt outputs
├── servers/      # More complex/managed MCP server implementations (e.g., management, memory)
├── storage/      # Database interaction (models, manager, connection)
└── workflows/    # Simple and Custom workflow implementations
