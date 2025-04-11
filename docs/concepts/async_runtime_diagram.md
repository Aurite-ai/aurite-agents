# Async Runtime Diagram (Pytest Context)

This diagram illustrates the relationship between the different asynchronous components and processes when running tests using the `host_manager` fixture.

```text
+-----------------------------------------------------------------------------+
| Layer 1: Pytest Process                                                     |
| +-------------------------------------------------------------------------+ |
| | Layer 2: Pytest Event Loop (Managed by pytest-asyncio)                  | |
| | +---------------------------------------------------------------------+ | |
| | | Layer 3: Test Function & Fixture Execution Context                  | | |
| | | +-----------------------------------------------------------------+ | | |
| | | | `host_manager` Fixture Task (Setup Phase)                       | | | |
| | | |   - Creates `HostManager` instance                            | | | |
| | | |   - Calls `manager.initialize()`                              | | | |
| | | |     - Creates `MCPHost` instance                            | | | |
| | | |       - Creates `AsyncExitStack` instance (`_exit_stack`)     | | | |
| | | |     - Loops through client configs:                           | | | |
| | | |       - Calls `await _exit_stack.enter_async_context(...)`    | | | |
| | | |         - `stdio_client(...)` is called                       | | | |
| | | |           |                                                   | | | |
| | | |           +---> OS Operation: Starts MCP Server Process <-------+ | | |
| | | |           |                                                   | | | |
| | | |         - `stdio_client.__aenter__` runs ON HOST LOOP:        | | | |
| | | |           - Layer 4: `anyio` machinery (within stdio_client)  | | | |
| | | |             +-----------------------------------------------+ | | | |
| | | |             | `anyio.CancelScope` created (associated with  | | | | |
| | | |             | this setup task context)                      | | | | |
| | | |             +-----------------------------------------------+ | | | |
| | | |             | Background I/O Tasks started ON HOST LOOP     | | | | |
| | | |             | (e.g., read from server stdout pipe)          | | | | |
| | | |             | managed by the Cancel Scope                   | | | | |
| | | |             +-----------------------------------------------+ | | | |
| | | |                                                               | | | |
| | | | Test Function (`test_...`) Runs Here                          | | | |
| | | |   - Uses `host_manager` -> `host` -> `host.execute_tool(...)` | | | |
| | | |     (Communicates via pipes using host-side I/O tasks)        | | | |
| | | |                                                               | | | |
| | | | `host_manager` Fixture Task (Teardown Phase)                  | | | |
| | | |   - Calls `await manager.shutdown()`                          | | | |
| | | |     - Calls `await host.shutdown()`                         | | | |
| | | |       - Calls `await _exit_stack.aclose()`                  | | | |
| | | |         - Iterates entered contexts (LIFO):                 | | | |
| | | |           - Calls `await stdio_client.__aexit__(...)`       | | | |
| | | |             ON HOST LOOP                                    | | | |
| | | |             - Attempts to exit the internal                 | | | |
| | | |               `anyio.CancelScope`                           | | | |
| | | |             - *** ERROR HERE: `anyio` detects this exit *** | | | |
| | | |             - *** is in a different task context than   *** | | | |
| | | |             - *** the one during `__aenter__`.          *** | | | |
| | | +-----------------------------------------------------------------+ | | |
| | +---------------------------------------------------------------------+ | |
| +-------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------+
      |
      | (stdio pipe communication)
      v
+-----------------------------------------------------------------------------+
| Separate Process: MCP Server (e.g., weather_mcp_server.py)                  |
| +-------------------------------------------------------------------------+ |
| | Own Event Loop (Managed by `anyio.run`)                                 | |
| | +---------------------------------------------------------------------+ | |
| | | Server-specific tasks (e.g., handling tool requests) run here       | | |
| | +---------------------------------------------------------------------+ | |
| +-------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------+

Key Points:
- The Host (pytest process) and Server are separate processes.
- All host-side async operations run on the single pytest event loop.
- `AsyncExitStack` manages host-side context managers.
- `stdio_client` uses `anyio` internally *on the host loop* to manage communication and cancellation via a `CancelScope`.
- The error occurs during the host-side cleanup (`aclose` -> `__aexit__`) due to `anyio`'s strict task context rules for `CancelScope` exit.
