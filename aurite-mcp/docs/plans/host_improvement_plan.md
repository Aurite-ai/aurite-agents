# Plan: MCP Host System Improvements

**Version:** 0.1
**Date:** 2025-04-05

## 1. Goal

Refactor and improve the `aurite-mcp` Host system (`src/host/`) based on the technical review documented in `docs/host_implementation.md`. The focus is on simplifying the architecture, improving consistency, addressing immediate security concerns, and removing deprecated components.

## 2. Scope

This plan covers the following improvement areas:

1.  **Configuration Model Consolidation:** Unify configuration object definitions.
2.  **Security Manager Storage:** Review and potentially enhance credential handling.
3.  **Transport Manager Role:** Clarify or remove the `TransportManager`.
4.  **ConfigurationManager Removal:** Deprecate and remove the utility class.

**Out of Scope (Deferred):**
*   Major refactoring of `StorageManager` for broader database support.
*   Refactoring `WorkflowManager` (pending BaseWorkflow rebuild).

## 3. Implementation Steps

*(Note: These are high-level steps. Detailed analysis and specific code changes will be determined during each step's implementation phase.)*

### 3.1. Step 1: Consolidate Configuration Models

*   **Goal:** Ensure consistent use of Pydantic models from `src/host/config.py` across all managers.
*   **Tasks:**
    1.  Review `RootManager`, `PromptManager`, and `ResourceManager`.
    2.  Identify internal dataclasses (`RootConfig`, `PromptConfig`, `ResourceConfig`) that are redundant with the Pydantic models (`RootConfig` in `src/host/config.py`).
    3.  Refactor these managers to use the Pydantic models from `src/host/config.py` directly for configuration and internal representation where appropriate.
    4.  Remove the redundant internal dataclass definitions.
    5.  Verify that functionality remains unchanged through existing tests or by adding minimal checks if necessary.

### 3.2. Step 2: Remove ConfigurationManager Utility

*   **Goal:** Remove the deprecated `ConfigurationManager` class from `src/host/config.py`.
*   **Tasks:**
    1.  Identify all modules currently importing or using `ConfigurationManager` (likely `StorageManager` for `connections.json` and potentially others if used for `workflows.json`).
    2.  Confirm that the primary host configuration mechanism (loading `HostConfig` from a single JSON file like `aurite-mcp/config/host/aurite_host.json` in `main.py`) covers all necessary configuration needs previously handled by `ConfigurationManager`. *(Self-correction: `main.py` loads the host config specified by `ServerConfig.HOST_CONFIG_PATH`, which could point to `aurite_agents.json` or `aurite_host.json` depending on the environment setting)*.
    3.  Refactor any components using `ConfigurationManager` to obtain necessary configuration through other means (e.g., passed during initialization, loaded directly if absolutely necessary and simple).
    4.  Remove the `ConfigurationManager` class definition from `src/host/config.py`.
    5.  Rename `aurite-mcp/src/host/config.py` to `models.py` as it is only for models now.

### 3.3. Step 3: Review SecurityManager Storage

*   **Goal:** Assess the current in-memory credential storage and identify simple, near-term improvements, potentially leveraging GCP Secrets Manager.
*   **Tasks:**
    1.  Analyze how credentials (especially the encryption key and potentially database credentials loaded by `StorageManager`) are currently handled.
    2.  Investigate the feasibility and complexity of integrating GCP Secrets Manager for storing/retrieving the primary encryption key and potentially other sensitive configurations.
    3.  Propose a specific, minimal change (if any) to improve security posture without requiring a full production-ready vault implementation at this stage. (e.g., ensuring the encryption key is *only* loaded from env var).
    4.  Implement the agreed-upon change.

### 3.4. Step 4: Clarify/Refactor TransportManager Role

*   **Goal:** Determine the necessity of `TransportManager` given the current implementation in `MCPHost`.
*   **Tasks:**
    1.  Compare the transport/client session lifecycle management in `TransportManager` versus how it's handled directly in `MCPHost._initialize_client` using `AsyncExitStack`.
    2.  Decide whether `TransportManager` provides necessary abstraction or if its logic can be fully integrated into `MCPHost`.
    3.  If `TransportManager` is deemed redundant, refactor `MCPHost` to remove the dependency and inline any necessary logic.
    4.  If `TransportManager` is kept, refactor `MCPHost._initialize_client` to utilize the manager correctly for transport creation and lifecycle.
