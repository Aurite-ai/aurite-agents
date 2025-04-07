# MCP Host System - Technical Implementation Specification

**Version:** 0.2
**Date:** 2025-04-07

## 1. Overview

This document details the technical implementation of the `aurite-agents` MCP Host system (`src/host/`), reflecting the state after the major refactor completed on 2025-04-06. It aims to provide a clear understanding of the current implementation, focusing solely on the Host's role in managing MCP server interactions.

The Host system orchestrates communication with various MCP tool servers, providing a unified interface for higher-level components like the `Agent` framework (`src/agents/`). It follows a layered architecture as outlined in the updated `docs/architecture_overview.md`.

## 2. Core Class: `MCPHost` (`src/host/host.py`)

The `MCPHost` class is the central orchestrator.

*   **Initialization:**
    *   Takes a `HostConfig` object (defined in `src/host/models.py`) and an optional `encryption_key` (passed to `SecurityManager`).
    *   Instantiates manager classes for the Foundation, Communication, and Resource Management layers.
    *   The `initialize()` method calls the `initialize()` method of each manager sequentially (Foundation -> Communication -> Resource Management).
    *   Initializes client connections based on the `HostConfig.clients` list using an `AsyncExitStack` to manage `stdio_client` lifecycles.
    *   During client initialization (`_initialize_client`):
        *   Registers roots with `RootManager`.
        *   Registers server capabilities with `MessageRouter`.
        *   Registers the client session with `ToolManager`, `PromptManager`, and `ResourceManager`.
        *   Discovers tools, prompts, and resources from the client.
        *   Registers discovered components with the respective managers, applying the `exclude` list from the `ClientConfig` to filter out unwanted components *at registration time*.
*   **Dependencies:** Uses `contextlib.AsyncExitStack` to manage client session lifecycles.
*   **Service Access:** Exposes managers from the Resource Management layer (Prompts, Resources, Tools) as public properties (e.g., `host.tools`, `host.prompts`, `host.resources`).
*   **Core Functionality (Convenience Methods):** Provides high-level async methods that wrap manager functions for easier use by consumers like the `Agent` class:
    *   `get_prompt(prompt_name, arguments, client_name=None)`: Retrieves a prompt template. Discovers the client if `client_name` is None.
    *   `execute_tool(tool_name, arguments, client_name=None)`: Executes a tool. Discovers the client if `client_name` is None.
    *   `read_resource(uri, client_name=None)`: Retrieves a resource definition (currently not the content). Discovers the client if `client_name` is None.
    *   *(Implicitly uses underlying manager methods like `list_tools`, `list_prompts`, `list_resources`)*.
    *   **Note:** These methods currently only support specifying a single optional `client_name`. Filtering by a list of client IDs is planned for a future update.
*   **Shutdown:** The `shutdown()` method calls the `shutdown()` method of each manager in reverse layer order (Resource Management -> Communication -> Foundation) and closes client connections via the `AsyncExitStack`.

## 3. Layered Architecture Implementation

### 3.1. Layer 1: Foundation

*   **`RootManager` (`src/host/foundation/roots.py`)**
    *   **Purpose:** Manages MCP roots (resource URI boundaries) associated with clients.
    *   **Implementation:** Stores `client_id` -> `List[RootConfig]` mapping. Validates and normalizes URIs upon registration. Provides `validate_access` method used by `ToolManager` and `ResourceManager` to check if a required URI is within a client's allowed roots.
    *   **Notes:** Assumes unrestricted access if no roots are registered for a client.
*   **`SecurityManager` (`src/host/foundation/security.py`)**
    *   **Purpose:** Handles encryption (optional), credential storage (in-memory), access tokens, and basic server permissions (currently unused after refactor).
    *   **Implementation:** Uses `cryptography.fernet` for symmetric encryption. Derives key from `AURITE_MCP_ENCRYPTION_KEY` env var or generates one. Stores encrypted credentials in an *in-memory* dictionary (`_credentials`). Creates temporary access tokens (`_access_tokens`) mapped to credential IDs. Manages server permissions (`_server_permissions`) mapping `server_id` to allowed credential *types*. Provides masking for sensitive data.
    *   **Notes:** In-memory storage is not suitable for production secrets.

