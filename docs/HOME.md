# Aurite Agent Framework

![Aurite Logo](aurite_logo.png)

Welcome to the internal documentation site for the **Aurite Agent Framework**. This framework is designed for building, orchestrating, and managing sophisticated AI agents.

Aurite provides a comprehensive suite of tools and a flexible architecture to support the development of complex agentic applications, enabling interaction with various Language Models (LLMs) and external services through the Model Context Protocol (MCP).

## Key Documentation Areas

Navigate through the documentation using the links below to understand different aspects of the Aurite Agent Framework:

### 1. Getting Started & Main Overview
*   **[[./README.md]]**: The main project README.md. This is a great place to start for installation, setup, and a general overview of the framework.

### 2. Framework Architecture
*   **[[./framework_overview.md|Framework Overview]]**: A deep dive into the overall architecture, design principles, and how different parts of the framework interact.
*   **Framework Layers**: Understand the specific responsibilities of each architectural layer.
    *   **[[layers/1_entrypoints.md|Layer 1: Entrypoints]]**: Covers the API, CLI, and Worker entrypoints.
    *   **[[layers/2_orchestration.md|Layer 2: Orchestration]]**: Details the `Aurite` (HostManager) and `ExecutionFacade`.
    *   **[[layers/3_host.md|Layer 3: Host Infrastructure]]**: Explains the `MCPHost` system for managing MCP server connections.
    *   *(Note: Refer to `layers/template.md` for the general structure of layer documentation if specific files are not yet fully populated).*

### 3. Component Configurations
*   **[[components/|Component Configurations Overview]]**: Start here for an overview of how all components (LLMs, Clients, Agents, Workflows, Projects) are configured in Aurite.
    *   [[components/project_configs.md|Project Configs]]
    *   [[components/llms.md|LLM Configs]]
    *   [[components/clients.md|Client Configs]]
    *   [[components/agents.md|Agent Configs]]
    *   [[components/simple_workflows.md|Simple Workflow Configs]]
    *   [[components/custom_workflows.md|Custom Workflow Configs]]

### 4. Packaged Version & CLI
*   **[[./README_packaged.md|Packaged Aurite README]]**: Information specific to the pip-installable `aurite` package, including how to use the `aurite init` CLI command.

---

This landing page will be updated as new documentation sections are added or existing ones are refined.
