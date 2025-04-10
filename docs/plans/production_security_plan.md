# Production Security Implementation Plan: GCP Secrets Manager

**Date:** 2025-04-10
**Status:** Proposed
**Related Plan:** `docs/plans/production_readiness_plan.md`

## 1. Goal

Integrate Google Cloud Platform (GCP) Secrets Manager into the Aurite Agents framework to securely manage environment variables/secrets required by MCP servers, using Application Default Credentials (ADC) for authentication.

## 2. Background

Currently, MCP servers like `mem0_server.py` rely on standard environment variables (e.g., `os.getenv("MEM0_PASSWORD")`). For production, sensitive values like database passwords or API keys should not be stored directly in environment variables or configuration files. GCP Secrets Manager provides a secure way to store and access these secrets.

This plan details modifications to the `ClientConfig`, `SecurityManager`, `MCPHost`, and configuration loading process to fetch secrets from GCP Secrets Manager and make them available to the specific MCP server process environment just before it starts.

## 3. Implementation Steps

1.  **Dependency:**
    *   Add `google-cloud-secret-manager` to the `dependencies` list in `pyproject.toml`.
    *   Run `pip install -e .` or equivalent to update the environment.

2.  **Model Update (`src/host/models.py`):**
    *   Define a new `GCPSecretConfig` model:
      ```python
      from pydantic import BaseModel, Field # Add Field if not already imported

      class GCPSecretConfig(BaseModel):
          secret_id: str = Field(..., description="Full GCP Secret Manager secret ID (e.g., projects/my-proj/secrets/my-secret/versions/latest)")
          env_var_name: str = Field(..., description="Environment variable name to map the secret value to")
      ```
    *   Modify the `ClientConfig` model to add an optional list of these secrets:
      ```python
      class ClientConfig(BaseModel):
          # ... existing fields ...
          gcp_secrets: Optional[List[GCPSecretConfig]] = Field(None, description="List of GCP secrets to resolve and inject into the server environment")
          # ... rest of the model ...
      ```

3.  **Config Loading Update (`src/config.py`):**
    *   In `load_host_config_from_json`:
        *   When iterating through `config_data.get("clients", [])`:
            *   Extract the `gcp_secrets` list from `client_data`.
            *   If present, parse each item into a `GCPSecretConfig` object.
            *   Pass the parsed list to the `ClientConfig` constructor.
            *   Handle potential `KeyError` or `ValidationError` during parsing.

4.  **SecurityManager Enhancement (`src/host/foundation/security.py`):**
    *   Add imports:
      ```python
      from google.cloud import secretmanager
      from google.api_core import exceptions as gcp_exceptions # Alias for clarity
      # Ensure List, Dict, Optional are imported from typing
      ```
    *   In `__init__`:
        *   Initialize the GCP client within a try-except block:
          ```python
          try:
              self._gcp_secret_client = secretmanager.SecretManagerServiceClient()
              logger.info("GCP Secret Manager client initialized successfully via ADC.")
          except Exception as e:
              logger.warning(f"Failed to initialize GCP Secret Manager client (ADC might be missing/misconfigured, or package not installed): {e}")
              self._gcp_secret_client = None # Allow SecurityManager to function without GCP if client fails
          ```
    *   Add the new method:
      ```python
      async def resolve_gcp_secrets(self, secrets_config: List[GCPSecretConfig]) -> Dict[str, str]:
          """Fetches secrets from GCP Secrets Manager based on config."""
          if not self._gcp_secret_client:
              logger.error("GCP Secret Manager client not available. Cannot resolve secrets.")
              # Consider if raising an error is more appropriate depending on requirements
              return {}

          resolved_secrets: Dict[str, str] = {}
          logger.info(f"Attempting to resolve {len(secrets_config)} GCP secrets.")
          for secret_conf in secrets_config:
              secret_name = secret_conf.secret_id
              env_var = secret_conf.env_var_name
              logger.debug(f"Attempting to access secret: {secret_name} for env var: {env_var}")
              try:
                  request = secretmanager.AccessSecretVersionRequest(name=secret_name)
                  # Use the synchronous client method directly as SDK doesn't provide async access method
                  # This will block the event loop briefly for each secret access.
                  # If many secrets are needed frequently, consider running in a thread pool executor.
                  response = self._gcp_secret_client.access_secret_version(request=request)
                  secret_value = response.payload.data.decode("UTF-8")
                  resolved_secrets[env_var] = secret_value
                  logger.debug(f"Successfully resolved GCP secret for env var: {env_var}")
              except gcp_exceptions.NotFound:
                  logger.error(f"GCP Secret not found: {secret_name}")
                  # Skip this secret and continue
              except gcp_exceptions.PermissionDenied:
                  logger.error(f"Permission denied accessing GCP secret: {secret_name}. Check IAM roles for ADC.")
                  # Skip this secret and continue
              except Exception as e:
                  logger.error(f"Failed to access GCP secret {secret_name}: {e}")
                  # Skip this secret and continue

          logger.info(f"Resolved {len(resolved_secrets)} out of {len(secrets_config)} requested GCP secrets.")
          return resolved_secrets
      ```