### 3.2. Layer 2: Communication

*   **`MessageRouter` (`src/host/foundation/routing.py`)**
    *   **Purpose:** Maps tools and prompts to the clients/servers that provide them based on registration during host initialization. Selects servers for tool execution.
    *   **Implementation:** Maintains dictionaries mapping `tool_name` -> `List[client_id]` and `prompt_name` -> `List[client_id]`. Stores server capabilities and routing weights (`ClientConfig.routing_weight`). The `select_server_for_tool` method (used internally by `ToolManager`) currently uses weights primarily to distinguish primary (weight=1.0) vs. backup (weight<1.0) servers if multiple clients offer the same tool.
    *   **Notes:** Provides methods like `get_clients_for_tool` used by `MCPHost` convenience methods for discovery.

### 3.3. Layer 3: Resource Management

*   **`PromptManager` (`src/host/resources/prompts.py`)**
    *   **Purpose:** Manages system prompts provided by clients.
    *   **Implementation:** Registers prompts per client, applying the `exclude` list from `ClientConfig`. Provides `get_prompt` (retrieves template), `list_prompts`, and `get_clients_for_prompt`.
    *   **Notes:** Prompt *execution* (LLM call) is handled by the `Agent` framework.
*   **`ResourceManager` (`src/host/resources/resources.py`)**
    *   **Purpose:** Manages MCP resources (data identified by URIs) provided by clients.
    *   **Implementation:** Registers resources per client, applying the `exclude` list from `ClientConfig`. Provides `get_resource` (retrieves definition), `list_resources`, `get_clients_for_resource`, and `validate_resource_access` (using `RootManager`).
    *   **Notes:** Actual resource *reading* requires calling `session.read_resource` on the specific client session, which is not currently wrapped by a high-level `ResourceManager` or `MCPHost` method.
*   **`ToolManager` (`src/host/resources/tools.py`)**
    *   **Purpose:** Central hub for tool registration, discovery, execution, and formatting for LLMs.
    *   **Implementation:** Takes `RootManager` and `MessageRouter` as dependencies. Registers tools discovered from clients, applying the `exclude` list from `ClientConfig`. Orchestrates `execute_tool` by selecting a server via `MessageRouter`, validating access via `RootManager` (if tool requires resources), and calling the tool on the client session. Provides `list_tools`, `get_clients_for_tool`, and specific formatting methods (`format_tools_for_llm`, `create_tool_result_blocks`) for LLM interaction (used by the `Agent` class).
    *   **Notes:** Core component bridging the host infrastructure and the `Agent` framework.

*(Note: `StorageManager`, `TransportManager`, and `WorkflowManager` have been removed from the Host system).*

## 4. Configuration (`src/host/models.py`)

*   Defines core Pydantic models used for host configuration: `RootConfig`, `ClientConfig`, `HostConfig`.
*   These models are loaded from a JSON file (specified by `ServerConfig.HOST_CONFIG_PATH`) by the utility function `src.config.load_host_config_from_json` during application startup (`src/main.py`).
*   `ClientConfig` includes the `exclude: Optional[List[str]]` field, used during host initialization to prevent specific tools, prompts, or resources from being registered for that client.

## 5. Current Discussion Points / Areas for Improvement

*   **SecurityManager Storage:** In-memory credential storage is insecure for production. Integration with a secrets management solution should be considered.
*   **Resource Reading:** Currently, no high-level method exists on the Host or `ResourceManager` to directly read resource content; consumers need to access the client session. Consider adding `host.read_resource_content(uri)` or similar.
*   **Host Filtering Feature:** Implement the planned feature to allow convenience methods (`execute_tool`, `list_tools`, etc.) to filter based on a provided list of `client_ids` (Phase 4 of current plan).
*   **Error Handling:** Review error propagation from managers and client sessions up through the host convenience methods.
*   **Configuration Schema:** Review if `RootConfig` defined within `models.py` is sufficient or if managers still need internal representations. (Initial review suggests `models.RootConfig` is used).
