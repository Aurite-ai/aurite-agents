# ✨ Aurite Agents Framework

<p align="center">
  <img src="https://raw.githubusercontent.com/Aurite-ai/aurite-agents/main/docs/images/aurite_logo.png" alt="Aurite Logo" width="200"/>
</p>

<p align="center">
  <strong>A Python framework for building, testing, and running AI agents.</strong>
</p>

---

**Aurite Agents** is a powerful, configuration-driven framework designed for building and orchestrating sophisticated AI agents. It enables agents to interact with a variety of external tools, prompts, and resources through the Model Context Protocol (MCP), allowing them to perform complex, multi-step tasks.

Whether you're creating advanced AI assistants, automating processes, or experimenting with agentic workflows, Aurite provides the modular building blocks and robust infrastructure you need.

## Key Features

- **Hierarchical Configuration:** Organize your components with a powerful **Workspace -> Project** system that allows for shared configurations and clear separation of concerns.
- **Declarative Components:** Define agents, LLMs, tools, and workflows in simple JSON or YAML files.
- **Interactive CLI & TUIs:** A rich command-line interface (`aurite`) and two built-in Textual User Interfaces (TUIs) for interactive chat and configuration editing.
- **Extensible Tooling:** Connect to any tool or service using the **Model Context Protocol (MCP)**, with built-in support for local and remote servers.
- **Flexible Orchestration:** Chain agents together in `linear_workflows` for sequential tasks or write custom Python logic in `custom_workflows` for complex orchestration.
- **REST API:** A comprehensive FastAPI server that exposes all framework functionality for programmatic access and UI development.

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

For a complete walkthrough, see the [**Package Installation Guide**](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/getting-started/installation_guides/package_installation_guide.md).

Developers who wish to contribute to the framework should follow the [**Repository Installation Guide**](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/getting-started/installation_guides/repository_installation_guide.md).

## Core Concepts

### 1. Workspaces & Projects

Aurite uses a hierarchical system to organize your work, defined by a special `.aurite` file.

- **Workspace:** A top-level container that can manage multiple projects and share common configurations (e.g., a standard set of LLMs).
- **Project:** A self-contained directory holding all the configurations for a specific application or task.

This structure allows for clean separation and promotes reusable components. Learn more in the [**Projects and Workspaces Guide**](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/projects_and_workspaces.md).

### 2. Components

Your application is built by defining and combining different types of components in `.json` or `.yaml` files.

- **[Agents](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/agent.md):** The core actors, powered by an LLM and capable of using tools.
- **[LLMs](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/llm.md):** Configurations for different language models (e.g., GPT-4, Claude 3).
- **[MCP Servers](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/mcp_server.md):** Connections to external tools and resources.
- **[Linear Workflows](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/linear_workflow.md):** A sequence of agents to be executed in order.
- **[Custom Workflows](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/custom_workflow.md):** Complex orchestration logic defined in your own Python code.

### 3. Interfaces

Aurite provides multiple ways to interact with the framework:

