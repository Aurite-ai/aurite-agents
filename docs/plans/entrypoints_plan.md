# Overarching Plan: Dynamic Registration, Entrypoints, and Documentation

**Objective:** Enhance the Aurite Agent Framework by adding dynamic registration capabilities, refactoring the main API into a dedicated entrypoint, creating new CLI and worker entrypoints, testing these additions, and updating documentation.

**Owner:** Ryan Wilcox (assisted by Gemini)

**Status:** Proposed

**Related Docs:**
*   [Host Manager Implementation Plan](docs/plans/completed/4-09-25/host_manager_implementation_plan.md)
*   [Host Implementation](docs/host/host_implementation.md)
*   [Dynamic Registration Plan](docs/plans/dynamic_registration_plan.md) (To be created)
*   [Framework Guide](docs/framework_guide.md) (To be created)
*   [README.md](README.md) (To be updated)

**Background:**
The framework currently initializes all clients, agents, and workflows at startup based on a static configuration file. To increase flexibility, we need to allow dynamic registration of these components at runtime. Additionally, the current `main.py` serves as the API entrypoint; we want to refactor this and introduce alternative entrypoints (CLI, Worker) for different operational modes.

**High-Level Tasks & Order:**

1.  **Implement Dynamic Registration (HostManager & API):**
    *   Modify `HostManager` to support adding `ClientConfig`, `AgentConfig`, and `WorkflowConfig` after initial `initialize()`.
    *   Modify `MCPHost` to handle the initialization of dynamically added clients, including managing their lifecycle with the `AsyncExitStack`.
    *   Add new API endpoints to `main.py` (soon to be `api.py`) to expose this registration functionality.
    *   *Files Involved:* `src/host_manager.py`, `src/host/host.py`, `src/main.py`, `src/host/models.py`.
    *   *Detailed Plan:* `docs/plans/dynamic_registration_plan.md`

2.  **Test Dynamic Registration (Postman/Newman):**
    *   Expand the existing Postman collection (`tests/api/main_server.postman_collection.json`) with new requests to test the dynamic registration endpoints created in Task 1.
    *   Include tests for successful registration and error cases (e.g., duplicates, invalid data).
    *   Use Newman to run the updated collection and verify functionality.
    *   *Files Involved:* `tests/api/main_server.postman_collection.json`.

3.  **Refactor Entrypoints & Add CLI/Worker:**
    *   **3a. Refactor API:**
        *   Create `src/bin/` directory.
        *   Move `src/main.py` to `src/bin/api.py`.
        *   Update imports and any necessary references (e.g., `pyproject.toml` if script paths are defined there, uvicorn command).
    *   **3b. Create CLI Entrypoint:**
        *   Create `src/bin/cli.py`.
        *   Use a library like `argparse` or `typer` to define commands.
        *   Commands should allow initializing `HostManager` (using a specified config file) and then:
            *   Registering clients, agents, workflows (potentially reading definitions from files or stdin).
            *   Executing agents, simple workflows, custom workflows by name.
        *   Handle `HostManager` initialization and shutdown cleanly.
    *   **3c. Create Worker Entrypoint (Requires Redis):**
        *   **Prerequisite:** Install Redis server locally.
        *   Create `src/bin/worker.py`.
        *   Use a Redis client library (e.g., `redis-py`).
        *   The worker should:
            *   Initialize `HostManager`.
            *   Connect to Redis and listen on a specific stream/channel.
            *   Process incoming messages containing component configurations (Client, Agent, Workflow) and an action (`register` or `execute`).
            *   Call the appropriate `HostManager` methods based on the message.
            *   Handle errors and potentially publish results back to Redis.
        *   Define the message format for Redis interactions.
    *   *Files Involved:* `src/main.py`, `src/bin/api.py` (new), `src/bin/cli.py` (new), `src/bin/worker.py` (new), `pyproject.toml` (potentially).

4.  **Update Documentation:**
    *   **4a. Update README:** Modify `README.md` to reflect the new entrypoints and overall structure.
    *   **4b. Create Framework Guide:** Create `docs/framework_guide.md` explaining:
        *   The purpose of the framework.
        *   How to configure the system (`config/*.json`).
        *   How to run each entrypoint (`api.py`, `cli.py`, `worker.py`) with examples.
        *   How dynamic registration works (API, CLI, Worker).
    *   *Files Involved:* `README.md`, `docs/framework_guide.md` (new).

**Proposed Execution Order:** Task 1 -> Task 2 -> Task 3a -> Task 3b -> Task 3c (pending Redis setup) -> Task 4.
