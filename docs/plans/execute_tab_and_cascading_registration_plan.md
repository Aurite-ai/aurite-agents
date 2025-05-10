# Implementation Plan: Execute Tab & Cascading Component Registration

**Objective:**
1.  Implement cascading registration logic in the backend: when a component (Simple Workflow, Agent) is registered, its sub-components (Agents for Workflows, LLMConfigs for Agents) are also re-registered from their source configuration files.
2.  Introduce a new "Execute" tab in the frontend.
3.  Initially, implement a simple chatbot UI within the "Execute" tab for interacting with registered "Agents".
4.  Before execution via the UI, the selected component and its dependencies will be re-registered to ensure the active configuration is fresh.

## Phase 1: Backend - Cascading Registration & API Updates

**Target File 1: `src/host_manager.py`**

1.  **Modify `register_llm_config(self, llm_config: LLMConfig)`:**
    *   Remove the check `if llm_config.llm_id in active_project.llms: raise ValueError(...)`.
    *   The call to `self.project_manager.add_component_to_active_project("llms", ...)` will handle overwriting/updating if the ID already exists. This makes the method idempotent for content updates.

2.  **Modify `register_agent(self, agent_config: AgentConfig)`:**
    *   Remove the check `if agent_config.name in active_project.agents: raise ValueError(...)`.
    *   **Cascading Logic:**
        *   Before `self.project_manager.add_component_to_active_project("agents", ...)`:
            *   If `agent_config.llm_config_id` is present:
                *   Log the intent to register/update the LLM config.
                *   Retrieve the full `LLMConfig` object from `self.component_manager.get_component_config("llm_configs", agent_config.llm_config_id)`.
                *   If `retrieved_llm_config` is found, call `await self.register_llm_config(retrieved_llm_config)`.
                *   If not found, log an error but allow agent registration to proceed (the agent might function with only model/temp overrides or fail at runtime if LLM is truly needed). Consider if this should be a hard error. For "refresh" semantics, it should ideally be an error if a referenced dependency is missing from the source files.
    *   The call to `self.project_manager.add_component_to_active_project("agents", ...)` will update the agent.

3.  **Modify `register_workflow(self, workflow_config: WorkflowConfig)` (for Simple Workflows):**
    *   Remove the check `if workflow_config.name in active_project.simple_workflows: raise ValueError(...)`.
    *   **Cascading Logic:**
        *   Before `self.project_manager.add_component_to_active_project("simple_workflows", ...)`:
            *   For each `agent_name` in `workflow_config.steps`:
                *   Log the intent to register/update this agent step.
                *   Retrieve the full `AgentConfig` from `self.component_manager.get_component_config("agents", agent_name)`.
                *   If `retrieved_agent_config` is found, call `await self.register_agent(retrieved_agent_config)` (this will trigger its own cascading LLM registration).
                *   If not found, this is a critical error for the workflow. Raise `ValueError(f"Agent '{agent_name}' in workflow '{workflow_config.name}' not found in ComponentManager.")`.
    *   The call to `self.project_manager.add_component_to_active_project("simple_workflows", ...)` will update the workflow.

4.  **Modify `register_custom_workflow` (if necessary):**
    *   Similar to others, remove the check that raises ValueError if the custom workflow name already exists, allowing for updates.

**Target File 2: `src/bin/api/routes/components_api.py`**

1.  **New Endpoint: `POST /llm-configs/register`**
    *   Path: `/llm-configs/register`
    *   Method: `POST`
    *   Request Body: `LLMConfig` model.
    *   Action: Calls `await manager.register_llm_config(llm_config_from_body)`.
    *   Response: `{"status": "success", "llm_id": llm_config.llm_id}`.

2.  **Review existing registration endpoints (`/clients/register`, `/agents/register`, `/workflows/register`):**
    *   Ensure they correctly pass the full config object from the request body to the respective `HostManager.register_...` methods. This seems to be the case already.

## Phase 2: Frontend - Execute Tab UI & Logic

**Target File 1: `frontend/src/App.tsx` (or main layout component)**
1.  Add "Execute" as a top-level navigation item/tab.
2.  Set up routing for `/execute` path, likely rendering a layout that includes the `ExecuteSidebar` and a content area.

