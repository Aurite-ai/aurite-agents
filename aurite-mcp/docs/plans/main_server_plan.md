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

**Note:** Implementation steps 1-14 are complete.

### 3.1. Configuration and Initialization Refactoring (Completed)

1.  **Modify `HostConfig`:** Updated `HostConfig`, `ClientConfig`, `RootConfig` in `src/host/config.py` to use Pydantic `BaseModel`. Added `enable_memory: bool` flag to `HostConfig`.
2.  **Create `ServerConfig` Model:** Created `src/config.py` with `ServerConfig` using `pydantic-settings` to load server settings (host, port, keys, paths) from environment variables.
3.  **Implement Dependency for `ServerConfig`:** Added `get_server_config()` dependency function with caching in `src/main.py`.
4.  **Implement Dependency for `MCPHost`:** Added `get_mcp_host()` dependency function in `src/main.py` to retrieve the host instance from `app.state`.
5.  **Refactor `lifespan` Context Manager:** Updated `lifespan` in `src/main.py` to:
    *   Load `ServerConfig` and `HostConfig` JSON at startup.
    *   Correctly resolve relative `server_path` for clients based on the `aurite-mcp` directory.
    *   Read `enable_memory` flag from JSON and pass to `HostConfig`.
    *   Initialize `MCPHost` and store it in `app.state`.
    *   Handle `MCPHost` shutdown.
    *   Removed global `mcp_host` variable.
6.  **Remove `/initialize` Endpoint:** Deleted the `POST /initialize` endpoint and `InitializeRequest` model from `src/main.py`.

### 3.2. Security and Endpoint Refinement (Completed)

7.  **Implement API Key Security:** Added `get_api_key()` dependency using `APIKeyHeader` and `secrets.compare_digest` in `src/main.py`. Applied dependency to relevant endpoints.
8.  **Remove `/register_workflow` Endpoint:** Deleted the `POST /register_workflow` endpoint and `RegisterWorkflowRequest` model from `src/main.py`.
9.  **Refactor Endpoints to Use Dependencies:** Updated `/status`, `/prepare_prompt`, `/execute_prompt`, `/execute_workflow` to use `Depends(get_mcp_host)` and `Depends(get_api_key)`. Removed `anthropic_api_key` from `ExecutePromptRequest` model and `execute_prompt` call.
10. **Refine `/prepare_prompt` and `/execute_prompt`:** Kept both endpoints as per plan decision. No code changes needed.
11. **Configure CORS:** Updated `CORSMiddleware` in `src/main.py` to use `allow_origins=get_server_config().ALLOWED_ORIGINS`.
12. **Configure Uvicorn:** Updated `start()` function in `src/main.py` to use settings from `ServerConfig` for `uvicorn.run`.

### 3.3. Error Handling and Logging (Completed)

13. **Improve Error Handling:** Refined `try...except` blocks in endpoints (`/prepare_prompt`, `/execute_prompt`, `/execute_workflow`) to catch `ValueError` and return appropriate 4xx HTTP status codes, while retaining general 500 errors for other exceptions.
14. **Review Logging:** Confirmed logging provides adequate context for startup, configuration, security, and errors. No changes needed.

### 3.4. Additional Implementation (Completed)

*   **Add `/health` Endpoint:** Added a simple `GET /health` endpoint to `src/main.py` for basic server responsiveness checks.
*   **Install Dependencies:** Added `mem0ai` to `pyproject.toml` and installed dependencies using `pip install -e .`.
*   **Troubleshoot Startup:** Diagnosed and fixed issues related to `mem0ai` configuration and client `server_path` resolution.
*   **Implement Memory Feature Flag:** Added `enable_memory` flag to `HostConfig` and conditional logic in `host.py` and `main.py` to control memory client initialization based on JSON config.

## 4. Testing Strategy (Revised)

**Goal:** Verify the refactored server starts correctly and the basic `/health` endpoint works using Newman. Iteratively add tests for other endpoints.

1.  **Install Newman:** (Completed) Installed Newman globally via `npm install -g newman`.
2.  **Create Initial Postman Collection:** (Completed) Created `aurite-mcp/docs/testing/main_server.postman_collection.json` with a single request for `GET /health` and tests for 200 status and `{"status": "ok"}` body.
3.  **Run Server:** (Completed) Successfully started the server using `python aurite-mcp/src/main.py` after resolving dependency and path issues, and implementing the memory feature flag (currently disabled via config).
4.  **Run Newman Test (Health Check):** Execute the Postman collection using Newman to verify the `/health` endpoint.
    *   Command: `newman run aurite-mcp/docs/testing/main_server.postman_collection.json`
5.  **Iteratively Add Endpoint Tests:**
    *   Add the `GET /status` request (requires API Key) to the collection.
    *   Create a Postman Environment file (`aurite-mcp/docs/testing/main_server.postman_environment.json`) to store `API_KEY` and `base_url`.
    *   Update Newman command to use the environment file (`-e`).
    *   Run Newman tests for `/health` and `/status`.
    *   Incrementally add requests and tests for `/prepare_prompt`, `/execute_prompt`, and `/execute_workflow`, ensuring appropriate request bodies and API key headers are used.
6.  **Document Newman Execution:** Add final instructions to `aurite-mcp/docs/testing_infrastructure.md` on how to run the complete Postman collection using Newman CLI with the environment file.

## 5. Memory Bank Updates (To Do)

*   Log decision to remove dynamic workflow registration.
*   Log decision to use startup configuration loading via environment variables.
*   Log decision to use API Key authentication.

## 6. Next Steps

*   Review and confirm this plan with Ryan.
*   Proceed to Implementation Phase upon approval.