5.  **MCPHost Modification (`src/host/host.py`):**
    *   In `_initialize_client`, locate the section before `stdio_client` is called.
    *   Add the following logic:
      ```python
      # Resolve GCP secrets if configured
      client_env = os.environ.copy() # Start with current environment
      if config.gcp_secrets and self._security_manager: # Check if SecurityManager exists and secrets are configured
          logger.info(f"Resolving GCP secrets for client: {config.client_id}")
          try:
              # Await the resolution method
              resolved_env_vars = await self._security_manager.resolve_gcp_secrets(config.gcp_secrets)
              if resolved_env_vars:
                  # Update the environment dictionary for the subprocess
                  client_env.update(resolved_env_vars)
                  logger.info(f"Injecting {len(resolved_env_vars)} secrets into environment for client: {config.client_id}")
                  # Optional: Log the keys being injected for debugging (DO NOT log values)
                  logger.debug(f"Injecting env vars: {list(resolved_env_vars.keys())}")
          except Exception as e:
              # Log error but allow host to continue initialization without injected secrets
              logger.error(f"Failed to resolve or inject GCP secrets for client {config.client_id}: {e}. Proceeding without injected secrets.")

      # Setup transport with potentially updated environment
      server_params = StdioServerParameters(
          command="python", args=[str(config.server_path)], env=client_env # Pass the modified env
      )
      # ... rest of the _initialize_client method ...
      ```

6.  **Documentation:**
    *   Update `README.md`: Add `google-cloud-secret-manager` to dependencies. Briefly mention GCP secret support in configuration section.
    *   Update `docs/framework_guide.md` (or create `docs/security.md`):
        *   Explain the GCP Secrets Manager integration.
        *   Detail the required GCP setup: Enabling the API, creating secrets, granting the service account running the host (via ADC) the "Secret Manager Secret Accessor" IAM role.
        *   Show an example of the `gcp_secrets` section in the host JSON configuration.

7.  **Testing Strategy:**
    *   **Unit Tests:**
        *   Test `load_host_config_from_json` correctly parses `gcp_secrets` into `ClientConfig`.
        *   In `tests/host/foundation/test_security.py` (create if needed):
            *   Mock `secretmanager.SecretManagerServiceClient` and its `access_secret_version` method.
            *   Test `SecurityManager.resolve_gcp_secrets` returns the correct dict on success.
            *   Test it handles `NotFound`, `PermissionDenied`, and other exceptions gracefully (returns empty dict or partial dict as decided).
            *   Test it handles the case where `_gcp_secret_client` is `None`.
    *   **Integration Tests:**
        *   Create a simple test MCP server script (`tests/fixtures/servers/env_check_server.py`) that imports `os` and prints `os.getenv("TEST_SECRET_1")` and `os.getenv("TEST_SECRET_2")` on startup, then exits.
        *   In `config/agents/testing_config.json` (or a dedicated test config file):
            *   Add a `ClientConfig` pointing to `env_check_server.py`.
            *   Include a `gcp_secrets` section mapping hypothetical GCP secret IDs to `TEST_SECRET_1` and `TEST_SECRET_2`.
        *   In an integration test file (e.g., `tests/host/test_host_secrets.py`):
            *   Use a fixture like `real_mcp_host` that loads the test config.
            *   **Crucially, mock `SecurityManager.resolve_gcp_secrets`** before the host initializes. The mock should return `{"TEST_SECRET_1": "value1", "TEST_SECRET_2": "value2"}` without actually calling GCP.
            *   Allow the host to initialize (which starts the `env_check_server.py`).
            *   Capture the stdout/stderr of the `env_check_server.py` process (this might require modifying the `stdio_client` or test fixture setup to allow capturing subprocess output).
            *   Assert that the captured output contains "value1" and "value2".

## 4. Considerations

*   **ADC Setup:** The host environment needs Application Default Credentials configured correctly (e.g., running on GCP infrastructure, `gcloud auth application-default login`, or `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to a service account key file). This needs clear documentation.
*   **Error Handling:** Decide if failure to resolve a secret should prevent the client from starting or just log an error. Current plan logs and continues.
*   **Performance:** Accessing secrets blocks the async loop. If many secrets are needed for many clients at startup, performance might be impacted. Consider `asyncio.to_thread` or similar if this becomes an issue.
*   **Secret Naming:** Use the full GCP secret resource name (e.g., `projects/PROJECT_ID/secrets/SECRET_ID/versions/VERSION`).

## 5. Next Steps

*   Review and approve this plan.
*   Proceed with implementation step-by-step.
