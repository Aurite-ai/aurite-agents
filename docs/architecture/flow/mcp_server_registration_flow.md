# MCP Server Registration Flow

This document explains the five-phase process used by the MCP Host to register MCP (Model Context Protocol) servers and discover their capabilities.

## Overview

The MCP Host uses a comprehensive five-phase registration process to establish connections with external MCP servers and discover their tools, prompts, and resources. This process ensures reliable server registration, proper component discovery, and robust error handling.

## Registration Process

The registration process follows a sequential five-phase approach, where each phase must complete successfully before proceeding to the next phase.

## Five-Phase Registration Process

=== "Phase 1: Configuration Resolution"

    **Objective**: Retrieve and validate server configuration with credential resolution.

    ```mermaid
    flowchart TD
        A[ClientConfig] --> B[SecurityManager.resolve_credentials]
        B --> C[Environment Variable Substitution]
        C --> D[Transport Validation]
        D --> E[Resolved Configuration]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style E fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style B fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style C fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style D fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    ```

    **Key Activities**:
    - SecurityManager resolves encrypted credentials and environment variables
    - Environment variable substitution with placeholder resolution
    - Transport-specific validation (stdio, local, http_stream)
    - Configuration integrity verification

    **Implementation Details**:
    ```python
    # SecurityManager resolves encrypted credentials
    resolved_config = security_manager.resolve_credentials(server_config)

    # Environment variable substitution
    if "{API_TOKEN}" in resolved_config.headers.get("Authorization", ""):
        resolved_config.headers["Authorization"] = resolved_config.headers["Authorization"].replace(
            "{API_TOKEN}", os.environ.get("API_TOKEN", "")
        )
    ```

    **Validation Examples**:
    ```python
    # Validate required fields based on transport type
    if server_config.transport_type == "stdio":
        if not server_config.server_path:
            raise ValueError("'server_path' is required for stdio transport")
    elif server_config.transport_type == "http_stream":
        if not server_config.http_endpoint:
            raise ValueError("'http_endpoint' is required for http_stream transport")
    ```

=== "Phase 2: Transport Establishment"

    **Objective**: Establish the appropriate transport connection based on server configuration.

    ```mermaid
    flowchart TD
        A[Resolved ClientConfig] --> B{Transport Type}
        B -->|stdio| C[StdioServerParameters]
        B -->|local| D[Local Command Setup]
        B -->|http_stream| E[StreamableHttpParameters]

        C --> F[AsyncExitStack Context]
        D --> F
        E --> F

        F --> G[read, write streams]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style G fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style B fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
        style F fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
    ```

    **Key Activities**:
    - Transport-specific parameter setup based on configuration
    - AsyncExitStack context creation for guaranteed cleanup
    - Stream establishment (stdin/stdout, HTTP, or command execution)
    - Connection validation and error handling

    **Transport Implementations**:

    **STDIO Transport**:
    ```python
    # Local Python subprocess
    params = StdioServerParameters(
        command="python",
        args=[str(server_config.server_path)],
        env=client_env
    )
    client = stdio_client(params, errlog=open(os.devnull, "w"))
    read, write = await session_stack.enter_async_context(client)
    ```

    **Local Command Transport**:
    ```python
    # Execute local command with arguments
    resolved_args = [
        _resolve_placeholders(arg) for arg in (config.args or [])
    ]
    params = StdioServerParameters(
        command=config.command,
        args=resolved_args,
        env=client_env
    )
    client = stdio_client(params, errlog=open(os.devnull, "w"))
    read, write = await session_stack.enter_async_context(client)
    ```

    **HTTP Stream Transport**:
    ```python
    # Remote HTTP streaming connection
    endpoint_url = _resolve_placeholders(config.http_endpoint)
    params = StreamableHttpParameters(
        url=endpoint_url,
        headers=config.headers,
        timeout=timedelta(seconds=config.timeout or 30.0)
    )
    client = streamablehttp_client(
        url=params.url,
        headers=params.headers,
        timeout=params.timeout,
        sse_read_timeout=params.sse_read_timeout,
        terminate_on_close=True
    )
    read, write, _ = await session_stack.enter_async_context(client)
    ```

=== "Phase 3: MCP Session Initialization"

    **Objective**: Create MCP client session and perform protocol handshake.

    ```mermaid
    flowchart TD
        A[Transport Streams] --> B[mcp.ClientSession]
        B --> C[session.initialize]
        C --> D{Handshake Success?}
        D -->|Yes| E[Session Ready]
        D -->|No| F[Cleanup & Error]
        E --> G[Store Session]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style G fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style D fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
        style F fill:#F44336,stroke:#D32F2F,stroke-width:2px,color:#fff
    ```

    **Key Activities**:
    - MCP ClientSession creation with transport streams
    - Protocol handshake and capability negotiation
    - Session validation and error recovery
    - Session storage with exit stack for lifecycle management

    **Session Creation**:
    ```python
    # Create MCP client session
    session = await session_stack.enter_async_context(
        mcp.ClientSession(read, write)
    )

    # Store session for lifecycle management
    self._sessions[server_name] = session
    self._session_exit_stacks[server_name] = session_stack
    ```

    **Protocol Handshake**:
    ```python
    # Perform MCP protocol initialization
    await session.initialize()

    # Session now ready for component discovery
    logger.info(f"MCP session initialized for '{server_name}'")
    ```

