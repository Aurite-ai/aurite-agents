# Implementation Plan: Phase 3 - Advanced Configuration Features & Client Lifecycle Management

This document outlines the detailed steps for completing Phase 3 of the AI Agent Framework Enhancement, focusing on client lifecycle management, project switching, and new API endpoints as per the `docs/plans/overarching_plan.md` and your recent instructions.

## I. Client Lifecycle Management (`ClientManager` and `MCPHost` Refactor)

**Goal:** Centralize client process management into a new `ClientManager` and refactor `MCPHost` to utilize it for starting, stopping, and managing client lifecycles.

**1.1. Create `ClientManager` Class**
    *   **File:** `src/host/foundation/clients.py` (new file)
    *   **Action:**
        *   Define the `ClientManager` class.
        *   **Responsibilities:**
            *   `__init__(self, exit_stack: AsyncExitStack)`: Store an `AsyncExitStack` for managing client subprocess lifecycles.
            *   `active_clients: Dict[str, ClientSession]`: Dictionary to store active client sessions, keyed by `client_id`.
            *   `client_processes: Dict[str, Any]`: Dictionary to store client subprocess objects (e.g., from `stdio_client`), keyed by `client_id`. This helps in targeted shutdown.
            *   `async start_client(self, client_config: ClientConfig, security_manager: SecurityManager) -> ClientSession`:
                *   Logic to resolve GCP secrets using `security_manager` (similar to current `MCPHost._initialize_client`).
                *   Set up `StdioServerParameters` with the client's command and environment.
                *   Use `self.exit_stack.enter_async_context(stdio_client(server_params))` to start the server process and get transport. Store the process handle in `self.client_processes`.
                *   Use `self.exit_stack.enter_async_context(ClientSession(transport[0], transport[1]))` to create the session.
                *   Store the session in `self.active_clients`.
                *   Return the `ClientSession`.
            *   `async shutdown_client(self, client_id: str)`:
                *   Attempt to gracefully close the `ClientSession` if it exists in `self.active_clients`.
                *   Terminate/kill the subprocess associated with `client_id` from `self.client_processes`.
                *   Remove the client from `self.active_clients` and `self.client_processes`.
                *   Handle potential errors during shutdown.
            *   `async shutdown_all_clients(self)`:
                *   Iterate through all `client_id`s in `self.active_clients`.
                *   Call `self.shutdown_client(client_id)` for each.
                *   Clear `self.active_clients` and `self.client_processes`.
    *   **Testing (`tests/host/foundation/test_client_manager.py` - new file):**
        *   Unit tests for `ClientManager`:
            *   Test `start_client` successfully starts a mock client process and session.
            *   Test `shutdown_client` correctly stops a specific client.
            *   Test `shutdown_all_clients` stops all active clients.
            *   Test error handling during client start/stop.
            *   Mock `AsyncExitStack`, `stdio_client`, `ClientSession`, and `SecurityManager` as needed.

