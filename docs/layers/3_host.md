# Layer 3: MCP Host System

**Version:** 1.0
**Date:** 2025-05-04

## 1. Overview

The MCP Host System (Layer 3) serves as the foundational infrastructure layer within the Aurite MCP framework. Its primary purpose is to manage connections with external Model Context Protocol (MCP) servers (referred to as "clients" from the host's perspective) and provide a secure, unified interface for accessing their capabilities (tools, prompts, resources). It acts as the bridge between the higher-level Orchestration Layer (Layer 2) and the individual MCP servers.

`MCPHost` manages the lifecycle of these client connections using `anyio` for structured concurrency. An `anyio.TaskGroup` is used to run individual lifecycle tasks for each client, with each task operating within its own `anyio.CancelScope` for robust startup and shutdown. The `ClientManager` assists in coordinating and tracking these client lifecycles.

Key responsibilities include:
*   Establishing and managing secure, concurrent connections to configured MCP servers via stdio transport, utilizing `anyio.TaskGroup` and `anyio.CancelScope` for robust lifecycle management of each client.
*   Handling the MCP initialization handshake and capability negotiation within individual client lifecycle tasks.
*   Discovering and registering components (tools, prompts, resources) offered by connected clients.
*   Providing dedicated managers (`ToolManager`, `PromptManager`, `ResourceManager`) for interacting with specific component types.
*   Implementing filtering mechanisms based on `ClientConfig` (global exclusions) and `AgentConfig` (agent-specific client access and component exclusions).
*   Managing security aspects like credential encryption and GCP secret resolution (`SecurityManager`).
*   Routing requests to the appropriate client based on component availability, agent permissions, and routing weights (`MessageRouter`).
*   Enforcing access control based on defined MCP roots (`RootManager`).
*   Storing `AgentConfig` instances for use in filtering and discovery by Layer 2.

The Host System is structured internally into two sub-layers:
*   **Foundation Layer:** Provides core services like security, routing, and root management.
*   **Resource Layer:** Builds upon the foundation to manage specific MCP component types (prompts, resources, tools).

## 2. Relevant Files

| File Path                          | Primary Class(es)        | Core Responsibility                                                                 |
| :--------------------------------- | :----------------------- | :---------------------------------------------------------------------------------- |
| `src/host/host.py`                 | `MCPHost`                | Main entrypoint, orchestrates managers, client connections, stores AgentConfigs     |
| `src/host/models.py`               | Config Models            | Pydantic models for `HostConfig`, `ClientConfig`, `AgentConfig`, `RootConfig`, etc. |
| `src/host/filtering.py`            | `FilteringManager`       | Centralized logic for applying `ClientConfig` and `AgentConfig` filtering rules     |
| **Foundation Layer**               |                          |                                                                                     |
| `src/host/foundation/clients.py`   | `ClientManager`          | Manages client configurations, active sessions, and orchestrates client lifecycle tasks within `MCPHost`. |
| `src/host/foundation/security.py`  | `SecurityManager`        | Encryption, credential storage, GCP secret resolution                               |
| `src/host/foundation/routing.py`   | `MessageRouter`          | Routes requests to appropriate clients based on capabilities and configuration      |
| `src/host/foundation/roots.py`     | `RootManager`            | Manages MCP root definitions for client access control                              |
| **Resource Layer**                 |                          |                                                                                     |
| `src/host/resources/prompts.py`    | `PromptManager`          | Manages prompt definitions discovered from clients                                  |
| `src/host/resources/resources.py`  | `ResourceManager`        | Manages resource definitions discovered from clients                                |
| `src/host/resources/tools.py`      | `ToolManager`            | Manages tool definitions, formats tools for LLMs, handles tool execution requests   |

## 3. Functionality

This layer provides the core infrastructure for interacting with MCP servers.

**3.1. Multi-File Interactions & Core Flows:**

*   **Initialization (`MCPHost.initialize`):**
    *   Triggered by `HostManager` (Layer 2).
    *   Initializes managers in order: Foundation (`SecurityManager`, `RootManager`, `MessageRouter`) then Resource (`PromptManager`, `ResourceManager`, `ToolManager`).
    *   Iterates through `ClientConfig` entries in the `HostConfig`.
    *   For each client:
        *   Resolves GCP secrets via `SecurityManager` (if configured).
        *   Establishes stdio transport using `mcp.stdio_client`, injecting resolved secrets into the server's environment.
        *   Creates a `ClientSession` using the transport.
        *   Performs MCP `initialize` handshake, sending client capabilities.
        *   Sends `initialized` notification.
        *   Registers client roots with `RootManager`.
        *   Registers the client and its capabilities/weight with `MessageRouter`.
        *   Stores the `ClientSession`.
        *   Discovers components (tools, prompts, resources) via session methods (`list_tools`, `list_prompts`, `list_resources`).
        *   Registers discovered components with the respective Resource Managers (`ToolManager`, `PromptManager`, `ResourceManager`), applying client-level exclusions (`ClientConfig.exclude`) via the `FilteringManager`.
*   **Component Registration (Dynamic - `MCPHost.register_client`):**
    *   Allows adding new clients after initial host startup.
    *   Called by `HostManager.register_client` (Layer 2).
    *   Re-uses the internal `_initialize_client` logic for the new `ClientConfig`.
*   **Filtering & Discovery (Runtime):**
    *   **Client Exclusion (`ClientConfig.exclude`):** Applied by `FilteringManager.is_registration_allowed` during client initialization/registration within Resource Managers. Prevents globally excluded components from being registered for a specific client.
    *   **Agent Client Filtering (`AgentConfig.client_ids`):** Applied by `FilteringManager.filter_clients_for_request` within `MCPHost` methods (`get_prompt`, `execute_tool`, `read_resource`, `get_formatted_tools`). Restricts which clients an agent can interact with. The `MessageRouter` is first queried to find *all* clients providing a component, then this list is filtered based on the agent's allowed `client_ids`.
    *   **Agent Component Exclusion (`AgentConfig.exclude_components`):** Applied by `FilteringManager.is_component_allowed_for_agent` (for single requests) or `FilteringManager.filter_component_list` (for lists like tools) within `MCPHost` methods. Prevents an agent from using specific components, even if provided by an allowed client.
*   **Execution Requests (e.g., `MCPHost.execute_tool`):**
    *   Called by Layer 2 components (e.g., `Agent` via `ExecutionFacade`).
    *   Receives component name, arguments, and optionally a specific `client_name` and the requesting `AgentConfig`.
    *   Uses `MessageRouter` to find potential clients providing the component.
    *   Applies agent filtering (`client_ids`) via `FilteringManager` to narrow down potential clients.
    *   Determines the target client (handles ambiguity if `client_name` not provided).
    *   Applies agent component filtering (`exclude_components`) via `FilteringManager`.
    *   Delegates the actual execution to the appropriate Resource Manager (`ToolManager`, `PromptManager`, `ResourceManager`), passing the determined `client_id`.
    *   Resource Managers use the stored `ClientSession` to send the request to the target MCP server.
*   **Tool Formatting (`MCPHost.get_formatted_tools`):**
    *   Called by `Agent` (Layer 2.5) to prepare tools for the LLM.
    *   Delegates to `ToolManager.format_tools_for_llm`.
    *   Passes `FilteringManager` and `AgentConfig` to the `ToolManager` method to ensure the returned list respects both `client_ids` and `exclude_components` filters.

**3.2. Individual File Functionality:**

*   **`host/host.py` (`MCPHost`):**
    *   Orchestrates the initialization and shutdown sequence for all managers and client connections.
    *   Holds the main `HostConfig` and the dictionary of `AgentConfig`s.
    *   Provides public methods (`get_prompt`, `execute_tool`, `read_resource`, `get_formatted_tools`, `register_client`) that act as the primary interface for Layer 2.
    *   Integrates `MessageRouter` and `FilteringManager` to apply routing and filtering rules before delegating tasks to Resource Managers.
    *   Manages client sessions (`_clients`) and the `AsyncExitStack` for cleanup.
*   **`host/models.py`:**
    *   Defines core Pydantic models used by Layer 3: `HostConfig`, `ClientConfig`, `RootConfig`, `GCPSecretConfig`.
    *   Also defines `AgentConfig`, which is stored and used for filtering here, but primarily acted upon by Layer 2/2.5.
*   **`host/filtering.py` (`FilteringManager`):**
    *   Contains stateless methods for applying filtering logic based on `ClientConfig` and `AgentConfig`.
    *   `is_registration_allowed`: Checks `ClientConfig.exclude` during component registration.
    *   `filter_clients_for_request`: Filters client lists based on `AgentConfig.client_ids`.
    *   `is_component_allowed_for_agent`: Checks `AgentConfig.exclude_components` for single requests.
    *   `filter_component_list`: Filters lists of components based on `AgentConfig.exclude_components`.
*   **`host/foundation/security.py` (`SecurityManager`):**
    *   Manages encryption key (`AURITE_MCP_ENCRYPTION_KEY` or generated). It is crucial for production environments to explicitly set the `AURITE_MCP_ENCRYPTION_KEY` environment variable to ensure persistent and secure encryption, rather than relying on an auto-generated key.
    *   Provides methods for encrypting/decrypting credentials (though not heavily used by `MCPHost` currently, available for future use).
    *   Handles resolution of GCP secrets specified in `ClientConfig.gcp_secrets` using `google-cloud-secret-manager`.
*   **`host/foundation/routing.py` (`MessageRouter`):**
    *   Maintains mappings of components (tools, prompts, resources) to the client IDs that provide them.
    *   Stores client capabilities and routing weights.
    *   Provides methods (`get_clients_for_tool`, etc.) to find suitable clients for a given request.
*   **`host/foundation/roots.py` (`RootManager`):**
    *   Stores `RootConfig` definitions associated with each client.
    *   Provides methods (`register_roots`, `get_client_roots`, `validate_access`) used by `MCPHost` and Resource Managers to enforce access control based on resource URIs.
*   **`host/resources/prompts.py` (`PromptManager`):**
    *   Stores discovered `mcp.types.Prompt` definitions per client.
    *   Handles registration (`register_client_prompts`) and retrieval (`get_prompt`) of prompt *definitions*. (Actual prompt execution happens in Layer 2.5/`Agent`).
*   **`host/resources/resources.py` (`ResourceManager`):**
    *   Stores discovered `mcp.types.Resource` definitions per client.
    *   Handles registration (`register_client_resources`) and retrieval (`get_resource`) of resource *definitions*.
    *   Includes logic (`validate_resource_access`) to check resource URIs against client roots via `RootManager`.
*   **`host/resources/tools.py` (`ToolManager`):**
    *   Stores discovered `mcp.types.Tool` definitions.
    *   Handles registration (`register_tool`), discovery (`discover_client_tools`), and execution (`execute_tool`) requests.
    *   Formats tool definitions for LLM consumption (`format_tools_for_llm`), incorporating filtering logic by accepting `FilteringManager` and `AgentConfig`.
    *   Uses `RootManager` to validate access before execution.
    *   Uses the `ClientSession` to send `call_tool` requests to the target MCP server.

## 4. Testing

**4.A. Testing Overview:**

*   **Execution:** Tests for this layer are marked with `host`, `host_unit`, or `host_integration` and run via `pytest -m host`.
*   **Location:** Tests reside within the `tests/host/` directory, organized into subdirectories mirroring the `src/host/` structure (e.g., `tests/host/foundation/`, `tests/host/resources/`).
*   **Approach:** Testing focuses on verifying the core responsibilities of the Host System through:
    *   **Unit Tests:** Isolating and testing specific methods within `MCPHost` and each Manager (`FilteringManager`, `SecurityManager`, `MessageRouter`, `RootManager`, `PromptManager`, `ResourceManager`, `ToolManager`). Mocks are used for dependencies.
    *   **Integration Tests:** Verifying interactions *between* components within this layer (e.g., `MCPHost` -> `FilteringManager` -> `ToolManager` -> `MessageRouter`) using the `host_manager` fixture (which provides a real `MCPHost` connected to dummy servers). These tests validate the end-to-end flow for initialization, component registration, filtering, and execution requests within the Host layer.

**4.B. Testing Infrastructure:**

*   **`tests/conftest.py`:** (Global) Contains global pytest configuration, markers (`host`, `host_unit`, `host_integration`, etc.), `anyio_backend` setting.
*   **`tests/host/conftest.py`:** (Host Layer Specific) Provides shared mock fixtures used across multiple unit tests within `tests/host/`:
    *   `mock_message_router`: Mocked `MessageRouter`.
    *   `mock_filtering_manager`: Mocked `FilteringManager`.
    *   `mock_root_manager`: Mocked `RootManager`.
*   **`tests/fixtures/host_fixtures.py`:**
    *   `host_manager`: Crucial **function-scoped** integration fixture initializing `HostManager` -> `MCPHost` with `testing_config.json` and dummy servers. Essential for integration tests.
    *   `mock_mcp_host`: Mock `MCPHost` for Layer 2 unit tests.
    *   `mock_host_config`: Basic `HostConfig` mock.
*   **`tests/fixtures/agent_fixtures.py`:** Provides various `AgentConfig` instances needed for testing filtering logic (e.g., `minimal_agent_config`, `agent_config_filtered`).
*   **`tests/fixtures/servers/`:** Contains dummy MCP server implementations (`weather_mcp_server.py`, `planning_server.py`, `env_check_server.py`) used by the `host_manager` fixture.
*   **`tests/mocks/`:** Contains mocks like `mock_gcp_secret_client` (used within `test_security_manager.py`) and potentially others.
*   **`pytestmark = pytest.mark.anyio`:** Used at the module level for async tests.

**4.C. Testing Coverage (Completed):**

| Functionality                                      | Relevant File(s)                              | Test File(s) / Status                                                                                                                                                                                                                                                           |
| :------------------------------------------------- | :-------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **MCPHost: `__init__` & Basic State**              | `host.py`                                     | `tests/host/test_host_basic.py`. **Coverage: Good.**                                                                                                                                                                                                                            |
| **MCPHost: `initialize()` (Success)**              | `host.py`, Managers, `mcp` lib                | `tests/host/test_host_basic_e2e.py` (via `host_manager`). **Coverage: Good (E2E).**                                                                                                                                                                                              |
| **MCPHost: `initialize()` (Error Handling)**       | `host.py`, Managers                           | `tests/host/test_host_lifecycle.py` (Client connection error, Manager init error). **Coverage: Good.**                                                                                                                                                                           |
| **MCPHost: `_initialize_client` (Secret Injection)** | `host.py`, `security.py`                      | `tests/host/foundation/test_security_manager.py` (Mocked GCP), `tests/host/test_host_basic_e2e.py` (Implicit E2E via `host_manager` if secrets were in `testing_config.json`). **Coverage: Good (Mechanism).**                                                              |
| **MCPHost: `shutdown()`**                          | `host.py`, Managers                           | `tests/host/test_host_lifecycle.py`. **Coverage: Good.**                                                                                                                                                                                                                        |
| **MCPHost: `register_client()` (Dynamic)**         | `host.py`                                     | `tests/host/test_host_dynamic_registration.py` (Integration via `host_manager`). **Coverage: Good.**                                                                                                                                                                            |
| **MCPHost: Filtering Application**                 | `host.py`, `filtering.py`, Managers           | `tests/host/filtering/test_filtering.py` (Integration tests for `get_formatted_tools`, `execute_tool`, `get_prompt`, `read_resource`). **Coverage: Good.**                                                                                                                      |
| **FilteringManager: Logic**                        | `filtering.py`                                | `tests/host/filtering/test_filtering.py` (Unit tests). **Coverage: Excellent.**                                                                                                                                                                                                 |
| **SecurityManager: GCP Secret Resolution**         | `security.py`                                 | `tests/host/foundation/test_security_manager.py` (Unit tests mocking GCP client). **Coverage: Good.**                                                                                                                                                                           |
| **SecurityManager: Encryption/Tokens/Masking**     | `security.py`                                 | `tests/host/foundation/test_security_manager.py` (Unit tests). **Coverage: Good.**                                                                                                                                                                                              |
| **MessageRouter: Logic**                           | `routing.py`                                  | `tests/host/foundation/test_message_router.py` (Unit tests). **Coverage: Excellent.**                                                                                                                                                                                           |
| **RootManager: Logic**                             | `roots.py`                                    | `tests/host/foundation/test_root_manager.py` (Unit tests - registration, retrieval, shutdown). `tests/host/resources/test_resource_manager.py` (Unit tests - `validate_access`). **Coverage: Good.**                                                                          |
| **PromptManager: Logic**                           | `prompts.py`                                  | `tests/host/resources/test_prompt_manager.py` (Unit tests - registration, retrieval, listing, shutdown). **Coverage: Excellent.**                                                                                                                                               |
| **ResourceManager: Logic**                         | `resources.py`                                | `tests/host/resources/test_resource_manager.py` (Unit tests - registration, retrieval, listing, validation, shutdown). **Coverage: Excellent.**                                                                                                                                  |
| **ToolManager: Logic**                             | `tools.py`                                    | `tests/host/resources/test_tool_manager.py` (Unit tests - registration, discovery, execution, formatting, shutdown). `tests/host/filtering/test_filtering.py` (Partial integration). `tests/host/test_host_basic_e2e.py` (Partial E2E). **Coverage: Excellent (Unit).** |

**(Section 4.D removed)**
