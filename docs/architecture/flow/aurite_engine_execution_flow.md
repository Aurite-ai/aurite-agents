# AuriteEngine Execution Flow

This document explains the execution flows used by the AuriteEngine to orchestrate agents, workflows, and streaming operations across the Aurite framework.

## Overview

The AuriteEngine implements distinct execution flows for different component types while maintaining consistent patterns for session management, resource provisioning, and error handling. Each flow coordinates between the ConfigManager, MCPHost, and SessionManager to provide unified execution orchestration.

## Core Execution Flows

The AuriteEngine supports four primary execution patterns, each optimized for specific use cases while sharing common orchestration principles.

=== "Agent Execution Flow"

    **Objective**: Execute individual agents with JIT server registration, session management, and comprehensive error handling.

    ```mermaid
    flowchart TD
        A[Agent Execution Request] --> B[Configuration Resolution]
        B --> C[Session ID Management]
        C --> D[Agent Preparation]
        D --> E[JIT Server Registration]
        E --> F[History Loading]
        F --> G[Agent Execution]
        G --> H[Result Processing]
        H --> I[Session Persistence]
        I --> J[Cleanup & Return]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style J fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style D fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style E fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style G fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    ```

    **Phase 1: Configuration Resolution**
    ```python
    # Retrieve agent configuration from ConfigManager
    agent_config_dict = self._config_manager.get_config("agent", agent_name)
    if not agent_config_dict:
        raise ConfigurationError(f"Agent configuration '{agent_name}' not found.")

    agent_config_for_run = AgentConfig(**agent_config_dict)
    ```

    **Phase 2: Session ID Management**
    ```python
    # Auto-generate session ID if agent has history enabled
    effective_include_history = (
        force_include_history if force_include_history is not None
        else agent_config.include_history
    )

    if effective_include_history:
        if not final_session_id:
            final_session_id = f"agent-{uuid.uuid4().hex[:8]}"
            logger.info(f"Auto-generated session_id for agent '{agent_name}': {final_session_id}")
    ```

    **Phase 3: JIT Server Registration**
    ```python
    # Register required MCP servers dynamically
    if agent_config_for_run.mcp_servers:
        for server_name in agent_config_for_run.mcp_servers:
            if server_name not in self._host.registered_server_names:
                server_config_dict = self._config_manager.get_config("mcp_server", server_name)
                server_config = ClientConfig(**server_config_dict)
                await self._host.register_client(server_config)
                dynamically_registered_servers.append(server_name)
    ```

    **Phase 4: History Loading & Agent Creation**
    ```python
    # Load conversation history if enabled
    initial_messages = []
    if effective_include_history and session_id and self._session_manager:
        history = self._session_manager.get_session_history(session_id)
        if history:
            initial_messages.extend(history)

    # Add current user message and create agent
    current_user_message = {"role": "user", "content": user_message}
    initial_messages.append(current_user_message)

    agent_instance = Agent(
        agent_config=agent_config_for_run,
        base_llm_config=base_llm_config,
        host_instance=self._host,
        initial_messages=initial_messages,
        session_id=session_id,
    )
    ```

    **Phase 5: Execution & Result Processing**
    ```python
    # Execute agent conversation
    run_result = await agent_instance.run_conversation()
    run_result.agent_name = agent_name

    # Save complete execution result
    if agent_instance.config.include_history and final_session_id and self._session_manager:
        self._session_manager.save_agent_result(
            session_id=final_session_id,
            agent_result=run_result,
            base_session_id=final_base_session_id
        )
    ```

=== "Linear Workflow Execution Flow"

    **Objective**: Execute sequential workflow steps with coordinated session management and step-level error handling.

    ```mermaid
    flowchart TD
        A[Workflow Execution Request] --> B[Workflow Configuration]
        B --> C[Session Management]
        C --> D[Workflow Executor Creation]
        D --> E[Step-by-Step Execution]
        E --> F[Result Aggregation]
        F --> G[Session Persistence]
        G --> H[Cleanup & Return]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style H fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style E fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
        style F fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    ```

    **Phase 1: Configuration & Session Setup**
    ```python
    # Resolve workflow configuration
    workflow_config_dict = self._config_manager.get_config("linear_workflow", workflow_name)
    workflow_config = WorkflowConfig(**workflow_config_dict)

    # Manage workflow session ID with prefix
    final_session_id = session_id
    base_session_id = session_id
    if workflow_config.include_history:
        if final_session_id:
            if not final_session_id.startswith("workflow-"):
                final_session_id = f"workflow-{final_session_id}"
        else:
            final_session_id = f"workflow-{uuid.uuid4().hex[:8]}"
            base_session_id = final_session_id
    ```

    **Phase 2: Workflow Execution Delegation**
    ```python
    # Create workflow executor with engine reference
    workflow_executor = LinearWorkflowExecutor(
        config=workflow_config,
        engine=self,  # Engine passed for step execution
    )

    # Execute workflow with session coordination
    result = await workflow_executor.execute(
        initial_input=initial_input,
        session_id=final_session_id,
        base_session_id=base_session_id
    )
    ```

    **Phase 3: Result Persistence**
    ```python
    # Save complete workflow execution result
    if result.session_id and self._session_manager:
        self._session_manager.save_workflow_result(
            session_id=result.session_id,
            workflow_result=result,
            base_session_id=base_session_id
        )
    ```

    **Step Execution Pattern**:
    Each workflow step is executed through the AuriteEngine, enabling:
    - **Recursive Orchestration**: Steps can be agents, workflows, or custom components
    - **Session Coordination**: Base session ID maintained across all steps
    - **Error Isolation**: Step failures don't prevent result persistence
    - **Resource Sharing**: JIT-registered servers available to all steps

