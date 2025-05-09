# Logging Refactor Implementation Plan

**Objective:** Refactor application logging to reduce INFO-level clutter in the terminal output, primarily by changing some INFO logs to DEBUG and consolidating others. MCP server-specific logging (handled by a different logger) will be ignored for now as per the request.

**Key Areas & Desired Logging Behavior:**

1.  **`HostManager` / `Host` Initialization:**
    *   **Current:** Multiple INFO lines detailing project loading, DB persistence status, MCP Host initialization steps, and individual client initializations.
    *   **Desired:**
        *   One INFO line summarizing the number of clients initialized and the number of agent configs loaded/stored by the Host.
        *   One INFO line confirming the `Host` (MCP Host) initialized properly.
        *   One INFO line confirming the `HostManager` initialized properly.

2.  **`ComponentManager` & `ProjectManager` Initialization:**
    *   **Current:**
        *   `ComponentManager`: Multiple INFO lines for each component type loaded, then one INFO for `ComponentManager` initialization.
        *   `ProjectManager`: One INFO line for `ProjectManager` initialization.
    *   **Desired:**
        *   One INFO line in `ProjectManager.__init__` confirming its proper initialization. This line should include component type counters from `ComponentManager`.
            *   This will require adding a method to `ComponentManager` to expose these counts.

3.  **General Logging Refinements (Startup):**
    *   Most detailed, step-by-step INFO logs during startup will be changed to DEBUG.
    *   Core lifecycle messages (e.g., server starting, HostManager initialized) will remain INFO.
    *   Specific logs to change from INFO to DEBUG:
        *   `src.bin.dependencies:get_server_config:34 - Server configuration loaded successfully.`
        *   `src.config.component_manager:_load_all_components:146 - Loaded X components of type 'Y' ...` (These will be summarized).
        *   `src.config.component_manager:__init__:72 - ComponentManager initialized and all components loaded.` (Will be covered by ProjectManager log).
        *   `src.host_manager:__init__:104 - Database persistence is disabled...`
        *   `src.host_manager:initialize:121 - Initializing HostManager with project config...`
        *   `src.config.project_manager:load_project:67 - Loading project configuration from...`
        *   `src.config.project_manager:load_project:149 - Successfully loaded and resolved project 'DefaultMCPHost'.`
        *   `src.config.project_manager:load_project:151 - Project 'DefaultMCPHost' set as active in ProjectManager.`
        *   `src.host_manager:initialize:134 - Project 'DefaultMCPHost' loaded successfully and set as active.`
        *   `src.host.host:initialize:98 - Initializing MCP Host...`
        *   `src.host.foundation.clients:start_client:58 - Starting client: X...`
        *   `src.host.foundation.clients:start_client:114 - Client X started and session established successfully.`
        *   `src.host.foundation.routing:register_server:120 - Registered server 'X' ...`
        *   `src.host.host:_initialize_client:228 - Client 'X' initialized. Tools: [...], Prompts: [...], Resources: [...]` (This data will be aggregated).
        *   `src.host_manager:initialize:168 - MCPHost initialized successfully.`

4.  **General Logging Refinements (Shutdown):**
    *   Most detailed INFO logs during shutdown will be changed to DEBUG.
    *   Key summary messages (e.g., HostManager shutdown complete, Host shutdown complete) will remain INFO.
    *   Specific logs to change from INFO to DEBUG:
        *   `src.host_manager:shutdown:242 - Shutting down HostManager...`
        *   `src.host.host:shutdown:698 - Shutting down MCP Host...`
        *   And all subsequent detailed shutdown steps within `Host` and `HostManager` (e.g., shutting down layers, managers, clients).

**Implementation Steps (Numbered & Sequential):**

1.  **Modify `src.config.component_manager.py`:**
    *   In `_load_all_components` method: Change `logger.info` to `logger.debug`.
    *   In `__init__` method: Change `logger.info("ComponentManager initialized and all components loaded.")` to `logger.debug`.
    *   Add a new public method `get_component_counts(self) -> dict[str, int]:` that returns a dictionary of component types to their counts (e.g., `self.component_counts` which should be populated in `_load_all_components`). Ensure `self.component_counts` is initialized (e.g. `self.component_counts: Dict[str, int] = {}`) and updated correctly.

2.  **Modify `src.config.project_manager.py`:**
    *   In `__init__` method:
        *   Replace `logger.info("ProjectManager initialized.")` with a new consolidated INFO message:
            ```python
            component_counts = self.component_manager.get_component_counts()
            count_str = ", ".join(f"{count} {ctype}" for ctype, count in component_counts.items())
            logger.info(f"ProjectManager initialized, ComponentManager loaded: {count_str if count_str else '0 components'}.")
            ```
    *   In `load_project` method: Change all existing `logger.info` calls to `logger.debug`.

