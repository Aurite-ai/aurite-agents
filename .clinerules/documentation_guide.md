# Aurite Framework Documentation Guide

## Purpose
This guide helps developers navigate the Aurite Framework documentation and ensures consistency when updating docs. It maps common tasks to relevant documents and provides a checklist for maintaining documentation accuracy as the codebase evolves.

## Documentation Overview

### Categories at a Glance
1. **Getting Started** - Installation, setup, and tutorials
2. **Copilot Rules** - Development workflows and guidelines
3. **Configuration Reference** - How to configure framework components
4. **Interfaces & Usage** - How to interact with the framework (API, CLI, TUI)
5. **Architecture & Design** - Technical architecture and design decisions
6. **Testing** - Test strategies and execution
7. **Internal Resources** - Implementation plans and external references

### 1. Getting Started
**Purpose:** Help new users install, configure, and learn the framework
**Audience:** New users, developers setting up the framework
**Location:** Root directory + `docs/getting-started/`
**Documents:**
- `README.md` - Framework overview and core concepts
- `README_packaged.md` - Package installation and `aurite init` usage
- `docs/getting-started/Learning_Path.md` - Overview and structured learning approach
- `docs/getting-started/Quick_Start.md` - 5-minute guide for experienced developers
- `docs/getting-started/installation_guides/package_installation_guide.md` - Detailed package setup
- `docs/getting-started/installation_guides/repository_installation_guide.md` - Development setup from source
- `docs/getting-started/tutorials/` - Sequential learning tutorials (01-08)
- `docs/getting-started/project_ideas/` - Practical project exercises

### 2. Copilot Rules
**Purpose:** Define development workflows, best practices, and guidelines for working with the codebase
**Audience:** Framework developers and contributors
**Location:** `.clinerules/`
**Documents:**
- `MUST_READ_FIRST.md` - Entry point and task router for all development work
- `documentation_guide.md` - This guide for navigating all documentation
- `development_rules.md` - Workflow and template for all development tasks.
  - `refactoring_rules.md` - Workflow and template for code improvements. Extension of development_rules.md
  - `debugging_rules.md` - Workflow and template for bug fixes. Extension of devlepment_rules.md

### 3. Configuration Reference
**Purpose:** Detailed guides for configuring each component type
**Audience:** Users configuring agents, workflows, and other components
**Location:** `docs/config/`
**Documents:**
- `projects_and_workspaces.md` - How the configuration system works
- `agent.md` - Agent configuration options
- `llm.md` - LLM provider configurations
- `mcp_server.md` - MCP server setup and configuration
- `simple_workflow.md` - Sequential workflow configuration
- `custom_workflow.md` - Python-based workflow configuration

### 4. Interfaces & Usage
**Purpose:** How to interact with the framework through various interfaces
**Audience:** Users and developers who need to run agents and workflows
**Location:** `docs/usage/`
**Documents:**
- `overview.md` - Comparison of interfaces and when to use each
- `cli_reference.md` - Complete CLI command reference
- `api_reference.md` - API usage guide and authentication
- `tui_guide.md` - Terminal UI interface guide
- `openapi.yaml` - OpenAPI specification
- API endpoints: `/api-docs`, `/redoc`, `/openapi.json` (when server is running)
- `routes/` - Detailed API route documentation
  - `config_manager_routes.md` - Configuration Manager API details, decision trees, and error handling

### 5. Architecture & Design
**Purpose:** Explain the framework's technical architecture and design decisions
**Audience:** Framework developers, advanced users
**Location:** `docs/architecture/`
**Documents:**
- `overview.md` - High-level architecture overview
- `layers/0_frontends.md` - Frontend layer (UI applications)
- `layers/1_entrypoints.md` - API, CLI, and worker entrypoints
- `layers/2_orchestration.md` - Core orchestration layer
- `layers/3_host.md` - MCP host infrastructure
- `design/` - Design documents and architectural decisions
- `config/` - Configuration system architecture
  - `index_building_flow.md` - How the configuration index is built with priority resolution

### 6. Testing
**Purpose:** Guide for running tests and understanding test strategies
**Audience:** Contributors and developers
**Location:** `tests/`
**Documents:**
- `tests/README.md` - Test execution guide and strategies

### 7. Internal Resources
**Purpose:** Internal references and implementation details
**Audience:** Framework maintainers
**Location:** `docs/internal/`
**Notes:**
- `plans/` - Implementation plans for features and refactors
- `reference/` - Documentation from external packages (textual, pyproject tools)
- Not included in open-source releases

### Documentation Assets
**Location:** `docs/images/`
**Purpose:** Diagrams, logos, and images used in documentation
**Key Files:**
- `architecture_diagram.svg` - Framework architecture visualization
- `aurite_logo.png` - Project branding

---

## Quick Reference Tables

### Finding Documentation by Task
| If you need to...           | Start here...                                        |
| --------------------------- | ---------------------------------------------------- |
| Install the framework       | `docs/getting-started/installation_guides/package_installation_guide.md` |
| Configure an agent          | `docs/config/agent.md`                               |
| Understand the architecture | `docs/architecture/overview.md`                      |
| Add a new API endpoint      | `docs/architecture/layers/1_entrypoints.md`          |
| Create a custom workflow    | `docs/config/custom_workflow.md`                     |
| Run tests                   | `tests/README.md`                                    |
| Learn framework basics      | `docs/getting-started/Learning_Path.md`              |
| Get started quickly         | `docs/getting-started/Quick_Start.md`                |
| Contribute to the project   | `.clinerules/MUST_READ_FIRST.md`                     |
| Develop a new feature       | `.clinerules/feature_development_rules.md`           |
| Fix a bug                   | `.clinerules/debugging_rules.md`                     |
| Refactor existing code      | `.clinerules/refactoring_rules.md`                   |
| Add or improve tests        | `.clinerules/testing_rules.md`                       |
| Update documentation        | `.clinerules/documentation_rules.md`                 |
| Use the CLI                 | `docs/usage/cli_reference.md`                        |
| Use the API                 | `docs/usage/api_reference.md`                        |
| Choose an interface         | `docs/usage/overview.md`                             |
| Understand projects/workspaces | `docs/config/projects_and_workspaces.md`         |

### Documentation Update Checklist
| If you changed...                 | Update these docs...                                 |
| --------------------------------- | ---------------------------------------------------- |
| Component configuration structure | Relevant `docs/config/*.md` file                     |
| Core architecture                 | `docs/architecture/` files                           |
| API endpoints                     | `docs/architecture/layers/1_entrypoints.md`, `openapi.yaml` |
| CLI commands                      | `docs/usage/cli_reference.md`                        |
| TUI interfaces                    | `docs/usage/tui_guide.md`                             |
| Installation process              | `docs/getting-started/installation_guides/*.md`      |
| Development workflow              | `.clinerules/MUST_READ_FIRST.md` and relevant task-specific rules |
| Test strategies                   | `tests/README.md`                                    |
