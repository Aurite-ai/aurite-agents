# MCP Host System - Technical Implementation Specification

**Version:** 0.1
**Date:** 2025-04-05

## 1. Overview

This document details the technical implementation of the `aurite-mcp` Host system (`src/host/`), based on the code review conducted in Phase 2 of the overarching development plan. It aims to provide a clear understanding of the current state, serving as a baseline for discussion and potential improvements.

The Host system orchestrates communication between AI agents/workflows and various MCP tool servers. It follows a layered architecture as outlined in `docs/architecture_overview.md`.

## 2. Core Class: `MCPHost` (`src/host/host.py`)

The `MCPHost` class is the central orchestrator.

*   **Initialization:**
    *   Takes a `HostConfig` object (defined in `src/host/config.py`) and an optional `encryption_key` (passed to `SecurityManager`).
    *   Instantiates all manager classes for each layer.
    *   The `initialize()` method calls the `initialize()` method of each manager sequentially, respecting layer order (Foundation -> Communication -> Resource Management -> Agent).
    *   Initializes client connections based on the `HostConfig.clients` list, registering roots, capabilities, tools, prompts, and resources with the relevant managers.
    *   Conditionally initializes a dedicated "memory" client (`mem0_server.py`) based on the `HostConfig.enable_memory` flag.
*   **Dependencies:** Uses an `AsyncExitStack` to manage the lifecycle of client sessions created via `stdio_client`.
*   **Service Access:** Exposes managers from the Resource Management and Agent layers (Prompts, Resources, Storage, Tools, Workflows) as public properties (e.g., `host.tools`, `host.workflows`).
*   **Core Functionality:** Provides high-level methods like `prepare_prompt_with_tools`, `execute_prompt_with_tools`, `register_workflow`, `execute_workflow`, `add_memories`, `search_memories` which delegate tasks to the appropriate managers.
*   **Shutdown:** The `shutdown()` method calls the `shutdown()` method of each manager in reverse layer order and closes client connections via the `AsyncExitStack`.

## 3. Layered Architecture Implementation

### 3.1. Layer 1: Foundation

*   **`RootManager` (`src/host/foundation/roots.py`)**
    *   **Purpose:** Manages MCP roots (resource URI boundaries) associated with clients.
    *   **Implementation:** Stores `client_id` -> `List[RootConfig]` mapping. Validates and normalizes URIs upon registration. Provides `validate_access` method used by `ToolManager` and `ResourceManager` to check if a required URI is within a client's allowed roots.
    *   **Notes:** Defines its own `RootConfig` dataclass, potentially redundant with `src/host/config.py`. Assumes unrestricted access if no roots are registered for a client.
*   **`SecurityManager` (`src/host/foundation/security.py`)**
    *   **Purpose:** Handles encryption, credential storage, access tokens, and permissions.
    *   **Implementation:** Uses `cryptography.fernet` for symmetric encryption. Derives key from `AURITE_MCP_ENCRYPTION_KEY` env var or generates one. Stores encrypted credentials in an *in-memory* dictionary (`_credentials`). Creates temporary access tokens (`_access_tokens`) mapped to credential IDs. Manages server permissions (`_server_permissions`) mapping `server_id` to allowed credential *types*. Provides masking for sensitive data.
    *   **Notes:** In-memory storage is not suitable for production secrets.

### 3.2. Layer 2: Communication

*   **`TransportManager` (`src/host/communication/transport.py`)**
    *   **Purpose:** Manages the creation and lifecycle of transport connections to MCP servers.
    *   **Implementation:** Currently supports `STDIO` transport using `mcp.client.stdio.stdio_client`. Holds references to active transport objects. Has placeholders for `SSE`.
    *   **Notes:** Seems underutilized currently, as `host.py` directly uses `stdio_client` within its `_initialize_client` method via the `AsyncExitStack`. The manager itself doesn't appear to be directly used for creating the main client transports in the current `host.py` flow.
*   **`MessageRouter` (`src/host/communication/routing.py`)**
    *   **Purpose:** Maps tools and prompts to the clients/servers that provide them. Selects servers for tool execution.
    *   **Implementation:** Maintains dictionaries mapping `tool_name` -> `client_id` and `prompt_name` -> `client_id`. Stores server capabilities and routing weights. `select_server_for_tool` method uses weights primarily to distinguish primary (weight=1.0) vs. backup (weight<1.0) servers.
    *   **Notes:** Routing logic based on weight seems basic currently.