=== "Custom Workflow Execution Flow"

    **Objective**: Execute Python-based custom workflows with dynamic component resolution and flexible execution patterns.

    ```mermaid
    flowchart TD
        A[Custom Workflow Request] --> B[Configuration Resolution]
        B --> C[Module Loading]
        C --> D[Executor Creation]
        D --> E[Dynamic Execution]
        E --> F[Result Processing]
        F --> G[Cleanup & Return]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style G fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style E fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
        style C fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    ```

    **Phase 1: Configuration & Module Resolution**
    ```python
    # Resolve custom workflow configuration
    workflow_config_dict = self._config_manager.get_config("custom_workflow", workflow_name)
    workflow_config = CustomWorkflowConfig(**workflow_config_dict)

    # Create executor with dynamic module loading
    workflow_executor = CustomWorkflowExecutor(config=workflow_config)
    ```

    **Phase 2: Dynamic Execution**
    ```python
    # Execute with engine reference for component access
    result = await workflow_executor.execute(
        initial_input=initial_input,
        executor=self,  # Engine passed for dynamic component execution
        session_id=session_id
    )
    ```

    **Key Features**:
    - **Dynamic Component Access**: Custom workflows can execute agents and other workflows through the engine
    - **Flexible Session Management**: Session handling delegated to custom workflow implementation
    - **Type Safety**: Input/output type validation through workflow executor
    - **Error Propagation**: Custom workflow errors wrapped with execution context

=== "Streaming Execution Flow"

    **Objective**: Provide real-time event streaming for interactive agent execution with comprehensive state management.

    ```mermaid
    flowchart TD
        A[Streaming Request] --> B[Agent Preparation]
        B --> C[Session Info Event]
        C --> D[Event Stream Loop]
        D --> E[State Management]
        E --> F[History Persistence]
        F --> G[Resource Cleanup]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style G fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style D fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
        style E fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    ```

    **Phase 1: Streaming Setup**
    ```python
    # Auto-generate session ID for agents with history
    if not session_id:
        agent_config_dict = self._config_manager.get_config("agent", agent_name)
        if agent_config_dict:
            agent_config = AgentConfig(**agent_config_dict)
            if agent_config.include_history:
                session_id = f"agent-{uuid.uuid4().hex[:8]}"

    # Prepare agent with same flow as synchronous execution
    agent_instance, servers_to_unregister = await self._prepare_agent_for_run(
        agent_name, user_message, system_prompt, session_id
    )
    ```

    **Phase 2: Event Streaming**
    ```python
    # Yield session info as first event
    if session_id:
        yield {"type": "session_info", "data": {"session_id": session_id}}

    # Stream agent conversation events
    async for event in agent_instance.stream_conversation():
        yield event
    ```

    **Phase 3: State Management & Cleanup**
    ```python
    # Save conversation history in finally block
    if agent_instance and agent_instance.config.include_history and session_id and self._session_manager:
        self._session_manager.save_conversation_history(
            session_id=session_id,
            conversation=agent_instance.conversation_history,
            agent_name=agent_name,
        )

    # Keep dynamically registered servers active for future use
    if servers_to_unregister:
        logger.debug(f"Keeping {len(servers_to_unregister)} dynamically registered servers active")
    ```

    **Error Handling in Streaming**:
    ```python
    try:
        # Streaming execution
        async for event in agent_instance.stream_conversation():
            yield event
    except Exception as e:
        error_msg = f"Error during streaming execution for Agent '{agent_name}': {type(e).__name__}: {str(e)}"
        yield {"type": "error", "data": {"message": error_msg}}
        raise AgentExecutionError(error_msg) from e
    ```

## JIT Registration Integration

### Registration Trigger Points

- **Agent Execution**: Servers registered during `_prepare_agent_for_run`
- **Workflow Steps**: Each step triggers its own JIT registration through recursive engine calls
- **Streaming Execution**: Same registration flow as synchronous agent execution

### Server Lifecycle Management

**Registration Strategy**:

- **On-Demand**: Servers registered only when required by specific components
- **Persistent**: Registered servers remain active for subsequent executions
- **Shared**: Multiple agents can use the same registered servers

## References

- **Implementation**: `src/aurite/execution/aurite_engine.py` - Main AuriteEngine implementation
- **Design Details**: [AuriteEngine Design](../design/aurite_engine_design.md) - Architecture and design patterns
- **Configuration Integration**: [Configuration Index Building Flow](config_index_building_flow.md) - ConfigManager integration
- **Resource Management**: [MCP Server Registration Flow](mcp_server_registration_flow.md) - MCPHost integration
