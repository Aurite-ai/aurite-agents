# Plan: FastAPI Server (`src/main.py`) Refactoring and Testing

**Version:** 1.0
**Date:** 2025-04-05

## 1. Goal

Refactor `src/main.py` to improve stability, security, testability, and maintainability by simplifying its responsibilities, improving configuration handling, and implementing basic security. Define a clear testing strategy using Postman/Newman.

## 2. Current State Analysis

*   FastAPI server acting as an interface to `MCPHost`.
*   Uses a global `mcp_host` variable.
*   Initializes `MCPHost` via an `/initialize` endpoint, reading config paths and secrets from the request body.
*   Includes a dynamic `/register_workflow` endpoint using `__import__`.
*   Lacks configuration validation (e.g., Pydantic).
*   Passes sensitive data (API keys, encryption keys) in request bodies.
*   Uses overly permissive CORS (`*`) and lacks authentication.
*   Contains hardcoded values (port, workers, model params).
*   Error handling is generic.

## 3. Proposed Changes & Implementation Steps

**Note:** Steps should be performed sequentially.

### 3.1. Configuration and Initialization Refactoring

1.  **Modify `HostConfig` (and related models in `src/host/config.py`):** Ensure `HostConfig`, `ClientConfig`, `RootConfig` are robust Pydantic models capable of validating the structure loaded from JSON configuration files. Add fields for necessary server settings if not present (e.g., potentially workflow paths if loading from config).
2.  **Create `ServerConfig` Model:** Define a new Pydantic model (e.g., in `src/config.py` or `src/main.py`) to manage server-specific settings like `HOST`, `PORT`, `WORKERS`, `LOG_LEVEL`, `API_KEY`, `ENCRYPTION_KEY`, `HOST_CONFIG_PATH`. Use `pydantic-settings` or similar to load these from environment variables.
3.  **Implement Dependency for `ServerConfig`:** Create a FastAPI dependency function to load and provide the `ServerConfig`.
4.  **Implement Dependency for `MCPHost`:**
    *   Create a function (e.g., `get_mcp_host`) that initializes the `MCPHost` instance *once* using the loaded `ServerConfig` (getting `HOST_CONFIG_PATH`, `ENCRYPTION_KEY`).
    *   This function should load the host configuration JSON from the path specified in `ServerConfig`.
    *   Use FastAPI's application state (`app.state`) or a simple cache within the dependency function to store and reuse the initialized `MCPHost` instance across requests.
5.  **Refactor `lifespan` Context Manager:**
    *   Remove global `mcp_host` usage.
    *   Modify the startup logic within `lifespan` to use the `get_mcp_host` dependency logic to initialize the host *during application startup*. This ensures the host is ready before requests are served.
    *   Ensure the host's `shutdown()` method is called correctly during application shutdown within `lifespan`.
6.  **Remove `/initialize` Endpoint:** Delete the `POST /initialize` endpoint and its associated `InitializeRequest` model, as initialization now happens at startup.

### 3.2. Security and Endpoint Refinement

7.  **Implement API Key Security:**
    *   Use FastAPI's `APIKeyHeader` security dependency.
    *   Create a dependency function (e.g., `get_api_key`) that checks the incoming request header against the `API_KEY` loaded in `ServerConfig`. Raise `HTTPException` (401/403) if invalid.
    *   Apply this security dependency to all relevant endpoints.
8.  **Remove `/register_workflow` Endpoint:** Delete the `POST /register_workflow` endpoint and its `RegisterWorkflowRequest` model. Workflow registration will rely solely on the configuration loaded during `MCPHost` initialization at startup. (Confirm `MCPHost.initialize` handles this correctly based on config).
9.  **Refactor Endpoints to Use Dependencies:**
    *   Modify all remaining endpoints (`/status`, `/prepare_prompt`, `/execute_prompt`, `/execute_workflow`) to use the `get_mcp_host` dependency to access the host instance instead of the global variable.
    *   Ensure endpoints use the `get_api_key` security dependency.
    *   Remove `anthropic_api_key` from the `ExecutePromptRequest` model and the `execute_prompt` endpoint signature; the host should retrieve this from its secure configuration (env vars).
10. **Refine `/prepare_prompt` and `/execute_prompt`:** Review the logic. Since `execute_prompt` internally calls `prepare_prompt`, consider if the separate `/prepare_prompt` endpoint is still necessary or if its functionality can be implicitly handled by `/execute_prompt`. (Decision: Keep both for now, allows preparing context separately if needed).
11. **Configure CORS:** Update `CORSMiddleware` to use specific allowed origins from `ServerConfig` instead of `*`.
12. **Configure Uvicorn:** Modify `start()` function and `uvicorn.run` call to use `HOST`, `PORT`, `WORKERS`, `LOG_LEVEL` from the loaded `ServerConfig`.

### 3.3. Error Handling and Logging

13. **Improve Error Handling:** Review `try...except` blocks in endpoints. Catch more specific exceptions where possible (e.g., `ValueError` from host methods) and return appropriate `HTTPException` status codes and details.
14. **Review Logging:** Ensure logging provides sufficient context, especially around configuration loading and endpoint execution.

## 4. Testing Strategy

1.  **Create Postman Collection:** Develop a Postman collection (`aurite-mcp/docs/testing/main_server.postman_collection.json`) with requests for each endpoint:
    *   `/status`
    *   `/prepare_prompt` (requires valid `client_id`, `prompt_name`)
    *   `/execute_prompt` (requires valid `client_id`, `prompt_name`, `user_message`)
    *   `/execute_workflow` (requires valid `workflow_name`, `input_data`)
    *   Include tests for valid requests (2xx status).
    *   Include tests for invalid requests (e.g., missing API key, bad input, host not ready - expect 4xx/5xx status).
    *   Use environment variables in Postman for `API_KEY`, `base_url`, etc.
2.  **Document Newman Execution:** Add instructions to `aurite-mcp/docs/testing_infrastructure.md` (or a new file) on how to run the Postman collection using Newman CLI for automated testing, including environment setup (setting API key, host config path env vars).

## 5. Memory Bank Updates

*   Log decision to remove dynamic workflow registration.
*   Log decision to use startup configuration loading via environment variables.
*   Log decision to use API Key authentication.

## 6. Next Steps

*   Review and confirm this plan with Ryan.
*   Proceed to Implementation Phase upon approval.