**1.2. Refactor `MCPHost` to Use `ClientManager`**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   In `MCPHost.__init__`:
            *   Remove `self._clients: Dict[str, ClientSession] = {}`.
            *   Remove `self._exit_stack = AsyncExitStack()`.
            *   Instantiate `self.client_manager = ClientManager(exit_stack=self._exit_stack)` (Note: `MCPHost` will now need to create and pass its `AsyncExitStack` to `ClientManager` or `ClientManager` creates its own. Let's plan for `MCPHost` to own the `AsyncExitStack` and pass it to `ClientManager`).
                *Correction:* `MCPHost` should instantiate an `AsyncExitStack` and pass it to the `ClientManager`. The `ClientManager` will then use this shared `AsyncExitStack` for managing the lifecycles of client processes and sessions it starts.
        *   Modify `MCPHost._initialize_client(self, config: ClientConfig)`:
            *   Delegate the actual client starting process to `self.client_manager.start_client(config, self._security_manager)`.
            *   The `ClientSession` returned by `start_client` will be used for `InitializeRequest`, `InitializedNotification`, registering roots, and registering server capabilities with `MessageRouter`.
            *   The `ClientSession` should *not* be stored in `MCPHost._clients` anymore, as `ClientManager` now holds this. `MCPHost` might need access to these sessions for discovery, so `ClientManager` should provide a way to get active sessions (e.g., `self.client_manager.active_clients`).
            *   Tool, prompt, and resource discovery/registration logic will use the session obtained from `ClientManager`.
        *   Add `async client_shutdown(self, client_id: str)`:
            *   Calls `await self.client_manager.shutdown_client(client_id)`.
            *   Potentially unregister tools/prompts/resources associated with this client from `ToolManager`, `PromptManager`, `ResourceManager`, and `MessageRouter`. This needs careful consideration to avoid issues if components are shared or if managers expect to handle this. For now, focus on process shutdown. Managers should ideally be robust to clients disappearing.
        *   Add `async shutdown_all_clients(self)`:
            *   Calls `await self.client_manager.shutdown_all_clients()`.
            *   Similar consideration for unregistering components from managers.
        *   Modify `MCPHost.shutdown()`:
            *   Ensure it calls `await self.shutdown_all_clients()` *before* `self._exit_stack.aclose()`. The `ClientManager`'s shutdown methods will handle individual client process/session cleanup using the `AsyncExitStack`. `MCPHost.shutdown()` then calls `aclose()` on the stack itself.
        *   Update `MCPHost.is_client_registered(self, client_id: str)`:
            *   Check `client_id in self.client_manager.active_clients`.
        *   Update `MCPHost.register_client(self, config: ClientConfig)` (dynamic registration):
            *   Call `await self._initialize_client(config)` which now uses `ClientManager`.
    *   **Testing (`tests/host/test_host_basic.py`, `tests/host/test_host_dynamic_registration.py`):**
        *   Update existing tests to mock `ClientManager` and verify `MCPHost` correctly delegates client operations.
        *   Test `MCPHost.client_shutdown()` and `MCPHost.shutdown_all_clients()`.
        *   Verify `MCPHost.shutdown()` correctly calls `ClientManager.shutdown_all_clients()`.

## II. HostManager Enhancements (`unload_project`, `change_project`)

**Goal:** Implement methods in `HostManager` to unload the current project (shutting down its clients) and to change to a new project.

**2.1. Implement `unload_project` in `HostManager`**
    *   **File:** `src/host_manager.py`
    *   **Action:**
        *   Add `async def unload_project(self):`
            *   Log the start of the unloading process.
            *   If `self.host` exists:
                *   Call `await self.host.shutdown_all_clients()`.
                *   Call `await self.host.shutdown()` to fully clean up the `MCPHost` instance (this will also call `shutdown_all_clients` again if not designed carefully, ensure `MCPHost.shutdown` is idempotent or `shutdown_all_clients` is only called once effectively. The `ClientManager`'s `shutdown_all_clients` should be idempotent).
                    *Clarification:* `unload_project` should call `self.host.shutdown()` which in turn calls `self.host.shutdown_all_clients()` (via `ClientManager`). This ensures a full cleanup of the `MCPHost` instance.
            *   Set `self.host = None`.
            *   Clear configuration stores:
                *   `self.current_project = None`
                *   `self.agent_configs.clear()`
                *   `self.llm_configs.clear()`
                *   `self.workflow_configs.clear()`
                *   `self.custom_workflow_configs.clear()`
            *   Log completion of unloading.
    *   **Testing (`tests/orchestration/test_host_manager_unit.py` - new or existing):**
        *   Test `unload_project`:
            *   Mocks `MCPHost` and its `shutdown` method.
            *   Verifies `host.shutdown()` is called.
            *   Verifies `current_project` and config dictionaries are cleared.
            *   Verifies `self.host` is set to `None`.

**2.2. Implement `change_project` in `HostManager`**
    *   **File:** `src/host_manager.py`
    *   **Action:**
        *   Add `async def change_project(self, new_project_config_path: Path):`
            *   Log attempt to change project to `new_project_config_path`.
            *   Call `await self.unload_project()`.
            *   Update `self.config_path = new_project_config_path`.
            *   Call `await self.initialize()`. This will:
                *   Load the new project using `self.project_manager.load_project(self.config_path)`.
                *   Populate `self.current_project` and config dictionaries.
                *   Create and initialize a new `MCPHost` instance with the new project's clients.
                *   Re-initialize `self.execution` facade.
            *   Log successful project change.
    *   **Testing (`tests/orchestration/test_host_manager_unit.py`):**
        *   Test `change_project`:
            *   Mocks `unload_project` and `initialize` methods.
            *   Verifies `unload_project` is called first.
            *   Verifies `self.config_path` is updated.
            *   Verifies `initialize` is called with the new path context.
        *   Integration-style test (if feasible within unit test scope or in `test_host_manager.py`):
            *   Initialize `HostManager` with project A.
            *   Call `change_project` with project B.
            *   Verify that `HostManager` state reflects project B (e.g., different `current_project.name`, different client configs loaded into the new `MCPHost` mock).

## III. API Endpoint Additions

**Goal:** Add new API endpoints to `api.py` for changing projects and creating new projects.

**3.1. Define/Implement `ProjectManager.create_project_file()`**
    *   **File:** `src/config/project_manager.py`
    *   **Action:**
        *   Add `def create_project_file(self, project_name: str, project_description: str, project_file_path: Path, client_configs: Optional[List[ClientConfig]] = None, llm_configs: Optional[List[LLMConfig]] = None, agent_configs: Optional[List[AgentConfig]] = None, simple_workflow_configs: Optional[List[WorkflowConfig]] = None, custom_workflow_configs: Optional[List[CustomWorkflowConfig]] = None, overwrite: bool = False) -> ProjectConfig:`
            *   Takes project metadata and optionally lists of component *configurations* (not just IDs).
            *   Constructs a `ProjectConfig` model instance.
            *   Serializes the `ProjectConfig` to a JSON string.
            *   Writes the JSON string to `project_file_path`. Handles `overwrite` flag.
            *   The project file should store components by their full configuration if provided inline, or by reference if a system for pre-defined, globally available components is used (for now, assume inline or simple references to components that `ComponentManager` would find by ID if they were pre-existing files).
            *   This method primarily creates the project *file*. It doesn't load it into the `HostManager`.
            *   Consider if it should also save the inline component definitions as separate component files using `ComponentManager` if they don't already exist. For simplicity in this phase, let's assume `create_project_file` primarily creates the project JSON. If components are defined inline, they stay inline in the project file.
    *   **Testing (`tests/config/test_project_manager.py`):**
        *   Test `create_project_file`:
            *   Verify it creates a valid project JSON file at the specified path.
            *   Test with and without optional component lists.
            *   Test `overwrite` behavior.
            *   Verify the content of the created file matches the expected `ProjectConfig` structure.

**3.2. Add `/change_project` Endpoint**
    *   **File:** `src/bin/api/api.py` (or a new route file, e.g., `project_api.py`, included in `api.py`)
    *   **Action:**
        *   Define a Pydantic model for the request body, e.g., `ChangeProjectRequest(project_config_path: str)`.
        *   Create a new POST endpoint, e.g., `/projects/change`.
        *   Depends on `get_host_manager`.
        *   The endpoint handler will:
            *   Take `ChangeProjectRequest` as input.
            *   Convert `project_config_path` string to `Path`.
            *   Call `await manager.change_project(Path(request.project_config_path))`.
            *   Return a success response.
            *   Handle potential errors (e.g., new project file not found, errors during `unload_project` or `initialize`).
    *   **Testing (`tests/api/routes/test_project_api.py` - new file):**
        *   Test `/change_project` endpoint:
            *   Mock `HostManager.change_project`.
            *   Verify the endpoint calls `change_project` with the correct path.
            *   Test successful response.
            *   Test error responses (e.g., invalid path, underlying `HostManager` errors).

**3.3. Add `/new_project` Endpoint**
    *   **File:** `src/bin/api/api.py` (or `project_api.py`)
    *   **Action:**
        *   Define a Pydantic model for the request body, e.g., `NewProjectRequest` including `project_name: str`, `project_description: str`, `project_filename: str` (e.g., "my_new_project.json"), and optionally lists for initial `ClientConfig`, `LLMConfig`, `AgentConfig` objects.
        *   Create a new POST endpoint, e.g., `/projects/new`.
        *   Depends on `get_host_manager` (to access `ProjectManager` and `ComponentManager` via `manager.project_manager`).
        *   The endpoint handler will:
            *   Determine the full path for the new project file (e.g., in `config/projects/`).
            *   Call `manager.project_manager.create_project_file(...)` with data from the request.
            *   If successful, call `await manager.change_project(new_project_file_path)`.
            *   Return a success response including the path to the new project file.
            *   Handle potential errors (file creation errors, `change_project` errors).
    *   **Testing (`tests/api/routes/test_project_api.py`):**
        *   Test `/new_project` endpoint:
            *   Mock `ProjectManager.create_project_file` and `HostManager.change_project`.
            *   Verify `create_project_file` is called with correct parameters.
            *   Verify `change_project` is called with the path of the newly created file.
            *   Test successful response.
            *   Test error handling.

## IV. Documentation & Final Review

1.  **Update Documentation:**
    *   Update `docs/plans/overarching_plan.md` to reflect the completion of Phase 3 and any deviations or refinements made during implementation.
    *   Update relevant design documents (e.g., `docs/design/architecture_overview.md` or similar) if the introduction of `ClientManager` or project lifecycle changes has significant architectural impact.
    *   Ensure all new/modified code has clear docstrings and comments.
2.  **Final Review:**
    *   Conduct a thorough review of all changed files for correctness, consistency, adherence to project coding standards, and proper error handling.
    *   Manually test the project switching and new project creation functionality via the API if possible.

This plan provides a structured approach to implementing the Phase 3 features. Each step includes actions and testing considerations to ensure robustness.
