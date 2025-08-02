# Security Policy for Aurite Agents

The Aurite Agents team and community take the security of the framework seriously. We appreciate your efforts to responsibly disclose your findings, and will make every effort to acknowledge your contributions.

## Reporting a Vulnerability

Please **DO NOT** report security vulnerabilities through public GitHub issues.

Instead, please report them by sending an email to `support@aurite.ai`.

Please include the requested information listed below (as much as you can provide) to help us better understand the nature and scope of the possible issue:

*   Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
*   Full paths of source file(s) related to the manifestation of the issue
*   The location of the affected source code (tag/branch/commit or direct URL)
*   Any special configuration required to reproduce the issue
*   Step-by-step instructions to reproduce the issue
*   Proof-of-concept or exploit code (if possible)
*   Impact of the issue, including how an attacker might exploit the issue

This information will help us triage your report more quickly.

## Security Mechanisms & Configuration

This section details important security-related configurations and mechanisms within the Aurite Agents framework.

### 1. Encryption Key (`AURITE_MCP_ENCRYPTION_KEY`)

The `AURITE_MCP_ENCRYPTION_KEY` environment variable is critical for securing sensitive data that might be encrypted by the framework's `SecurityManager` (located in `src/host/foundation/security.py`).

*   **Purpose:** This key is used for symmetric encryption (via Fernet) of credentials or other sensitive information that the `SecurityManager` is tasked to protect.
*   **Auto-generation:** If this environment variable is not set when the framework starts, a new encryption key will be **auto-generated**. This is provided for convenience, especially for quick local testing or initial setup.
*   **CRITICAL FOR PERSISTENCE:** If you rely on an auto-generated key, any data encrypted with it will become **inaccessible** if the application restarts and generates a new key.
*   **Recommendation for Production/Persistent Deployments:** For any deployment that is intended to be persistent, or if you plan to use features that rely on data encrypted by the `SecurityManager`, you **MUST** set `AURITE_MCP_ENCRYPTION_KEY` to a strong, persistent, and unique key.
*   **Key Format:** The key should be a URL-safe base64-encoded 32-byte string. You can generate such a key using Python:
    ```python
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    print(key.decode())
    ```
    Store this generated key securely and set it as the `AURITE_MCP_ENCRYPTION_KEY` environment variable.
*   **`.env.example`:** This variable is included and commented in the `.env.example` file as a reminder.

### 2. GCP Secret Manager Usage

The framework can optionally resolve secrets from Google Cloud Platform (GCP) Secret Manager.

*   **Enabling:** This feature is controlled by the `USE_SECRETS_MANAGER` environment variable (see `.env.example`). Set it to `true` to enable.
*   **Prerequisites:**
    *   **Application Default Credentials (ADC):** The environment where the Aurite Agents framework is running must have Google Cloud ADC configured. This typically involves running `gcloud auth application-default login` or setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to a service account key file.
    *   **IAM Permissions:** The identity associated with the ADC (e.g., your user account, or the service account) **MUST** have the `Secret Manager Secret Accessor` IAM role (or equivalent permissions) for each specific secret in GCP Secret Manager that you configure the framework to use.
*   **Configuration:** Secrets to be fetched are defined in the `ClientConfig` under the `gcp_secrets` list, specifying the GCP secret resource ID and the environment variable name it should populate for the MCP server process.

### 3. In-Memory Credential Storage (`SecurityManager._credentials`)

The `SecurityManager` component currently includes an internal, in-memory dictionary (`_credentials`) for storing credentials that it might be asked to manage via its `store_credential` method.

*   **Encryption:** Credentials stored via this mechanism are encrypted using the `AURITE_MCP_ENCRYPTION_KEY` before being held in this in-memory store.
*   **Intended Use & Limitations:**
    *   This in-memory store is primarily intended for **development and testing purposes**, or for scenarios where the framework might temporarily handle a credential that doesn't warrant full external vault integration for a specific use case.
    *   It is **NOT recommended** for storing highly sensitive production credentials that require robust, persistent, and audited storage solutions.
    *   For production environments requiring the framework to manage and persist sensitive credentials beyond what's passed for immediate MCP server use, integration with a dedicated secure vault service (e.g., HashiCorp Vault, Azure Key Vault, AWS Secrets Manager) is the best practice. The current `SecurityManager` provides the encryption primitives but not the persistent secure storage backend.
*   **Data Lifetime:** Credentials stored in this in-memory dictionary are cleared when the `SecurityManager` (and thus the `MCPHost`) is shut down.

### 4. Root Access Control (`RootManager`)

The `RootManager` (located in `src/host/foundation/roots.py`) is responsible for managing **Root Configurations** (`RootConfig`) for each connected MCP client.