### 3.3. Layer 3: Resource Management

*   **`PromptManager` (`src/host/resources/prompts.py`)**
    *   **Purpose:** Manages system prompts provided by clients.
    *   **Implementation:** Registers prompts per client. Includes helper methods to convert various data formats into standard `mcp.types.Prompt` and `mcp.types.GetPromptResult`. Validates arguments against prompt definitions.
    *   **Notes:** Defines an unused `PromptConfig` dataclass.
*   **`ResourceManager` (`src/host/resources/resources.py`)**
    *   **Purpose:** Manages MCP resources (data identified by URIs) provided by clients.
    *   **Implementation:** Registers resources per client. Provides `validate_resource_access` which uses `RootManager` to enforce boundaries. Includes subscription methods (publish/subscribe mechanism not fully implemented).
    *   **Notes:** Defines an unused `ResourceConfig` dataclass.
*   **`StorageManager` (`src/host/resources/storage.py`)**
    *   **Purpose:** Manages SQL database connections using SQLAlchemy.
    *   **Implementation:** Creates/manages SQLAlchemy `Engine` objects based on parameters or named configurations (`config/storage/connections.json`). Provides `execute_query` method. Manages server permissions based on allowed *database types* (e.g., 'postgresql'). Loads named connection configs and retrieves credentials from environment variables specified in the config.
    *   **Notes:** Tightly coupled to SQLAlchemy. Permission model is type-based, not instance-based.
*   **`ToolManager` (`src/host/resources/tools.py`)**
    *   **Purpose:** Central hub for tool registration, discovery, execution, and formatting for LLMs.
    *   **Implementation:** Takes `RootManager` and `MessageRouter` as dependencies. Registers tools discovered from clients. Orchestrates `execute_tool` by selecting a server via `MessageRouter`, validating access via `RootManager`, and calling the tool on the client session. Provides specific formatting methods (`format_tools_for_llm`, `create_tool_result_blocks`) for LLM interaction.
    *   **Notes:** Core component bridging the host infrastructure and agent capabilities.

### 3.4. Layer 4: Agent

*   **`WorkflowManager` (`src/host/agent/workflows.py`)**
    *   **Purpose:** Manages the registration, execution, and lifecycle of `BaseWorkflow` instances.
    *   **Implementation:** Takes the `MCPHost` instance as a dependency, allowing workflows to access host services. Can dynamically register a client specified by a workflow's `ClientConfig`, modifying the host's configuration and triggering client initialization via the host instance. Executes workflows and manages their lifecycle.
    *   **Notes:** The dynamic client registration mechanism involves a higher layer (Agent) modifying the configuration/state managed by the core Host, which might be an area to review for potential complexity or unexpected side effects.

## 4. Configuration (`src/host/config.py`)

*   Defines core Pydantic models: `RootConfig`, `ClientConfig`, `HostConfig`. These are used by `main.py` to load the primary host configuration during startup.
*   Includes a `ConfigurationManager` utility class with static methods for loading/saving other JSON configuration files (workflows, storage) from the `aurite-mcp/config/` directory. This seems separate from the main `HostConfig` loading.

## 5. Initial Discussion Points

*   **Redundant Config Classes:** `RootManager`, `PromptManager`, `ResourceManager` define dataclasses similar to Pydantic models in `config.py`. Consolidate?
*   **SecurityManager Storage:** In-memory credential storage is insecure for production. Plan for integration with a vault?
*   **TransportManager Usage:** The manager exists but `host.py` seems to handle transport creation directly via `AsyncExitStack`. Clarify role or refactor?
*   **StorageManager Specificity:** Tightly coupled to SQLAlchemy. Is this sufficient, or is broader storage support needed?
*   **WorkflowManager Dynamic Config:** The ability for `WorkflowManager` to modify host config and trigger client initialization feels complex. Is this the desired pattern?
*   **ConfigurationManager Utility:** Clarify the role of `ConfigurationManager` vs. the main `HostConfig` loading in `main.py`. Are both needed?
