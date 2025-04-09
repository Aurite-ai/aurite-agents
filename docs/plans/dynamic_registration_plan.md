# Implementation Plan: Dynamic Registration

**Objective:** Add functionality to the `HostManager` and the API (`main.py`) to allow dynamic registration of MCP Clients, Agents, and Simple Workflows after the initial application startup.

**Owner:** Ryan Wilcox (assisted by Gemini)

**Status:** Proposed

**Related Docs:**
*   [Overarching Plan: Dynamic Registration, Entrypoints, and Documentation](docs/plans/entrypoints_plan.md)
*   [Host Manager Implementation Plan (Completed)](docs/plans/completed/4-09-25/host_manager_implementation_plan.md)
*   [Host Implementation](docs/host/host_implementation.md)

**Background:**
Currently, all components (clients, agents, workflows) are loaded from a static configuration file at startup. Dynamic registration will allow adding new components via API calls without restarting the server, increasing flexibility for scenarios like on-demand agent deployment or connecting to newly available MCP servers.

**High-Level Plan:**

1.  Add registration methods to `HostManager` for clients, agents, and workflows.
2.  Add a corresponding registration method to `MCPHost` specifically for clients, leveraging the existing client initialization logic.
3.  Expose these registration capabilities via new API endpoints in `main.py`.

**Impacted Files:**

*   `src/host_manager.py` (Add registration methods)
*   `src/host/host.py` (Add client registration method)
*   `src/main.py` (Add API endpoints for registration)
*   `src/host/models.py` (Review models for API usage, likely no changes needed)

**Detailed Implementation Steps:**

1.  **Modify `HostManager` (`src/host_manager.py`):**
    *   **Add `async register_client(self, client_config: ClientConfig)` method:**
        *   Check if `self.host` is initialized; raise `ValueError` if not.
        *   Check if `client_config.client_id` already exists in `self.host._clients`; raise `ValueError` (or a custom exception like `DuplicateClientIdError`) if it does.
        *   Call `await self.host.register_client(client_config)`. This method will handle the actual initialization and add the client to `self.host._clients`.
        *   Log success or failure, including any exceptions propagated from `self.host.register_client`.
    *   **Add `async register_agent(self, agent_config: AgentConfig)` method:**
        *   Check if `self.host` is initialized; raise `ValueError` if not.
        *   Check if `agent_config.name` already exists in `self.agent_configs`; raise `ValueError` (or `DuplicateAgentNameError`) if it does.
        *   Validate `agent_config.client_ids`: Ensure all specified client IDs exist in `self.host._clients`. Raise `ValueError` if any are missing.
        *   Add the validated `agent_config` to the `self.agent_configs` dictionary: `self.agent_configs[agent_config.name] = agent_config`.
        *   Log success.
    *   **Add `async register_workflow(self, workflow_config: WorkflowConfig)` method:**
        *   Check if `self.host` is initialized; raise `ValueError` if not.
        *   Check if `workflow_config.name` already exists in `self.workflow_configs`; raise `ValueError` (or `DuplicateWorkflowNameError`) if it does.
        *   Validate `workflow_config.steps`: Ensure all agent names listed in the steps exist as keys in `self.agent_configs`. Raise `ValueError` if any are missing.
        *   Add the validated `workflow_config` to the `self.workflow_configs` dictionary: `self.workflow_configs[workflow_config.name] = workflow_config`.
        *   Log success.

2.  **Modify `MCPHost` (`src/host/host.py`):**
    *   **Add `async register_client(self, config: ClientConfig)` method:**
        *   Check if `config.client_id` already exists in `self._clients`; raise `ValueError` (or `DuplicateClientIdError`) if it does.
        *   Call `await self._initialize_client(config)`. This existing private method handles:
            *   Setting up the transport using `stdio_client`.
            *   Entering the transport and session into the `self._exit_stack`.
            *   Sending `initialize` and `initialized`.
            *   Registering roots, capabilities (router), and discovering/registering tools, prompts, resources.
            *   Adding the session to `self._clients`.
        *   **Verification:** Confirm that `_initialize_client` and its use of `self._exit_stack.enter_async_context` are safe to call after the initial `MCPHost.initialize()` has completed. (Initial assessment: Yes, `AsyncExitStack` allows entering new contexts dynamically).
        *   Log success or failure, propagating exceptions from `_initialize_client`.

3.  **Modify `src/main.py` (API Endpoints):**
    *   Import `ClientConfig`, `AgentConfig`, `WorkflowConfig` from `src.host.models`.
    *   **Add `POST /clients/register` endpoint:**
        *   Request Body: `client_config: ClientConfig`
        *   Dependencies: `api_key: str = Depends(get_api_key)`, `manager: HostManager = Depends(get_host_manager)`
        *   Logic:
            *   Call `await manager.register_client(client_config)`.
            *   Handle `ValueError` (e.g., duplicate ID, host not ready) -> `HTTPException(status_code=409 or 503)`.
            *   Handle other exceptions from client initialization (e.g., connection errors) -> `HTTPException(status_code=500)`.
            *   Return `{"status": "success", "client_id": client_config.client_id}` with status code `201 Created` on success.
    *   **Add `POST /agents/register` endpoint:**
        *   Request Body: `agent_config: AgentConfig`
        *   Dependencies: `api_key: str = Depends(get_api_key)`, `manager: HostManager = Depends(get_host_manager)`
        *   Logic:
            *   Call `await manager.register_agent(agent_config)`.
            *   Handle `ValueError` (e.g., duplicate name, invalid client ID, host not ready) -> `HTTPException(status_code=409 or 400 or 503)`.
            *   Handle Pydantic `ValidationError` if model validation fails -> `HTTPException(status_code=422)`.
            *   Return `{"status": "success", "agent_name": agent_config.name}` with status code `201 Created` on success.
    *   **Add `POST /workflows/register` endpoint:**
        *   Request Body: `workflow_config: WorkflowConfig`
        *   Dependencies: `api_key: str = Depends(get_api_key)`, `manager: HostManager = Depends(get_host_manager)`
        *   Logic:
            *   Call `await manager.register_workflow(workflow_config)`.
            *   Handle `ValueError` (e.g., duplicate name, invalid agent name, host not ready) -> `HTTPException(status_code=409 or 400 or 503)`.
            *   Handle Pydantic `ValidationError` -> `HTTPException(status_code=422)`.
            *   Return `{"status": "success", "workflow_name": workflow_config.name}` with status code `201 Created` on success.

4.  **Review `src/host/models.py`:**
    *   Confirm that `ClientConfig`, `AgentConfig`, and `WorkflowConfig` are suitable for direct use as API request body models. Ensure all necessary fields for registration are present and types are appropriate for JSON deserialization. (Initial assessment: Models seem suitable).

**Error Handling Considerations:**

*   Use specific exceptions where appropriate (e.g., `DuplicateClientIdError`) or rely on `ValueError` with descriptive messages.
*   Map exceptions caught in the API endpoints to appropriate HTTP status codes (400 Bad Request, 409 Conflict, 422 Unprocessable Entity, 500 Internal Server Error, 503 Service Unavailable).
*   Ensure clear logging for registration attempts and outcomes.

**Testing:**
Testing of these new endpoints and underlying logic will be performed in Task 2 of the overarching plan by extending the Postman collection (`tests/api/main_server.postman_collection.json`) and running it with Newman.
