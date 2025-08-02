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
7. **Frontend** - Frontend client, examples, and usage
8. **Internal Resources** - Implementation plans and external references

### 1. Getting Started

**Purpose:** Help new users install, configure, and learn the framework
**Audience:** New users, developers setting up the framework
**Location:** Root directory + `docs/getting-started/`
**Documents:**

- `README.md` - Framework overview and core concepts
- `README_packaged.md` - Package installation and `aurite init` usage
- `docs/getting-started/Start_Here.md` - Entry point for new users
- `docs/getting-started/installation_guides/package_installation_guide.md` - Detailed package setup
- `docs/getting-started/installation_guides/repository_installation_guide.md` - Development setup from source
- `docs/getting-started/tutorials/` - Sequential learning tutorials (01-08)
  - `Tutorials_Overview.md` - Overview of all tutorials
  - `01_Introducing_Aurite_Agents.ipynb` through `07_Understanding_Projects.md`
- `docs/getting-started/project_ideas/` - Practical project exercises
  - `Project_Ideas_Overview.md` - Overview of project ideas
  - `Project_Ideas_Customer_Support.md` - Customer support project examples
  - `Project_Ideas_Data_Processing.md` - Data processing project examples

### 2. Copilot Rules

**Purpose:** Define development workflows, best practices, and guidelines for working with the codebase
**Audience:** Framework developers and contributors
**Location:** `.clinerules/`

**File Organization System:**

- **Numbered files (00-02):** Core rules read by copilots for most development tasks
- **Non-numbered files:** Specialized rules read only for specific task types

**Documents:**

**Core Rules (Always Read):**

- `00_START_HERE.md` - Entry point and task router for all development work
- `01_DEVELOPMENT_RULES.md` - Workflow and template for all development tasks
- `02_DOCUMENTATION_GUIDE.md` - This guide for navigating all documentation

**Specialized Rules (Read When Needed):**

- `CODING_STANDARD.md` - Aurite Framework coding standard with 3-layer architecture rules
- `REFACTORING_RULES.md` - Workflow and template for code improvements (extension of 01_DEVELOPMENT_RULES.md)
- `DEBUGGING_RULES.md` - Workflow and template for bug fixes (extension of 01_DEVELOPMENT_RULES.md)

### 3. Configuration Reference

**Purpose:** Detailed guides for configuring each component type
**Audience:** Users configuring agents, workflows, and other components
**Location:** `docs/config/`
**Documents:**

- `projects_and_workspaces.md` - How the configuration system works
- `agent.md` - Agent configuration options
- `llm.md` - LLM provider configurations
- `mcp_server.md` - MCP server setup and configuration
- `linear_workflow.md` - Sequential workflow configuration
- `custom_workflow.md` - Python-based workflow configuration

### 4. Interfaces & Usage

**Purpose:** How to interact with the framework through various interfaces
**Audience:** Users and developers who need to run agents and workflows
**Location:** `docs/usage/` + root directory
**Documents:**

- `cli_reference.md` - Complete CLI command reference
- `api_reference.md` - API usage guide and authentication
- `tui_guide.md` - Terminal UI interface guide
- `openapi.yaml` - OpenAPI specification (root directory)
- API endpoints: `/api-docs`, `/redoc`, `/openapi.json` (when server is running)
- `routes/` - Detailed API route documentation
  - `config_manager_routes.md` - Configuration Manager API details, decision trees, and error handling
  - `facade_routes.md` - Execution Facade API details
  - `mcp_host_routes.md` - MCP Host API details
  - `system_routes.md` - System API details

### 5. Architecture & Design

**Purpose:** Explain the framework's technical architecture and design decisions
**Audience:** Framework developers, advanced users
**Location:** `docs/architecture/`
**Documents:**

- `overview.md` - High-level architecture overview
- `layers/` - Layer-by-layer architecture documentation
  - `1_entrypoints.md` - API, CLI, and worker entrypoints
  - `2_orchestration.md` - Core orchestration layer
  - `2.5_execution.md` - Execution layer details
  - `3_host.md` - MCP host infrastructure
- `design/` - Design documents and architectural decisions
  - `execution_facade.md` - ExecutionFacade architecture, JIT server registration, session management
  - `index_building_flow.md` - How the configuration index is built with priority resolution
  - `packaging_and_runtime_design.md` - Package structure and runtime design decisions

### 6. Testing

