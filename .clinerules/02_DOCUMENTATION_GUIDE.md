# Aurite Framework Documentation Guide

## Purpose

This guide helps developers navigate the Aurite Framework documentation and ensures consistency when updating docs. It maps common tasks to relevant documents and provides a checklist for maintaining documentation accuracy as the codebase evolves.

## Documentation Overview

### Categories at a Glance

1. **Getting Started** - Installation, setup, and tutorials
2. **Copilot Rules** - Development workflows and guidelines
3. **Configuration Reference** - How to configure framework components
4. **Interfaces & Usage** - How to interact with the framework (API, CLI, TUI, Studio)
5. **Architecture & Design** - Technical architecture and design decisions
6. **Frontend** - Frontend client, examples, and usage
7. **Testing & Security** - Comprehensive testing and security framework
8. **Internal Resources** - Implementation plans and external references
9. **Copilot Guides** - Specialized guides for development and testing workflows

### 1. Getting Started

**Purpose:** Help new users install, configure, and learn the framework
**Audience:** New users, developers setting up the framework
**Location:** Root directory + `docs/getting-started/`
**Documents:**

- `README.md` - Framework overview and core concepts
- `CONTRIBUTORS.md` - List of project contributors
- `SECURITY.md` - Security policies and guidelines
- `claude.md` - Claude-specific documentation
- `mkdocs.yml` - MkDocs configuration for documentation site
- `docs/getting-started/quick_start.md` - Quick start guide for getting up and running
- `docs/getting-started/installation_guides/package_installation_guide.md` - Detailed package setup
- `docs/getting-started/installation_guides/repository_installation_guide.md` - Development setup from source
- `docs/getting-started/tutorials/` - Sequential learning tutorials (01-07)
  - `Tutorials_Overview.md` - Overview of all tutorials
  - `01_Introducing_Aurite_Agents.ipynb` - Introduction to agents
  - `02_Agents_and_Tools.ipynb` - Working with agents and tools
  - `03_Agent_Challenge.ipynb` - Agent challenge exercises
  - `04_Agent_Challenge_Solutions.ipynb` - Solutions to agent challenges
  - `05_LLMs_Schemas_and_Workflows.ipynb` - LLMs, schemas, and workflows
  - `06_Building_Your_Own_MCP_Server.md` - Creating custom MCP servers
  - `07_Understanding_Projects.md` - Understanding projects and workspaces
- `docs/0.3.28-migration-guide.md` - Migration guide for version 0.3.28

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
- `graph_workflow.md` - Graph-based workflow configuration
- `evaluation.md` - Evaluation component configuration

### 4. Interfaces & Usage

**Purpose:** How to interact with the framework through various interfaces
**Audience:** Users and developers who need to run agents and workflows
**Location:** `docs/usage/` + root directory
**Documents:**

- `cli_reference.md` - Complete CLI command reference
- `api_reference.md` - API usage guide and authentication
- `tui_guide.md` - Terminal UI interface guide
- `database_guide.md` - Database usage and configuration guide
- `openapi.yaml` - OpenAPI specification (root directory)
- API endpoints: `/api-docs`, `/redoc`, `/openapi.json` (when server is running)

### 5. Architecture & Design

**Purpose:** Explain the framework's technical architecture and design decisions
**Audience:** Framework developers, advanced users
**Location:** `docs/architecture/`
**Documents:**

- `overview.md` - High-level framework architecture and component integration
- `design/` - Component design documents and architectural decisions
  - `aurite_engine_design.md` - AuriteEngine architecture, JIT server registration, session management
  - `config_manager_design.md` - ConfigManager hierarchical configuration system
  - `mcp_host_design.md` - MCP Host distributed tool management and security
- `flow/` - Operational flow documentation
  - `aurite_engine_execution_flow.md` - Agent and workflow execution flows
  - `config_index_building_flow.md` - Configuration discovery and indexing process
  - `mcp_server_registration_flow.md` - MCP server registration and component discovery
  - `session_management_flow.md` - Session lifecycle and storage operations

### 6. Frontend

**Purpose:** Documentation for the TypeScript/JavaScript frontend client and examples
**Audience:** Frontend developers, users of the API client
**Location:** `frontend/`
**Documents:**

- `frontend/README.md` - Overview of the frontend monorepo, setup, and architecture
- `frontend/packages/api-client/README.md` - TypeScript API client library documentation
- `frontend/packages/api-client/examples/README.md` - Detailed guide to API client examples
- `frontend/packages/aurite-studio/README.md` - React-based web UI documentation

