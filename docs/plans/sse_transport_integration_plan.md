# Implementation Plan: SSE Transport Integration

**Version:** 1.0
**Date:** 2025-05-15
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A (Covered by discussion)

## 1. Goals
    *   Integrate Server-Sent Events (SSE) as a new transport mechanism for MCP clients within the Aurite Agents framework.
    *   Allow `MCPHost` to connect to MCP servers via SSE URLs in addition to local stdio processes.
    *   Ensure existing stdio transport functionality remains unaffected.
    *   Provide a way to configure SSE clients, including their URL.

## 2. Scope
    *   **In Scope:**
        *   Modifying `src/config/config_models.py` (`ClientConfig`).
        *   Modifying `src/host/foundation/clients.py` (`ClientManager.manage_client_lifecycle`).
        *   Updating test configurations to include an SSE client.
        *   Adding new integration tests for SSE client connections.
        *   Ensuring the `mcp.client.sse_client` is correctly used.
    *   **Out of Scope (Optional but Recommended):**
        *   Implementing a new SSE MCP *server* within this framework (we will use the provided `sse_example_server.py` for testing).
        *   Advanced SSE features beyond basic connection and MCP message exchange (e.g., custom headers, complex auth for SSE beyond what `mcp.client.sse_client` might offer out-of-the-box).
        *   UI changes to configure SSE clients (this plan focuses on backend).

## 3. Prerequisites (Optional)
    *   The `mcp-py` library must have a functional `sse_client` implementation as suggested by the MCP documentation.
    *   The example SSE server (`src/packaged_servers/sse_example_server.py`) should be runnable for testing.

## 4. Implementation Steps

**Phase 1: Configuration Model Update**

1.  **Step 1.1: Modify `ClientConfig` Model**
    *   **File(s):** `src/config/config_models.py`
    *   **Action:**
        *   Import `Literal` from `typing` and `root_validator` from `pydantic`.
        *   Add `transport_type: Literal["stdio", "sse"] = "stdio"` to `ClientConfig`.
        *   Change `server_path: Path` to `server_path: Optional[Path] = None`.
        *   Add `sse_url: Optional[str] = None` to `ClientConfig`.
        *   Implement a `root_validator` method in `ClientConfig`:
            ```python
            @root_validator(pre=False, skip_on_failure=True)
            def check_transport_specific_fields(cls, values):
                transport_type = values.get("transport_type")
                server_path = values.get("server_path")
                sse_url = values.get("sse_url")

                if transport_type == "stdio":
                    if server_path is None:
                        raise ValueError("server_path is required for stdio transport type")
                elif transport_type == "sse":
                    if sse_url is None:
                        raise ValueError("sse_url is required for sse transport type")
                    # Basic URL validation (more sophisticated validation can be added if needed)
                    if not (sse_url.startswith("http://") or sse_url.startswith("https://")):
                        raise ValueError("sse_url must be a valid HTTP/HTTPS URL")
                return values
            ```
    *   **Verification:**
        *   Manually inspect the changes.
        *   Unit tests for `ClientConfig` (new or existing) should verify that the validator works correctly (e.g., raises ValueError for invalid combinations).

**Phase 2: ClientManager Update**

1.  **Step 2.1: Update `manage_client_lifecycle` for SSE**
    *   **File(s):** `src/host/foundation/clients.py`
    *   **Action:**
        *   Import `sse_client` from `mcp.client` (e.g., `from mcp.client import stdio_client, sse_client`).
        *   Modify the `manage_client_lifecycle` method to include conditional logic based on `client_config.transport_type` as detailed in the "Refined Plan" section above.
            *   The `if client_config.transport_type == "stdio":` block will contain the existing logic for `StdioServerParameters` and `stdio_client`.
            *   The `elif client_config.transport_type == "sse":` block will use `sse_client(client_config.sse_url)`. Environment variable injection for GCP secrets will likely be skipped for the SSE case, as it's typically for local processes.
            *   The inner `async with ClientSession(reader, writer) as session:` block and subsequent session handling logic should be common to both paths.
    *   **Verification:**
        *   Code review.
        *   Integration tests in Phase 3 will verify this functionality.

**Phase 3: Testing**

1.  **Step 3.1: Update Test Configuration**
    *   **File(s):** `config/projects/testing_config.json` (or a relevant test configuration file used by `host_manager` fixture).
    *   **Action:**
        *   Add a new client configuration entry for the SSE example server:
            ```json
            {
                "client_id": "sse_example_client",
                "transport_type": "sse",
                "sse_url": "http://localhost:8082/sse",
                "roots": [], // Add appropriate roots if needed for tests
                "capabilities": ["tools", "resources"], // Match example server's capabilities
                "timeout": 10.0,
                "routing_weight": 1.0,
                "exclude": null
            }
            ```
    *   **Verification:**
        *   The host should load this configuration without errors during test setup.

2.  **Step 3.2: Add SSE Integration Tests**
    *   **File(s):** `tests/host/test_host_sse_e2e.py` (new file) or extend `tests/host/test_host_basic_e2e.py`.
    *   **Action:**
        *   Create tests that use the `host_manager` fixture (which initializes `MCPHost`).
        *   Ensure the `sse_example_server.py` is running during these tests (this might require a pytest fixture to start/stop the server or running it manually).
        *   Test 1: Verify that the `MCPHost` successfully initializes the "sse_example_client". Check `host.is_client_registered("sse_example_client")`.
        *   Test 2 (If example server is enhanced): If the SSE server properly implements MCP tool/resource listing, test that `MCPHost` can discover these components from the SSE client.
    *   **Verification:**
        *   Pytest runs successfully, and the new tests pass.

3.  **Step 3.3: Run Existing Stdio Tests**
    *   **File(s):** Existing test files in `tests/host/`.
    *   **Action:**
        *   Run all existing host-layer tests.
    *   **Verification:**
        *   All existing tests should continue to pass, ensuring no regressions in stdio functionality.

## 5. Testing Strategy
    *   **Unit Tests:**
        *   Focus on the Pydantic validator in `ClientConfig`.
    *   **Integration Tests:**
        *   Primary focus for verifying SSE connectivity.
        *   Use the `host_manager` fixture with the updated test configuration.
        *   Requires the `sse_example_server.py` to be running.
    *   **Key Scenarios to Cover:**
        *   Successful initialization of an SSE client.
        *   Correct parsing of `ClientConfig` for SSE type.
        *   No regressions for stdio clients.

## 6. Potential Risks & Mitigation (Optional)
    *   **`mcp.client.sse_client` availability/API:** The plan assumes `sse_client` exists and has a similar interface to `stdio_client` (yielding reader/writer streams). If its API is different, `manage_client_lifecycle` will need more significant adaptation. Mitigation: Check `mcp-py` library documentation/source for `sse_client` early.
    *   **SSE Server for Testing:** The `sse_example_server.py` is basic. For more thorough testing of component discovery over SSE, it might need to be enhanced to be a more complete MCP server. Mitigation: For this initial implementation, basic connection/initialization is the primary goal. Further enhancements can be a separate task.

## 7. Open Questions & Discussion Points (Optional)
    *   Confirm the exact import path and usage for `sse_client` from the `mcp-py` library. The documentation provided shows `async with sse_client("http://localhost:8000/sse") as streams:`, which implies it's a context manager yielding streams.
    *   How should the lifecycle of the `sse_example_server.py` be managed during automated tests? (e.g., pytest fixture using `subprocess`).
