# Project Rules: Framework Development (aurite-agents)

## 1. Objective

This document outlines the core purpose, architecture, key documentation, and essential file structure for developing within the **Aurite Agents** framework. It serves as a quick reference guide for understanding the project's layout and design principles, complementing the global phase-specific rules.

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

*   **`README.md`:** Provides a detailed overview of the framework, core concepts, configuration specifics, installation, and usage examples for the different entrypoints. **(Note: You mentioned this needs updating; please ensure it reflects the latest state).**
*   **`README_packaged.md`:** Provides an overview of the aurite package

### User Documentation
*   **`docs/components/PROJECT.md`:** Explains how project files work, along with referencing the relevant component configuration documents in `docs/components`.
*   **`docs/components/`:** Detailed overview of each component type, including configuration settings and usager examples.
*   **`docs/USC - Get Started/Start  Here.md`:** Overview of tutorial for new users

### Framework Developer Documentation
*   **`docs/layers/framework_overview.md`:** (As referenced in the README) Provides a higher-level view.
*   **`docs/layers/`:** Contains documents describing each layer of the Domain-Driven Design (DDD) architecture (e.g., `1_entrypoints.md`, `2_orchestration.md`, `3_host.md`). These are **essential** reading before modifying code within a specific layer to understand its responsibilities and boundaries.
*   **`tests/`:** Existing tests serve as executable documentation of expected behavior.