*   **Purpose:** Root configurations define the permissible operational boundaries or namespaces (typically as base URIs) within which an MCP client is allowed to operate or provide resources. For example, a file system client might be rooted at `file:///mnt/shared/`, meaning it can only list or access files and directories under that path.
*   **Registration:** `MCPHost` registers these roots (defined in `ClientConfig`) with the `RootManager` during client initialization.
*   **Enforcement:** While `RootManager` stores these definitions, the actual enforcement of whether a requested resource URI (e.g., in a `read_resource` call) falls within a client's allowed roots is typically performed by the `ResourceManager` (in `src/host/resources/resources.py`), which consults the `RootManager`.
*   **Security Implication:** Properly configured roots are essential for sandboxing clients and preventing them from accessing unauthorized resources or areas of the system. Misconfigured or overly permissive roots can pose a security risk.

### 5. Request Routing & Filtering (`MessageRouter`, `FilteringManager`, `MCPHost`)

Controlled access to tools, prompts, and resources is managed through a combination of components:

*   **`MessageRouter` (`src/host/foundation/routing.py`):**
    *   Acts as a central registry, mapping component names (e.g., tool names, prompt names) or resource URIs to the list of client IDs that provide them.
    *   It does not, by itself, make security decisions but provides the foundational data for such decisions.
*   **`FilteringManager` (`src/host/filtering.py`):**
    *   Provides stateless functions used by `MCPHost` and Resource Managers to apply filtering rules.
    *   **Client-Level Exclusions:** During component registration, `FilteringManager` checks the `ClientConfig.exclude` list to prevent globally disallowed components from a specific client from being registered.
    *   **Agent-Specific Access (`AgentConfig`):** When `MCPHost` processes a request from an agent:
        *   `AgentConfig.client_ids`: `FilteringManager` helps filter the list of potential clients (obtained from `MessageRouter`) down to only those explicitly allowed for the requesting agent.
        *   `AgentConfig.exclude_components`: `FilteringManager` helps ensure that an agent cannot use a component explicitly excluded in its configuration, even if provided by an allowed client.
*   **`MCPHost` (`src/host/host.py`):**
    *   Orchestrates the use of `MessageRouter` to find potential providers and then `FilteringManager` to apply agent-specific access rules before dispatching a request to a resource manager (e.g., `ToolManager`).

*   **Security Implication:** This layered approach ensures that agents can only access clients and specific components they are explicitly permissioned for via their `AgentConfig`, providing a critical access control mechanism.

### 6. Environment Variable Handling for MCP Server Subprocesses

When `MCPHost` initializes an MCP client (which typically runs as a separate Python subprocess via `mcp.stdio_client`), it takes care to prepare the environment for that subprocess:

