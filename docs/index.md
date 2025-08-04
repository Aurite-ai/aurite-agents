---
hide:
  - title
  - toc
---

<div class="hero-banner">
  <div class="title-group">
    <img src="images/aurite_logo.png" alt="Aurite Logo" class="logo">
    <h1>Aurite Agents</h1>
  </div>
  <p class="subtitle">Build, Manage, and Deploy Sophisticated AI Agents.</p>
</div>
<div class="badges">
  <div class="badge-row">
    <img src="https://img.shields.io/badge/release-v0.1.0-blue" alt="Release">
    <img src="https://img.shields.io/badge/last%20commit-today-green" alt="Last Commit">
    <img src="https://img.shields.io/badge/issues-12%20open-orange" alt="Issues">
    <img src="https://img.shields.io/badge/build-passing-brightgreen" alt="Build">
    <img src="https://img.shields.io/badge/coverage-95%25-brightgreen" alt="Coverage">
  </div>
</div>

Welcome to the documentation site for the **Aurite Agent Framework**.

Aurite provides a comprehensive suite of tools and a flexible architecture to support the development of complex agentic applications, enabling interaction with various Language Models (LLMs) and external services through the Model Context Protocol (MCP).

!!! success "New to Aurite? Start Here!"

    Get up and running in minutes by following our **[Quick Start Guide](getting-started/quick_start.md)**.

---

## Documentation Sections

Navigate through the documentation using the tabs below to find what you need.

=== ":material-school: Getting Started"

    New to the framework? These guides will help you get started.

    - **[Quick Start](getting-started/quick_start.md)**: The fastest way to get Aurite running.
    - **[Tutorials Overview](getting-started/tutorials/Tutorials_Overview.md)**: A comprehensive learning section with concepts and assignments.
    - **[Package README](https://github.com/Aurite-ai/aurite-agents)**: Information specific to the pip-installable `aurite` package.

=== ":material-file-cog: Component Configurations"

    An in-depth look at the features each component offers through JSON/YAML configuration.

    - **[Projects and Workspaces](config/projects_and_workspaces.md)**: The foundation of your Aurite setup. **Start here!**
    - **[LLM Configs](config/llm.md)**: Configure language model providers.
    - **[MCP Server Configs](config/mcp_server.md)**: Connect tools and resources.
    - **[Agent Configs](config/agent.md)**: Define agent behaviors.
    - **[Linear Workflow Configs](config/linear_workflow.md)**: Create simple, sequential workflows.
    - **[Custom Workflow Configs](config/custom_workflow.md)**: Implement complex logic in Python.

=== ":material-console-line: Usage Guides"

    Learn how to interact with the framework.

    - **[CLI Reference](usage/cli_reference.md)**: Guide to using the Aurite command-line interface.
    - **[API Reference](usage/api_reference.md)**: Detailed documentation for the Python API.
    - **[TUI Guide](usage/tui_guide.md)**: Instructions for the text-based user interface.

=== ":material-sitemap: Framework Architecture"

    Dive deep into the framework's design and execution flow.

    - **[Framework Overview](architecture/overview.md)**: High-level architecture and design principles.
    - **Design Documents**:
        - [Aurite Engine Design](architecture/design/aurite_engine_design.md)
        - [Config Manager Design](architecture/design/config_manager_design.md)
        - [MCP Host Design](architecture/design/mcp_host_design.md)
    - **Execution & Flow**:
        - [Aurite Engine Execution Flow](architecture/flow/aurite_engine_execution_flow.md)
        - [Config Index Building Flow](architecture/flow/config_index_building_flow.md)
        - [MCP Server Registration Flow](architecture/flow/mcp_server_registration_flow.md)
        - [Session Management Flow](architecture/flow/session_management_flow.md)
