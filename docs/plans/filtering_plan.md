# Implementation Plan: Agent-Specific Component Filtering

**Date:** 2025-04-15
**Author:** Gemini (AI Assistant)
**Status:** In Progress

## 1. Goal

Implement a filtering mechanism that allows specific agents (`AgentConfig`) to exclude individual components (tools, prompts, resources) provided by the MCP clients (`ClientConfig`) they are configured to use. This adds a layer of granularity beyond the existing `ClientConfig.exclude` (which applies globally to a client) and `AgentConfig.client_ids` (which selects allowed clients).

## 2. Background

Currently, filtering occurs in two ways:
1.  **Client Exclusion (`ClientConfig.exclude`):** Components listed here are never registered for the specific client during `MCPHost` initialization. This affects all agents using that client.
2.  **Agent Client Selection (`AgentConfig.client_ids`):** An agent is restricted to only interact with clients specified in this list during runtime operations (tool execution, prompt/resource retrieval).

The requirement is to allow an agent, already permitted to use certain clients via `client_ids`, to be further restricted from using *specific* components offered by those allowed clients.

## 3. Proposed Approach: Dedicated FilteringManager

To avoid increasing the complexity of `MCPHost` and its resource managers (`ToolManager`, `PromptManager`, `ResourceManager`), we will create a dedicated `FilteringManager` class within a new file `src/host/filtering.py`. This manager will encapsulate all filtering logic:

*   `ClientConfig.exclude` (applied at registration time)
*   `AgentConfig.client_ids` (applied at runtime to select clients)
*   New: `AgentConfig.exclude_components` (applied at runtime to filter components from allowed clients)

`MCPHost` will instantiate and delegate filtering decisions to this manager.

## 4. Implementation Steps

1.  **Model Update (`src/host/models.py`):** ✅ Done (2025-04-15)
    *   Add a new optional field to `AgentConfig`:
        ```python
        exclude_components: Optional[List[str]] = Field(
            None,
            description="List of component names (tool, prompt, resource) to specifically exclude for this agent, even if provided by allowed clients."
        )
        ```

2.  **Config Loading (`src/config.py`):** ✅ Done (2025-04-15)
    *   Update the `load_host_config_from_json` function to parse and validate the new `exclude_components` field when creating `AgentConfig` objects.

3.  **Create `FilteringManager` (`src/host/filtering.py`):** ✅ Done (2025-04-15)
    *   Create the new file `src/host/filtering.py`.
    *   Define the `FilteringManager` class.
    *   Implement methods (async where necessary, depending on dependencies):
        *   `__init__(self, message_router: MessageRouter)`: Store necessary dependencies (like the router to know which client provides what).
        *   `is_registration_allowed(self, component_name: str, client_config: ClientConfig) -> bool`:
            *   Checks if `component_name` is in `client_config.exclude`.
            *   Returns `False` if excluded, `True` otherwise.
        *   `filter_clients_for_request(self, available_clients: List[str], agent_config: AgentConfig) -> List[str]`:
            *   If `agent_config.client_ids` is set, return the intersection of `available_clients` and `agent_config.client_ids`.
            *   If `agent_config.client_ids` is `None`, return `available_clients` as is.
        *   `is_component_allowed_for_agent(self, component_name: str, agent_config: AgentConfig) -> bool`:
            *   Checks if `agent_config.exclude_components` is set and if `component_name` is in it.
            *   Returns `False` if excluded, `True` otherwise.
        *   `filter_component_list(self, components: List[Dict[str, Any]], agent_config: AgentConfig) -> List[Dict[str, Any]]`:
            *   Filters a list of component dictionaries (e.g., tools formatted for LLM) based on `agent_config.exclude_components`. Assumes each dict has a 'name' key.