- [**Web Interface (Aurite Studio)**](https://github.com/Aurite-ai/aurite-agents/tree/main/frontend/packages/aurite-studio): Modern React web application for visual agent management, workflow design, and real-time execution monitoring.
- [**TypeScript/JavaScript API**](https://github.com/Aurite-ai/aurite-agents/tree/main/frontend/packages/api-client): Production-ready API client for building web applications and integrations with full type safety and streaming support.
- [**Command-Line Interface (CLI)**](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/usage/cli_reference.md): The primary tool for managing your projects. Use it to `init`, `list`, `show`, `run`, and `edit` your components.
- [**Textual User Interfaces (TUIs)**](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/usage/tui_guide.md): Rich, in-terminal applications for interactive chat with agents (`aurite run <agent_name>`) and live configuration editing (`aurite edit`).
- [**REST API**](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/usage/api_reference.md): A complete FastAPI server (`aurite api`) that exposes all framework functionality for UIs and programmatic control.

## Frontend Framework

Aurite includes a comprehensive **TypeScript/JavaScript frontend ecosystem** that provides both programmatic access and visual interfaces for the Python framework.

### Frontend Packages

- **[@aurite/api-client](https://github.com/Aurite-ai/aurite-agents/tree/main/frontend/packages/api-client)** - Production-ready TypeScript client library with full type safety, retry logic, and streaming support for all framework APIs.
- **[@aurite/aurite-studio](https://github.com/Aurite-ai/aurite-agents/tree/main/frontend/packages/aurite-studio)** - Modern React web interface providing visual management and execution of agents, workflows, and configurations.

### Key Frontend Features

- 🔒 **Type Safety**: Full TypeScript support with comprehensive type definitions
- 🔄 **Real-time Streaming**: Live agent responses and execution monitoring
- 🎨 **Modern UI**: Intuitive React interface with responsive design
- 🧪 **Production Ready**: Extensive testing, error handling, and deployment tools
- 📖 **Rich Examples**: Comprehensive examples and integration guides

For complete setup instructions, examples, and API documentation, see the [**Frontend Documentation**](https://github.com/Aurite-ai/aurite-agents/blob/main/frontend/README.md).

## Architecture Overview

The framework is built on a layered architecture that separates concerns from the user-facing entrypoints down to the external tool connections.

![Aurite Architecture](https://raw.githubusercontent.com/Aurite-ai/aurite-agents/main/docs/images/architecture_diagram.svg)

For a deep dive into the framework's design, see the [**Architecture Overview**](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/architecture/overview.md).

## Documentation

- **Getting Started**
  - [Package Installation](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/getting-started/installation_guides/package_installation_guide.md)
  - [Repository Installation](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/getting-started/installation_guides/repository_installation_guide.md)
  - [Tutorials](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/getting-started/tutorials/Tutorials_Overview.md)
- **Frontend**
  - [Frontend Overview](https://github.com/Aurite-ai/aurite-agents/blob/main/frontend/README.md)
  - [API Client Documentation](https://github.com/Aurite-ai/aurite-agents/blob/main/frontend/packages/api-client/README.md)
  - [Aurite Studio Guide](https://github.com/Aurite-ai/aurite-agents/blob/main/frontend/packages/aurite-studio/README.md)
- **Usage Guides**
  - [CLI Reference](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/usage/cli_reference.md)
  - [TUI Guide](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/usage/tui_guide.md)
  - [API Reference](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/usage/api_reference.md)
- **Configuration**
  - [Projects and Workspaces](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/projects_and_workspaces.md)
  - [Agent Config](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/agent.md)
  - [LLM Config](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/llm.md)
  - [MCP Server Config](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/mcp_server.md)
  - [Linear Workflow Config](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/linear_workflow.md)
  - [Custom Workflow Config](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/config/custom_workflow.md)
- **Architecture**
  - [Architecture Overview](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/architecture/overview.md)

## ⭐ Star this Repository!

**Found Aurite Agent Framework useful?** Give us a star! ⭐

Your support helps us:

- 🚀 **Prioritize new features** based on community interest
- 📈 **Attract more contributors** to accelerate development
- 🎯 **Focus our roadmap** on what matters most to developers
- 🌟 **Build a thriving ecosystem** around AI agent development

**Join us** in building the future of AI agents & workflows with Aurite!

### Join Our Community

- 🐛 **Report Issues**: Found a bug? [Open an issue](https://github.com/Aurite-ai/aurite-agents/issues)
- 💡 **Feature Requests**: Have an idea? [Start a discussion](https://github.com/Aurite-ai/aurite-agents/discussions)
- 🤝 **Contribute**: Check our Contributing Guidelines below
- 📧 **Contact**: Reach out at hello@aurite.ai

## 📄 Citation

If you use Aurite Agents in your research or projects, please cite:

### BibTeX

```bibtex
@software{aurite_agents_2025,
  title={Aurite Agents Framework: A Python Framework for Building and Orchestrating AI Agents},
  author={Ryan W and Blake R and Jiten Oswal},
  year={2025},
  version={0.3.28},
  publisher={GitHub},
  url={https://github.com/Aurite-ai/aurite-agents},
  note={Configuration-driven AI agent framework with MCP integration and multi-LLM support},
  keywords={artificial intelligence, agents, python, framework, MCP, multi-LLM},
  abstract={A configuration-driven AI agent framework with Model Context Protocol (MCP) integration and multi-LLM support for building and orchestrating intelligent agents},
  license={MIT}
}
```

## 🔗 Related Work & Ecosystem

### Built With

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) - Tool integration standard
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for APIs
- [Textual](https://textual.textualize.io/) - Rich terminal user interfaces
- [Pydantic](https://pydantic.dev/) - Data validation and settings management

### Integrations

- **LLM Providers**: OpenAI, Anthropic, Google, and more via LiteLLM
- **Tools**: Any MCP-compatible server or custom Python tools
- **Deployment**: Docker, cloud platforms, local development

### Community Projects

- [MCP Servers Registry](https://github.com/modelcontextprotocol/servers) - Official MCP tools
- [Aurite Community Examples](https://github.com/Aurite-ai/aurite-agents/tree/main/demo-config) - Templates and examples

## Contributing

<!-- Test comment for changelog workflow integration testing -->
<!-- Second test comment to validate changelog workflow is working correctly -->

Contributions are welcome! Please follow standard fork/pull request workflows. Ensure tests pass and documentation is updated for any changes.