### 7. Testing & Security

**Purpose:** Comprehensive testing and security framework documentation (Kahuna Testing & Security Framework)
**Audience:** Developers writing tests, security engineers, and administrators
**Location:** `docs/testing/` + `tests/` + root directory
**Documents:**

- `SECURITY.md` - Security policies and vulnerability reporting
- `docs/testing/README.md` - Kahuna Testing & Security Framework overview
- `docs/testing/architecture/` - Testing architecture and patterns
  - `compositional_testing.md` - Compositional testing approach
  - `test_inheritance.md` - Test inheritance patterns
  - `testing_architecture.md` - Overall testing architecture
  - `testing_hierarchy.md` - Test hierarchy and organization
- `docs/testing/components/` - Component-specific testing and security
  - `llm/README.md` - LLM testing overview
  - `llm/quality_tests.md` - Quality test specifications
  - `llm/security_tests.md` - Security test specifications
  - Additional component folders for MCP servers, agents, and workflows
- `docs/testing/guides/` - Practical testing guides
- `docs/testing/user_security/` - User access and RBAC documentation
- `tests/README.md` - Test suite documentation and running instructions

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
- `aurite-agents-llm-full.md` - Comprehensive LLM integration guide

---

## Quick Reference Tables

### Finding Documentation by Task

| If you need to...              | Start here...                                                            |
| ------------------------------ | ------------------------------------------------------------------------ |
| Install the framework          | `docs/getting-started/installation_guides/package_installation_guide.md` |
| Configure an agent             | `docs/config/agent.md`                                                   |
| Understand the architecture    | `docs/architecture/overview.md`                                          |
| Add a new API endpoint         | `src/aurite/bin/api/routes/`                                             |
| Create a custom workflow       | `docs/config/custom_workflow.md`                                         |
| Create a graph workflow        | `docs/config/graph_workflow.md`                                          |
| Run tests                      | `tests/README.md`                                                        |
| Learn framework basics         | `docs/getting-started/tutorials/`                                        |
| Get started quickly            | `docs/getting-started/quick_start.md`                                    |
| Contribute to the project      | `.clinerules/00_START_HERE.md`                                           |
| Develop a new feature          | `.clinerules/01_DEVELOPMENT_RULES.md`                                    |
| Fix a bug                      | `.clinerules/DEBUGGING_RULES.md`                                         |
| Refactor existing code         | `.clinerules/REFACTORING_RULES.md`                                       |
| Add or improve tests           | `docs/testing/README.md`                                                 |
| Update documentation           | `.clinerules/02_DOCUMENTATION_GUIDE.md`                                  |
| Use the CLI                    | `docs/usage/cli_reference.md`                                            |
| Use the API                    | `docs/usage/api_reference.md`                                            |
| Use the TUI                    | `docs/usage/tui_guide.md`                                                |
| Use the database               | `docs/usage/database_guide.md`                                           |
| Use the frontend client        | `frontend/README.md`                                                     |
| Run frontend examples          | `frontend/packages/api-client/examples/README.md`                        |
| Use Aurite Studio              | `frontend/packages/aurite-studio/README.md`                              |
| Choose an interface            | `docs/usage/api_reference.md`                                            |
| Understand projects/workspaces | `docs/config/projects_and_workspaces.md`                                 |
| Configure evaluation           | `docs/config/evaluation.md`                                              |
| Test LLM components            | `docs/testing/components/llm/README.md`                                  |
| Implement security             | `SECURITY.md`                                                            |

### Documentation Update Checklist

| If you changed...                 | Update these docs...                                            |
| --------------------------------- | --------------------------------------------------------------- |
| Component configuration structure | Relevant `docs/config/*.md` file                                |
| Core architecture                 | `docs/architecture/` files                                      |
| API endpoints                     | `src/aurite/bin/api/routes/`, `openapi.yaml`                    |
| CLI commands                      | `docs/usage/cli_reference.md`                                   |
| TUI interfaces                    | `docs/usage/tui_guide.md`                                       |
| Installation process              | `docs/getting-started/installation_guides/*.md`                 |
| Development workflow              | `.clinerules/00_START_HERE.md` and relevant task-specific rules |
| Test strategies                   | `docs/testing/README.md`                                        |