*   **Base Environment:** The subprocess inherits a copy of the environment from the main Aurite Agents host process.
*   **GCP Secret Injection:** If `ClientConfig.gcp_secrets` are defined and `USE_SECRETS_MANAGER` is enabled, the `SecurityManager` resolves these secrets, and they are then **added to or overwrite existing variables in the environment specific to that MCP server subprocess.** This is handled by `ClientManager` before launching the subprocess.
*   **Mechanism:** These environment variables are passed to the subprocess using standard operating system mechanisms for process creation (typically via the `env` parameter in Python's `subprocess` module, which is used by `anyio` and `mcp.stdio_client`).
*   **Security Considerations:**
    *   **Isolation:** Environment variables are generally isolated to the specific child process they are passed to. They are not directly accessible by other MCP server subprocesses or the host process after launch (unless the host process explicitly reads them back, which it doesn't).
    *   **Logging:** The Aurite Agents framework (specifically `ClientManager` and `MCPHost`) **does not log the values of these environment variables** (including resolved secrets) during the startup process. It logs that secrets *are* being injected and how many, but not their content.
    *   **MCP Server Script Responsibility:** Once the MCP server subprocess is launched with these environment variables, it is the responsibility of the MCP server script itself to handle them securely (e.g., not logging them, not writing them to insecure locations). The Aurite Agents framework provides them to the script in a standard way; the script must then maintain their confidentiality.
    *   **Least Privilege:** Ensure that any secrets configured via `ClientConfig.gcp_secrets` (and the IAM permissions for the ADC identity) grant only the necessary permissions required by that specific MCP server.

### 7. Custom Workflow Execution (`CustomWorkflowExecutor`)

The Aurite Agents framework allows for the execution of custom Python-based workflows via the `CustomWorkflowExecutor` (`src/workflows/custom_workflow.py`). This feature provides significant flexibility but carries inherent security implications due to the execution of arbitrary Python code.

*   **Nature of Risk:** Custom workflows execute Python code defined in modules specified by `CustomWorkflowConfig`. The primary risk is that this code could be insecure, whether unintentionally or maliciously.
*   **Path Restriction (Mitigation):**
    *   A critical security control is that the `module_path` for custom workflow code **must reside within the defined `PROJECT_ROOT_DIR`**. This restriction is enforced by both `CustomWorkflowExecutor` during execution and `HostManager` during dynamic registration of new custom workflows. This prevents loading code from arbitrary, potentially unsafe system locations.
*   **Dynamic Registration Control (Mitigation):**
    *   The `AURITE_ALLOW_DYNAMIC_REGISTRATION` environment variable (see Section 9 of this document) globally controls whether new custom workflows (and other components) can be registered at runtime. Setting this to `"false"` (recommended for production) prevents the addition of new custom workflow configurations beyond those defined in the initial project setup.
*   **Trust Model:** The framework inherently trusts the Python code within the modules specified for custom workflows. Developers using this feature are responsible for the security, correctness, and resource management of their custom workflow code.
*   **Capabilities Granted:** Custom workflows are passed an instance of the `ExecutionFacade`. This allows them to orchestrate other components within the Aurite Agents framework, such as running agents or other workflows. This power means that a compromised custom workflow could potentially misuse these capabilities.
*   **Input/Output:** Custom workflows can define arbitrary inputs and outputs. Validation and sanitization of these are the responsibility of the custom workflow's implementation and its calling context.

### 8. Data Persistence Security Considerations

If database persistence is enabled (via `AURITE_ENABLE_DB="true"`), the `StorageManager` (`src/storage/db_manager.py`) handles saving and loading certain configurations and agent conversation history.

*   **Agent Conversation History:**
    *   Agent conversation history is stored in the database if `AgentConfig.include_history` is true and a `session_id` is provided.
    *   The content of these conversations (stored in the `AgentHistoryDB.content_json` column) is saved as-is by the `StorageManager` (typically as plaintext JSON).
    *   **Security Implication:** If agents handle or discuss sensitive information, this data will be stored in plaintext within the database. The security of this sensitive data then relies heavily on the security measures applied to the database system itself (e.g., access controls, network security, encryption at rest at the database/filesystem level). The Aurite Agents framework does not currently perform application-level encryption of conversation history before storage.
    *   **Recommendation:** Ensure your database instance is appropriately secured if sensitive information is anticipated in agent conversations.
*   **Configuration Storage:**
    *   Component configurations (Agents, LLMs, Workflows) are also synced to the database. These configurations generally do not contain direct secrets like API keys (which are typically handled via environment variables for the respective clients or via GCP Secret Manager integration). They are stored as-is.
*   **SQL Injection:** The `StorageManager` uses SQLAlchemy ORM for database interactions, which inherently protects against SQL injection vulnerabilities when used correctly.

### 9. Dynamic Registration Control (`AURITE_ALLOW_DYNAMIC_REGISTRATION`)

The `HostManager` (`src/host_manager.py`) provides methods for dynamically registering new components (Clients, Agents, LLMs, Linear Workflows, and Custom Workflows) at runtime, typically via API endpoints.

*   **Purpose:** This environment variable allows administrators to globally enable or disable these dynamic registration capabilities.
*   **Environment Variable:** `AURITE_ALLOW_DYNAMIC_REGISTRATION`
    *   Set to `"true"` (case-insensitive) to enable dynamic registration.
    *   If set to any other value, or if not set, dynamic registration will be **disabled by default**.
*   **Behavior When Disabled:** If an attempt is made to call a dynamic registration method (e.g., `HostManager.register_agent()`) while this feature is disabled, the method will raise a `PermissionError`.
*   **Security Implication:**
    *   Disabling dynamic registration provides an important security hardening measure, especially in production environments or where API endpoints might be exposed. It prevents unauthorized or accidental changes to the running configuration of the Aurite Agents framework.
    *   If dynamic registration is required, ensure that the API endpoints or other mechanisms that trigger these `HostManager` methods are adequately secured with authentication and authorization.
*   **Recommendation:** For most production deployments, it is recommended to set `AURITE_ALLOW_DYNAMIC_REGISTRATION="false"` unless dynamic updates to the configuration are a specific operational requirement and the calling interfaces are secured.

### 10. API Authentication (FastAPI Server)

The FastAPI server (`src/bin/api/api.py`) provides the primary programmatic interface to the Aurite Agents framework. Access to its endpoints is controlled via an API key.

*   **Mechanism:** API key authentication is enforced by a dependency (`get_api_key` in `src/bin/dependencies.py`) applied to protected routes.
*   **Transmission:** The API key **must** be provided in the `X-API-Key` HTTP header of the request. Transmitting the API key via query parameters is **not supported** to enhance security (as URLs, including query parameters, can be logged in various places).
*   **Configuration:** The server-side expected API key is configured via the `API_KEY` environment variable (see `.env.example`).
*   **Security Best Practices:**
    *   The framework uses `secrets.compare_digest` for comparing the provided API key against the expected key, which helps protect against timing attacks.
    *   It is crucial to generate a strong, unique, and random string for your `API_KEY`.
    *   Treat the `API_KEY` as a sensitive secret and manage it accordingly (e.g., using environment variables, secrets management tools, and not committing it to version control).
