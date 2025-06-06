# Aurite Agents Documentation Guide

## 1. Introduction

This guide is designed to help navigate the documentation of the Aurite Agents framework. It maps common development tasks to the most relevant documents and provides a checklist for which documents to update when changes are made to the codebase. Its purpose is to ensure consistency and accuracy across the documentation as the framework evolves.

## 2. Document Map

This table provides a high-level overview of the key documents, their purpose, and their primary audience.

| Document Path                               | Purpose                                                                                             | Primary Audience      |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------- | --------------------- |
| `README.md`                                 | High-level overview of the framework, core concepts, and architecture for repository users.         | Developers, Newcomers |
| `README_packaged.md`                        | Information for users who have installed the `aurite` package via pip. Focuses on `aurite init`.      | End-Users             |
| `frontend/README.md`                        | Technical details of the frontend application (stack, structure, setup).                            | Frontend Developers   |
| `docs/package_installation_guide.md`        | Step-by-step guide for end-users to install the package and set up a project.                       | End-Users             |
| `docs/repository_installation_guide.md`     | Guide for developers setting up the project from the source code repository.                        | Developers            |
| `docs/layers/framework_overview.md`         | The primary architectural document, explaining all layers and their interactions.                   | Framework Developers  |
| `docs/layers/0_frontends.md`                | Deep dive into the frontend layer, its files, and its interaction with the backend API.             | Frontend Developers   |
| `docs/layers/1_entrypoints.md`              | Deep dive into the API, CLI, and Worker entrypoints.                                                | Backend Developers    |
| `docs/layers/2_orchestration.md`            | Deep dive into `HostManager`, `ExecutionFacade`, and component executors.                           | Backend Developers    |
| `docs/layers/3_host.md`                     | Deep dive into `MCPHost` and its interaction with external MCP servers.                             | Backend Developers    |
| `docs/components/PROJECT.md`                | Explains the central project configuration file (`aurite_config.json`) and how it works.            | End-Users, Developers |
| `docs/components/*.md`                      | Detailed guides for configuring each component type (Agent, Client, LLM, etc.).                     | End-Users, Developers |
| `docs/HOME.md`                              | The main landing page for the Obsidian Publish documentation site.                                  | All                   |
| `docs/USC - Get Started/Start Here.md`      | The entry point for the USC tutorial modules.                                                       | Newcomers, Students   |
| `docs/USC - Get Started/module1/*.md`       | Tutorial content for learning basic framework concepts and agent configuration.                     | Newcomers, Students   |
| `docs/USC - Get Started/module2/*.md`       | Tutorial content for learning about the Model Context Protocol (MCP) and using the CLI.             | Newcomers, Students   |

---

## 3. Part 1: Task-Based Document Reference

Use this section to find the most relevant documents to consult *before* starting a specific task.

| If your task is to...                                       | Start by reading these documents...                                                                                                                             |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Change a user-facing configuration** (e.g., an Agent's prompt, a Workflow's steps, an LLM's temperature) | 1. `docs/components/PROJECT.md` (to understand how components are referenced) <br> 2. The specific component document (e.g., `docs/components/agent.md`, `docs/components/simple_workflow.md`) |
| **Add or change an API endpoint**                               | 1. `docs/layers/1_entrypoints.md` (to understand the API structure, routers, and dependencies) <br> 2. `docs/layers/framework_overview.md` (for context on how the API fits in) |
| **Modify the core orchestration logic** (e.g., how agents are executed, how history is managed) | 1. `docs/layers/2_orchestration.md` (the primary document for this layer) <br> 2. `docs/layers/framework_overview.md` (for high-level context) <br> 3. `docs/layers/3_host.md` (to understand the `MCPHost` interface it calls) |
| **Modify the low-level MCP interaction** (e.g., how clients connect, how tools are filtered) | 1. `docs/layers/3_host.md` (the primary document for this layer) <br> 2. `docs/layers/framework_overview.md` (for high-level context) |
| **Modify the Frontend UI**                                      | 1. `frontend/README.md` (for tech stack, project structure, and setup) <br> 2. `docs/layers/0_frontends.md` (for how the frontend interacts with the backend API) |
| **Change the packaged user experience** (e.g., the `aurite init` command or the default project template) | 1. `README_packaged.md` (describes the user experience) <br> 2. `docs/package_installation_guide.md` (details the user setup flow) |
| **Add a new component type** (e.g., a new kind of workflow)     | 1. `docs/layers/framework_overview.md` (to decide where it fits) <br> 2. `docs/layers/2_orchestration.md` (likely where new execution logic would go) <br> 3. `docs/components/PROJECT.md` (to understand how it would be configured) |

---

## 4. Part 2: Document Update Cheatsheet

After making changes to the codebase, use this section to identify which documents **must be reviewed and updated**.

| If you changed...                                                                                                                                                                                                                                                                            | Documents to Review/Update                                                                                                                                                                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **The structure of a component's JSON config** (e.g., adding a new field to `AgentConfig` in `src/aurite/config/config_models.py`) | 1. The relevant component document (e.g., `docs/components/agent.md`) - **MUST be updated** with the new field. <br> 2. `docs/components/PROJECT.md` (if the change affects inline definitions). <br> 3. `README.md` (if the concept is mentioned there). |
| **The core behavior of `HostManager` or `ExecutionFacade`** (in `src/aurite/host_manager.py` or `src/aurite/execution/facade.py`) | 1. `docs/layers/2_orchestration.md` - **MUST be updated**. <br> 2. `docs/layers/framework_overview.md` - Review for high-level impact. |
| **The core behavior of `MCPHost` or its managers** (in `src/aurite/host/`) | 1. `docs/layers/3_host.md` - **MUST be updated**. <br> 2. `docs/layers/framework_overview.md` - Review for high-level impact. |
| **An API route's signature or behavior** (in `src/aurite/bin/api/routes/`) | 1. `docs/layers/1_entrypoints.md` - **MUST be updated**. <br> 2. `docs/layers/0_frontends.md` (if the frontend consumes this endpoint). |
| **The frontend application** (in `frontend/src/`) | 1. `frontend/README.md` (if structure or setup changes). <br> 2. `docs/layers/0_frontends.md` (if the core interaction flow with the backend changes). |
| **The `aurite init` command or its templates** | 1. `README_packaged.md` - **MUST be updated**. <br> 2. `docs/package_installation_guide.md` - **MUST be updated**. |
| **High-level architecture or adding a new layer/major component** | 1. `docs/layers/framework_overview.md` - **MUST be updated**. <br> 2. `README.md` (especially the architecture diagram/description). <br> 3. A new layer document (`docs/layers/X_new_layer.md`) will likely be needed. |
