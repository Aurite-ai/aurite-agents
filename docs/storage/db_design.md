# Database Integration Design Document

**Version:** 0.1
**Date:** 2025-05-05
**Status:** Draft

## 1. Goals & Motivation

- Provide an optional, persistent storage mechanism for agent/workflow configurations beyond JSON files.
- Offer a more scalable and queryable solution for storing agent conversation history compared to individual files.
- Lay the foundation for future features like programmatic configuration management and advanced history analysis.
- Maintain compatibility with the existing file-based configuration system for users who don't need or want database persistence.

## 2. Proposed Solution

### 2.1. Feature Flag

- Introduce a new environment variable/setting (e.g., `AURITE_ENABLE_DB=false`).
- This flag will control whether database interactions are enabled. Default to `false` to maintain current behavior.
- Potentially add more granular flags later (e.g., `AURITE_DB_STORE_CONFIGS`, `AURITE_DB_STORE_HISTORY`) if needed.

### 2.2. Database Choice

- **Primary Choice:** Use **PostgreSQL**.
    - Robust, feature-rich relational database suitable for development and production.
    - Requires a running PostgreSQL server instance.
    - Connection details (host, port, user, password, dbname) will be configured via environment variables (e.g., `AURITE_DB_HOST`, `AURITE_DB_PORT`, etc.).
- **Dependencies:** Requires `psycopg2-binary` or `psycopg` driver.

### 2.3. Storage Abstraction (`src/storage/`)

- Create a dedicated `src/storage/` directory.
- **`db_connection.py`:** Handles establishing the SQLAlchemy engine and session management based on environment variables.
- **`db_models.py`:** Defines the SQLAlchemy ORM models representing the database schema (see Section 3). These models will align with, but be distinct from, the Pydantic configuration models in `src/host/models.py`.
- **`db_manager.py` (`StorageManager` class):**
    - This class encapsulates all database operations (CRUD for configs, history management).
    - It uses the connection/session logic from `db_connection.py` and the ORM models from `db_models.py`.
    - It provides the interface for the rest of the application (e.g., `HostManager`, `Agent`) to interact with storage.
    - `StorageManager` will be initialized by `HostManager` if `AURITE_ENABLE_DB` is true, receiving necessary connection info.
    - `HostManager` and `Agent` interact with the `StorageManager` instance.

### 2.4. Configuration Storage

- **Initial Load:**
    - `HostManager` still loads the primary configuration from the JSON file specified by `PROJECT_CONFIG_PATH`.
    - If `AURITE_ENABLE_DB` is true, after successful loading and validation from JSON, `HostManager` uses `StorageManager` to **sync** these configurations to the database (e.g., `storage_manager.sync_configs(agents=self.agent_configs, ...)`). This could involve inserting or updating records based on component names.
- **Dynamic Registration:**
    - When `HostManager.register_client/agent/workflow` is called:
        - The configuration is first validated and added to the in-memory dictionaries as usual.
        - If `AURITE_ENABLE_DB` is true, `HostManager` calls the `StorageManager` to add/update the corresponding configuration in the database (e.g., `storage_manager.save_agent_config(agent_config)`).
- **Loading from DB (Future Consideration):**
    - We could add a mechanism where the JSON config references DB entries by ID, or a `HostManager` method `load_configs_from_db()`. This requires further design. For now, JSON remains the primary source of truth at startup.

### 2.5. Agent History Storage

- In `src/agents/agent.py::Agent.execute_agent`:
    - Before starting execution, if `self.config.include_history` and `host_instance.storage_manager` (passed via `HostManager`/`ExecutionFacade`) is available:
        - Call `storage_manager.load_history(agent_name=self.config.name)` to retrieve previous conversation turns.
        - Prepend retrieved history to the `conversation` list.
    - After execution completes (or after each turn if streaming), if history is enabled and `storage_manager` exists:
        - Call `storage_manager.save_history_turn(agent_name=self.config.name, turn_data=...)` or `save_full_history(...)` to persist the latest state.
        - Decision: Store individual turns (Option 1 below) for flexibility.
    - **Responsibility:** The `Agent` class itself will be responsible for interacting with the `StorageManager` to load and save its history when `config.include_history` is true and the DB is enabled. This keeps the history logic close to its usage and avoids complicating the `HostManager` or `Facade`. The `StorageManager` instance will be passed down through the `Facade` to the `Agent`.

## 3. Schema Design (PostgreSQL - SQLAlchemy Models in `src/storage/db_models.py`)

- Database schema will be defined using SQLAlchemy ORM models in `src/storage/db_models.py`.
- These models will map Python classes to database tables (e.g., `AgentConfigDB`, `WorkflowConfigDB`, `AgentHistoryDB`).
- They need to align closely with the Pydantic models in `src/host/models.py` but will handle database-specific concerns like primary keys, foreign keys (potentially later), indexing, and data type mapping (e.g., storing lists/dicts as JSONB in PostgreSQL).
- Timestamps (`created_at`, `last_updated`) should be included for tracking configuration changes.
- The `AgentHistoryDB` table should store individual turns, likely including `agent_name`, `timestamp`, `role`, and `content` (as JSONB).

*(Detailed SQLAlchemy model definitions are deferred to the implementation phase).*