**Purpose:** Guide for running tests and understanding test strategies
**Audience:** Contributors and developers
**Location:** `tests/` + `docs/testing/`
**Documents:**

- `tests/README.md` - Test execution guide and strategies
- `docs/testing/api_test_coverage_connections.md` - API test coverage analysis
- `docs/testing/api_test_coverage_visual.md` - Visual test coverage documentation

### 7. Frontend

**Purpose:** Documentation for the TypeScript/JavaScript frontend client and examples
**Audience:** Frontend developers, users of the API client
**Location:** `frontend/`
**Documents:**

- `frontend/README.md` - Overview of the frontend monorepo, setup, and architecture
- `frontend/packages/api-client/README.md` - TypeScript API client library documentation
- `frontend/packages/api-client/examples/README.md` - Detailed guide to API client examples
- `frontend/packages/aurite-studio/README.md` - React-based web UI documentation

### 8. Internal Resources

**Purpose:** Internal references and implementation details
**Audience:** Framework maintainers
**Location:** `docs/internal/`
**Documents:**

- `plans/refactoring/` - Refactoring implementation plans
  - Various dated refactoring plans (e.g., `07-29_cache_manager_simplification.md`)
    **Notes:**
- Not included in open-source releases

### 9. Copilot Guides

**Purpose:** Specialized guides for development and testing workflows
**Audience:** Framework developers using AI copilots
**Location:** `docs/copilot_guides/`
**Documents:**

- `mcp_server_testing_guide.md` - Guide for testing MCP server implementations

### 10. Documentation Assets

**Purpose:** Diagrams, logos, stylesheets, and images used in documentation
**Location:** `docs/images/` + `docs/assets/`
**Documents:**

- `docs/images/architecture_diagram.svg` - Framework architecture visualization
- `docs/images/aurite_logo.png` - Project branding
- `docs/assets/stylesheets/extra.css` - Custom documentation styling
- `docs/index.md` - Documentation index/landing page

---

## Quick Reference Tables

### Finding Documentation by Task

| If you need to...              | Start here...                                                            |
| ------------------------------ | ------------------------------------------------------------------------ |
| Install the framework          | `docs/getting-started/installation_guides/package_installation_guide.md` |
| Configure an agent             | `docs/config/agent.md`                                                   |
| Understand the architecture    | `docs/architecture/overview.md`                                          |
| Add a new API endpoint         | `docs/architecture/layers/1_entrypoints.md`                              |
| Create a custom workflow       | `docs/config/custom_workflow.md`                                         |
| Run tests                      | `tests/README.md`                                                        |
| Learn framework basics         | `docs/getting-started/Start_Here.md`                                     |
| Get started quickly            | `docs/getting-started/Start_Here.md`                                     |
| Contribute to the project      | `.clinerules/00_START_HERE.md`                                           |
| Develop a new feature          | `.clinerules/01_DEVELOPMENT_RULES.md`                                    |
| Fix a bug                      | `.clinerules/DEBUGGING_RULES.md`                                         |
| Refactor existing code         | `.clinerules/REFACTORING_RULES.md`                                       |
| Add or improve tests           | `tests/README.md`                                                        |
| Update documentation           | `.clinerules/02_DOCUMENTATION_GUIDE.md`                                  |
| Use the CLI                    | `docs/usage/cli_reference.md`                                            |
| Use the API                    | `docs/usage/api_reference.md`                                            |
| Use the frontend client        | `frontend/README.md`                                                     |
| Run frontend examples          | `frontend/packages/api-client/examples/README.md`                        |
| Choose an interface            | `docs/usage/api_reference.md`                                            |
| Understand projects/workspaces | `docs/config/projects_and_workspaces.md`                                 |

### Documentation Update Checklist

| If you changed...                 | Update these docs...                                            |
| --------------------------------- | --------------------------------------------------------------- |
| Component configuration structure | Relevant `docs/config/*.md` file                                |
| Core architecture                 | `docs/architecture/` files                                      |
| API endpoints                     | `docs/architecture/layers/1_entrypoints.md`, `openapi.yaml`     |
| CLI commands                      | `docs/usage/cli_reference.md`                                   |
| TUI interfaces                    | `docs/usage/tui_guide.md`                                       |
| Installation process              | `docs/getting-started/installation_guides/*.md`                 |
| Development workflow              | `.clinerules/00_START_HERE.md` and relevant task-specific rules |
| Test strategies                   | `tests/README.md`                                               |