3.  **Modify `src.host.host.py`:**
    *   In `initialize` method (around line 98): Change `logger.info("Initializing MCP Host...")` to `logger.debug`.
    *   In `_initialize_client` method (around line 228): Change `logger.info(f"Client '{client_config.name}' initialized. ...")` to `logger.debug`.
    *   In `initialize` method, after the loop for initializing clients (e.g., after `await self._initialize_client(client_config)` loop):
        *   Add a new INFO log:
            ```python
            num_clients = len(self.client_manager.clients)
            # Assuming agent configs are part of the project_config loaded into the host
            num_agent_configs = len(self.project_config.agents) if self.project_config and self.project_config.agents else 0
            logger.info(f"Host initialized {num_clients} clients and loaded {num_agent_configs} agent configs.")
            ```
        *   The existing `logger.info("MCP Host initialization complete")` (around line 121) should remain as INFO.
    *   In `shutdown` method and its called sub-methods (e.g., `shutdown_all_clients`, and internal layer shutdowns): Change all detailed step-by-step INFO logs to `logger.debug`. Keep `logger.info("MCP Host shutdown complete")` (around line 729) as INFO.

4.  **Modify `src.host_manager.py`:**
    *   In `__init__` method (around line 104): Change `logger.info("Database persistence is disabled...")` to `logger.debug`.
    *   In `initialize` method:
        *   Change `logger.info(f"Initializing HostManager with project config: {project_config_path}...")` (around line 121) to `logger.debug`.
        *   Change `logger.info(f"Project '{self.project_manager.active_project_name}' loaded successfully and set as active.")` (around line 134) to `logger.debug`.
        *   Change `logger.info("MCPHost initialized successfully.")` (around line 168) to `logger.debug`.
        *   The existing `logger.info("HostManager initialization complete.")` (around line 197) should remain as INFO.
    *   In `shutdown` method: Change detailed INFO logs like `logger.info("Shutting down HostManager...")` (around line 242), `logger.info("Managed MCPHost shutdown successfully.")` (around line 246), and `logger.info("HostManager internal state cleared.")` (around line 300) to `logger.debug`. Keep `logger.info("HostManager shutdown complete.")` (around line 301) as INFO.

5.  **Modify `src.host.foundation.clients.py`:**
    *   In `start_client` method: Change `logger.info(f"Starting client: {client_name}...")` (around line 58) and `logger.info(f"Client {client_name} started and session established successfully.")` (around line 114) to `logger.debug`.
    *   In `shutdown_client` and `shutdown_all_clients` methods: Change all `logger.info` calls related to client shutdown processes to `logger.debug`.

6.  **Modify `src.host.foundation.routing.py`:**
    *   In `register_server` method (around line 120): Change `logger.info(...)` to `logger.debug`.
    *   In `shutdown` method (around line 128): Change `logger.info(...)` to `logger.debug`.

7.  **Modify `src.host.foundation.security.py`:**
    *   In `_setup_cipher` method (around line 141): The log `logger.info("Encryption key is not valid base64, deriving key from string.")` can remain INFO as it indicates a specific configuration fallback.

8.  **Modify `src.bin.dependencies.py`:**
    *   In `get_server_config` method (around line 34): Change `logger.info("Server configuration loaded successfully.")` to `logger.debug`.

9.  **Modify `src.bin.api.api.py` (Lifespan and Start logging):**
    *   The Uvicorn/FastAPI specific logs like `INFO: Started server process [...]`, `INFO: Waiting for application startup.`, etc., are from Uvicorn itself and generally should not be altered from within this application's codebase.
    *   `logger.info(f"Starting Uvicorn server on {host}:{port} with {workers} worker(s)...")` (around line 372) - Keep INFO.
    *   In `lifespan` function:
        *   `logger.info("Starting FastAPI server and initializing HostManager...")` (around line 57) - Keep INFO.
        *   `logger.info("HostManager initialized successfully.")` (around line 68) - Keep INFO.
        *   `logger.info("Shutting down HostManager...")` (around line 93) - Keep INFO.
        *   `logger.info("HostManager shutdown complete.")` (around line 96) - Keep INFO.
        *   `logger.info("FastAPI server shutdown sequence complete.")` (around line 105) - Keep INFO.

10. **Modify Resource Management Shutdown Logs (`src/host/resources/*.py`):**
    *   In `shutdown` methods of `prompts.py` (around line 143), `resources.py` (around line 152), and `tools.py` (around line 516): Change `logger.info` calls to `logger.debug`.

**Verification:**
*   After all changes are implemented, run the `start-api` command.
*   Carefully observe the terminal output.
*   Verify that INFO-level logs are significantly reduced and align with the desired patterns outlined above.
*   Specifically check for the new consolidated INFO messages for `ProjectManager`, `Host` (clients/agents count, then host init complete), and `HostManager`.
*   Ensure that essential FastAPI/Uvicorn lifecycle INFO messages and critical warnings (like encryption key generation) remain visible.
*   Confirm that shutdown INFO messages are minimal and summarize the key shutdown events.