**Target File 2: `frontend/src/components/layout/ComponentSidebar.tsx` (or new `ExecuteSidebar.tsx`)**
1.  Define a new set of selectable items for the "Execute" mode:
    ```typescript
    export type ExecutableComponentType = 'agents' | 'simple_workflows' | 'custom_workflows'; // Add 'llms' if direct LLM execution is desired
    const executableComponentTypes: { id: ExecutableComponentType; label: string }[] = [
      { id: 'agents', label: 'Agents' },
      { id: 'simple_workflows', label: 'Simple Workflows' },
      { id: 'custom_workflows', label: 'Custom Workflows' },
    ];
    ```
2.  Conditionally render this list when the "Execute" tab is active.
3.  Update `selectedComponent` state in `useUIStore` (or a new store for execute state) to hold `ExecutableComponentType | null`.

**Target File 3: `frontend/src/features/execute/views/ExecuteListView.tsx` (New or adapted from `ConfigListView`)**
1.  Displays a list of available components of the selected `ExecutableComponentType`.
2.  Fetches data using new API client functions:
    *   If type is "agents": `GET /api/components/agents` (lists registered agents).
    *   (Similarly for workflows later).
3.  When an agent is selected, navigate to `AgentChatView`, passing the `agentName`.

**Target File 4: `frontend/src/features/execute/views/AgentChatView.tsx` (New Component)**
1.  **Props:** `agentName: string`.
2.  **State:**
    *   `messages: Array<{ role: 'user' | 'assistant' | 'error'; content: string }>`
    *   `inputValue: string`
    *   `isLoading: boolean` (for execution in progress)
    *   `error: string | null`
3.  **UI:**
    *   Area to display `messages`.
    *   Text input for `inputValue`.
    *   "Send" button.
4.  **`handleSend` Logic:**
    *   Set `isLoading = true`, clear `error`.
    *   Add user message to `messages` array.
    *   **Pre-Execution Registration Steps:**
        a.  Fetch `AgentConfig`: `await getConfigFileContent("agents", `${agentName}.json`)`.
        b.  If `agentConfig.llm_config_id`:
            i.  Fetch `LLMConfig`: `await getConfigFileContent("llms", `${agentConfig.llm_config_id}.json`)`.
            ii. Register LLM: `await registerLlmConfigAPI(llmConfig)`. (New API client function).
        c.  Register Agent: `await registerAgentAPI(agentConfig)`. (New API client function).
        d.  Handle any errors from registration steps; display to user and stop.
    *   **Execute Agent:**
        *   Call `await executeAgentAPI(agentName, inputValue)`. (New API client function).
        *   Add assistant's response or tool calls to `messages`. If error, add error message.
    *   Set `isLoading = false`.
    *   Clear `inputValue`.

## Phase 3: Frontend - API Client Updates (`frontend/src/lib/apiClient.ts`)

1.  **New function `registerLlmConfigAPI(llmConfig: LLMConfig): Promise<any>`:**
    *   Calls `POST /api/llm-configs/register` with `llmConfig` in the body.
2.  **New function `registerAgentAPI(agentConfig: AgentConfig): Promise<any>`:**
    *   Calls `POST /api/agents/register` with `agentConfig` in the body.
3.  **New function `registerWorkflowAPI(workflowConfig: WorkflowConfig): Promise<any>`:** (For later use)
    *   Calls `POST /api/workflows/register` with `workflowConfig`.
4.  **New function `executeAgentAPI(agentName: string, userMessage: string, systemPrompt?: string): Promise<AgentExecutionResult>`:**
    *   Calls `POST /api/agents/${agentName}/execute` with `{ user_message: userMessage, system_prompt: systemPrompt }`.
5.  **New function `listRegisteredAgents(): Promise<string[]>`:**
    *   Calls `GET /api/components/agents`.
6.  **(For later) Similar list and execute functions for simple and custom workflows.**

## Phase 4: State Management (Consider `useExecuteStore.ts` or similar)
*   A new Zustand store might be useful for managing the state related to the "Execute" tab, such as:
    *   `selectedExecutableComponentType: ExecutableComponentType | null`
    *   `availableExecutableComponents: string[]`
    *   `currentChatSessionId: string | null` (if implementing history)
    *   Actions to fetch lists of executable components.

This plan outlines a significant feature. We'll proceed step-by-step.