=== "Phase 4: Component Discovery"

    **Objective**: Query MCP server for available tools, prompts, and resources.

    ```mermaid
    flowchart TD
        A[Initialized Session] --> B[session.list_tools]
        A --> C[session.list_prompts]
        A --> D[session.list_resources]

        B --> E[Process & Prefix Tools]
        C --> F[Process & Prefix Prompts]
        D --> G[Validate & Store Resources]

        E --> H[Update Registries]
        F --> H
        G --> H

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style H fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style B fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style C fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style D fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    ```

    **Key Activities**:
    - Parallel discovery of tools, prompts, and resources via MCP protocol
    - Server prefix application to prevent naming conflicts
    - Resource access validation through RootManager
    - Metadata enhancement (timeouts, schemas, access controls)

    **Tool Discovery**:
    ```python
    # Discover available tools
    try:
        tools_response = await session.list_tools()
        for tool in tools_response.tools:
            # Preserve original name in title
            tool.title = tool.name

            # Add server prefix for uniqueness
            tool.name = f"{server_name}-{tool.name}"

            # Add timeout metadata
            if not tool.meta:
                tool.meta = {}
            tool.meta["timeout"] = server_config.timeout

            # Register with ToolManager
            self._tools[tool.name] = tool
            self._tool_to_session[tool.name] = session

        logger.info(f"Discovered {len(tools_response.tools)} tools from '{server_name}'")

    except Exception as e:
        logger.warning(f"Could not fetch tools from '{server_name}': {e}")
    ```

    **Prompt Discovery**:
    ```python
    # Discover available prompts
    try:
        prompts_response = await session.list_prompts()
        for prompt in prompts_response.prompts:
            # Add server prefix for uniqueness
            prompt_name = f"{server_name}-{prompt.name}"

            # Store prompt definition
            self._prompts[prompt_name] = prompt

            # Map to session for execution
            self._prompt_to_session[prompt_name] = session

        logger.info(f"Discovered {len(prompts_response.prompts)} prompts from '{server_name}'")

    except Exception as e:
        logger.warning(f"Could not fetch prompts from '{server_name}': {e}")
    ```

    **Resource Discovery**:
    ```python
    # Discover available resources
    try:
        resources_response = await session.list_resources()
        for resource in resources_response.resources:
            # Add server prefix for uniqueness
            resource_name = f"{server_name}-{resource.name}"

            # Validate resource URI with RootManager
            if self._root_manager.validate_access(resource.uri):
                # Store resource definition
                self._resources[resource_name] = resource

                # Map to session for access
                self._resource_to_session[resource_name] = session
            else:
                logger.warning(f"Resource '{resource.name}' denied by root manager")

        logger.info(f"Discovered {len(resources_response.resources)} resources from '{server_name}'")

    except Exception as e:
        logger.warning(f"Could not fetch resources from '{server_name}': {e}")
    ```

    <!-- prettier-ignore -->
    !!! note "Component Naming Strategy"
        Components are prefixed with server names to prevent conflicts:

        - **Tool Names**: `weather_server-get_weather` (server_name-tool_name)
        - **Prompt Names**: `planning_server-task_breakdown` (server_name-prompt_name)
        - **Resource Names**: `file_server-document.txt` (server_name-resource_name)
        - **Original Names**: Preserved in `title` field for display purposes

=== "Phase 5: Component Registration"

    **Objective**: Register discovered components with internal registries and update routing tables.

    ```mermaid
    flowchart TD
        A[Discovered Components] --> B[Update Tool Registry]
        A --> C[Update Prompt Registry]
        A --> D[Update Resource Registry]

        B --> E[Update MessageRouter]
        C --> E
        D --> E

        E --> F[Registration Complete]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style F fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style E fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    ```

    **Key Activities**:
    - Component storage in type-specific registries
    - Session routing table updates for efficient tool execution
    - MessageRouter mapping creation for O(1) component lookup
    - FilteringManager integration for access control enforcement

    **Registry Updates**:
    ```python
    # Registration creates multiple data structures
    registration_data = {
        # Component storage (by type)
        "tools": {
            "weather_server-get_weather": Tool(name="weather_server-get_weather", ...),
            "location_server-geocode": Tool(name="location_server-geocode", ...)
        },

        # Session routing (for execution)
        "tool_to_session": {
            "weather_server-get_weather": <ClientSession for weather_server>,
            "location_server-geocode": <ClientSession for location_server>
        }
    }
    ```

    **MessageRouter Updates**:
    ```python
    # MessageRouter maintains component-to-session mappings
    self._message_router.register_component_mappings({
        "weather_server-get_weather": session_weather,
        "weather_server-get_forecast": session_weather,
        "location_server-geocode": session_location,
        "location_server-reverse_geocode": session_location
    })

    # Enables fast lookup during tool execution
    target_session = self._message_router.get_session_for_component("weather_server-get_weather")
    ```

## References

- **Implementation**: `src/aurite/execution/mcp_host.py` - Main MCP Host implementation
- **Design Details**: [MCP Host Design](../design/mcp_host_design.md) - Architecture and component details
