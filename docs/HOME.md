# Aurite Agent Framework

Welcome to the internal documentation site for the **Aurite Agent Framework**. This framework is designed for building, orchestrating, and managing sophisticated AI agents.

Aurite provides a comprehensive suite of tools and a flexible architecture to support the development of complex agentic applications, enabling interaction with various Language Models (LLMs) and external services through the Model Context Protocol (MCP).

## Key Documentation Areas

Navigate through the documentation using the links below to understand different aspects of the Aurite Agent Framework:

### 1. Getting Started & Main Overview

*   **[[USC/Start_Here|Tutorial Modules Overview (USC)]]** The learning section overview. This section contains concepts, tutorials, and optional assignments to get you more familiar with the framework.

* **[Aurite Package README](https://github.com/Aurite-ai/aurite-agents/blob/main/README_packaged.md)**: Information specific to the pip-installable `aurite` package, including how to use the `aurite init` CLI command.

### 2. Component Configurations
An in-depth look at the features each component offers through json configuration.
*   **[[components/PROJECT.md|Project Configs]]** Start here!
*   **[[components/llm.md|LLM Configs]]**
*   **[[components/mcp_server.md|MCP Server Configs]]**
*   **[[toolbox/mcp_server_directory.md|Packaged MCP Servers]]**
*   **[[components/agent.md|Agent Configs]]**
*   **[[components/simple_workflow.md|Simple Workflow Configs]]**
*   **[[components/custom_workflow.md|Custom Workflow Configs]]**

### 3. Framework Architecture
*   **[[layers/framework_overview.md|Framework Overview]]**: A diagram of the overall architecture, design principles, and how different parts of the framework interact.
*   **Framework Layers**: Understand the specific responsibilities of each architectural layer.
    *   **[[layers/0_frontends.md|Layer 0: Frontend Developer UI]]** Developer UI extension built off the API.
    *   **[[layers/1_entrypoints.md|Layer 1: Entrypoints]]**: Covers the API, CLI, and Worker entrypoints.
    *   **[[layers/2_orchestration.md|Layer 2: Orchestration]]**: Details the `Aurite` (HostManager) and `ExecutionFacade`.
    *   **[[layers/3_host.md|Layer 3: Host Infrastructure]]**: Explains the `MCPHost` system for managing MCP server connections.


---
