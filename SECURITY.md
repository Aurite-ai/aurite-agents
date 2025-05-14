# Security Policy for Aurite Agents

The Aurite Agents team and community take the security of the framework seriously. We appreciate your efforts to responsibly disclose your findings, and will make every effort to acknowledge your contributions.

## Reporting a Vulnerability

Please **DO NOT** report security vulnerabilities through public GitHub issues.

Instead, please report them by sending an email to `[REPLACE_WITH_SECURITY_EMAIL_ALIAS]`.

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

### 6. Environment Variable Handling for MCP Servers

*(Placeholder for details on how secrets and other environment variables are securely passed to MCP server subprocesses. To be detailed after `MCPHost` and `ClientManager` review.)*

## Supported Versions

*(Placeholder: Detail which versions of Aurite Agents are currently supported with security updates.)*

---

*This document is a work in progress and will be updated as the security review progresses.*