4.  **Integrate `FilteringManager` into `MCPHost` (`src/host/host.py`):** ✅ Done (2025-04-15)
    *   Import `FilteringManager`.
    *   Instantiate `FilteringManager` in `MCPHost.__init__`, passing the `_message_router`. Store it as `self._filtering_manager`.
    *   **Refactor `_initialize_client`:**
        *   The core logic for checking `ClientConfig.exclude` should move *into* the respective resource manager registration methods (`ToolManager.register_tool`, `PromptManager.register_client_prompts`, `ResourceManager.register_client_resources`). These managers will need access to the `FilteringManager` (passed during their initialization or via a method call) to use `is_registration_allowed`. *Alternatively, keep the check in `_initialize_client` but call the filtering manager method.* (Decision: Let's aim to push the check into the resource managers for better encapsulation).
    *   **Refactor Runtime Methods (`execute_tool`, `get_prompt`, `read_resource`):**
        *   These methods already accept `filter_client_ids` which corresponds to `AgentConfig.client_ids`. We need to enhance the logic:
        *   **Client Filtering:** Use `self._message_router` to find all clients providing the component. Then, use `self._filtering_manager.filter_clients_for_request` (passing the found clients and the relevant `AgentConfig`) to get the list of *allowed* clients for this agent. Handle cases where no allowed clients provide the component or ambiguity arises.
        *   **Component Filtering:** *Before* executing the tool/retrieving the prompt/resource on the chosen `target_client_id`, add a check:
            ```python
            agent_config = self.get_agent_config(agent_name) # Assuming agent_name is available or passed down
            if not self._filtering_manager.is_component_allowed_for_agent(component_name, agent_config):
                raise ValueError(f"Component '{component_name}' is excluded for agent '{agent_name}'.")
            ```
            *(Need to ensure `AgentConfig` is accessible in these methods, likely by passing `agent_name` or the config itself down from the caller, e.g., `Agent.execute`)*.
    *   **Add `get_formatted_tools` method:** Added convenience method to `MCPHost` to handle calling `ToolManager.format_tools_for_llm` with appropriate filters.

5.  **Update Resource Managers (`src/host/resources/*.py`):** ✅ Done (2025-04-15)
    *   Modify `ToolManager`, `PromptManager`, `ResourceManager` registration methods (`register_tool`, `register_client_prompts`, `register_client_resources`) to accept `client_config` and `filtering_manager` and call `filtering_manager.is_registration_allowed` before registering a component.
    *   **Update `ToolManager.format_tools_for_llm`:**
        *   Accept `filtering_manager: FilteringManager` and `agent_config: AgentConfig` as arguments.
        *   Apply filtering based on `agent_config.client_ids` and `agent_config.exclude_components` using the `FilteringManager`.

6.  **Update `Agent` (`src/agents/agent.py`):** ✅ Done (2025-04-15)
    *   Remove `filter_client_ids` parameter from `execute_agent`.
    *   Update calls to `host_instance.get_formatted_tools` and `host_instance.execute_tool` to pass `agent_config=self.config`.

7.  **Testing (`tests/host/test_filtering.py`):** ⏳ In Progress
    *   ✅ Create a new test file `tests/host/test_filtering.py`. (2025-04-15)
    *   ✅ Add unit tests for `FilteringManager` methods and verify they pass. (2025-04-15)
    *   ⏳ Add integration tests using `MCPHost` and mock clients/agents:
        *   Verify `ClientConfig.exclude` still works correctly through the `FilteringManager`.
        *   Verify `AgentConfig.client_ids` filtering works correctly.
        *   Verify the new `AgentConfig.exclude_components` prevents listing (`format_tools_for_llm`) and execution/retrieval (`execute_tool`, `get_prompt`, `read_resource`) for specific agents.
        *   Test scenarios with combinations of filters.
        *   Test edge cases (empty lists, non-existent components).

## 5. Future Considerations

*   **`type:name` Filtering:** The `FilteringManager` structure makes it easier to later enhance `is_component_allowed_for_agent` and `exclude_components` to support syntax like `"tool:weather_lookup"` or `"prompt:system_intro"` for more precise exclusion. This would require passing the component type (`tool`, `prompt`, `resource`) to the filtering methods.
*   **Performance:** For very large numbers of components/clients/agents, the performance of filtering lookups could be considered, but standard list/dict operations should be sufficient initially.

## 6. Risks and Mitigation

*   **Refactoring Complexity:** Integrating the `FilteringManager` requires careful modification of `MCPHost` and resource managers. Mitigation: Perform changes step-by-step with thorough testing at each stage.
*   **Incorrect Filtering Logic:** Errors in the `FilteringManager` logic could lead to incorrect component access. Mitigation: Comprehensive unit and integration tests.
*   **Passing Agent Context:** Ensuring the correct `AgentConfig` is available deep within `MCPHost` calls requires careful propagation. Mitigation: Review call stacks and adjust method signatures as needed during implementation.
