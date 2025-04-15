# Implementation Plan: Agent-Level Component Filtering

**Objective:** Add optional `include_components` and `exclude_components` lists to `AgentConfig` for fine-grained control over accessible MCP components (tools, prompts, resources) per agent.

**Owner:** Gemini

**Status:** Proposed

**Date:** 2025-04-14

---

## 1. Technical Specifications

### 1.1. Component Naming Convention

Components within the filter lists will use the format: `{type}:{name}`.
*   **Tools:** `tool:{tool_name}` (e.g., `tool:save_plan`)
*   **Prompts:** `prompt:{prompt_name}` (e.g., `prompt:create_plan_prompt`)
*   **Resources:** `resource:{resource_uri}` (e.g., `resource:planning://plan/my_plan`)

### 1.2. Model Changes (`src/host/models.py`)

Modify `AgentConfig`:
```python
class AgentConfig(BaseModel):
    # ... existing fields ...
    client_ids: Optional[List[str]] = None
    # NEW: List of components to explicitly allow (acts as allowlist if not None)
    include_components: Optional[List[str]] = Field(None, description="Explicit list of allowed components (e.g., ['tool:get_weather', 'prompt:weather_report']). If set, only these are usable.")
    # NEW: List of components to explicitly deny (takes precedence over include)
    exclude_components: Optional[List[str]] = Field(None, description="Explicit list of disallowed components (e.g., ['tool:save_plan']). Takes precedence over include_components.")
    # ... existing fields ...
```

### 1.3. Configuration Loading (`src/config.py`)

Update `load_host_config_from_json` to parse `include_components` and `exclude_components` from the `agents` section of the JSON configuration file and populate the `AgentConfig` model correctly.

### 1.4. Host Filtering Logic (`src/host/host.py`)

Modify `MCPHost.get_prompt`, `MCPHost.execute_tool`, and `MCPHost.read_resource`:

*   **Add Parameters:** Add `include_filters: Optional[List[str]] = None` and `exclude_filters: Optional[List[str]] = None` to the method signatures.
*   **Filtering Logic:**
    1.  Determine the potential providing clients based on the existing `filter_client_ids` logic.
    2.  For each potential client and the requested component (tool, prompt, or resource):
        a.  Construct the component identifier string (e.g., `tool:save_plan`).
        b.  Check against `exclude_filters`: If the identifier is in `exclude_filters`, this client cannot provide this component for this agent. Skip this client for this component.
        c.  Check against `include_filters`: If `include_filters` is not `None` *and* the identifier is *not* in `include_filters`, this client cannot provide this component for this agent. Skip this client for this component.
    3.  After applying these filters, proceed with the existing logic to check for ambiguity (multiple valid clients remaining) or non-existence (no valid clients remaining).
    4.  Ensure error messages clearly indicate if a component was not found *due to filtering* versus not being available at all.

### 1.5. Agent Execution (`src/agents/agent.py`)

Modify `Agent.execute_agent`:
*   When calling `host_instance.get_prompt`, `host_instance.execute_tool`, or `host_instance.read_resource`, pass the agent's `self.config.include_components` and `self.config.exclude_components` as the `include_filters` and `exclude_filters` arguments, respectively.

### 1.6. Test Configuration Helper (`tests/config/__init__.py`)

Create a helper function:
```python
# tests/config/__init__.py
from pathlib import Path
import json
from typing import Any, Dict # Added Dict
from src.config import PROJECT_ROOT_DIR # Assuming this is defined

CONFIG_DIR = PROJECT_ROOT_DIR / "config"

def load_test_config(config_filename: str) -> Dict[str, Any]:
    """Loads a JSON configuration file from the config directory for testing."""
    config_path = CONFIG_DIR / config_filename
    if not config_path.exists():
        raise FileNotFoundError(f"Test configuration file not found: {config_path}")
    with open(config_path, 'r') as f:
        return json.load(f)

```

### 1.7. Test Configuration Data (`config/deployment_testing.json`)

Update an existing agent definition to include filters. Example:
```json
// ... inside "agents": [ ... ]
{
  "name": "Weather Planning Agent",
  "system_prompt": "Your job is to use the tools at your disposal...",
  "client_ids": ["weather_server", "planning_server"],
  "model": "claude-3-opus-20240229",
  // ... other fields ...
  "exclude_components": [
    "tool:save_plan" // Exclude the save_plan tool specifically for this agent
  ]
  // "include_components": null // Or specify includes
},
// ...
```

### 1.8. New Test File (`tests/agents/test_agent_filtering.py`)

Create this file with `pytest` tests using the `deployment_testing.json` config (loaded via the new helper). Tests should cover:
*   Successful use of an allowed tool/prompt/resource.
*   Attempted use of an excluded tool/prompt/resource (expect specific error).
*   Attempted use of a non-included tool/prompt/resource when `include_components` is active (expect specific error).
*   Interaction between `client_ids` and component filters (e.g., a tool exists on two clients, one client is excluded by `client_ids`, the tool is excluded by `exclude_components` - ensure it's blocked).
*   Cases where filters result in ambiguity errors or not-found errors.

---

## 2. Implementation Steps

1.  **(Self)** Create this plan document (`docs/plans/agent_filtering_plan.md`).
2.  Modify `AgentConfig` in `src/host/models.py` (Add `include_components`, `exclude_components`).
3.  Update `load_host_config_from_json` in `src/config.py` to parse new fields.
4.  Modify `MCPHost.get_prompt`, `MCPHost.execute_tool`, `MCPHost.read_resource` in `src/host/host.py` to accept and apply new filter parameters and logic.
5.  Modify `Agent.execute_agent` in `src/agents/agent.py` to pass filters to host methods.
6.  Create `load_test_config` helper function in `tests/config/__init__.py`.
7.  Update `config/deployment_testing.json` with example agent filters.
8.  Create `tests/agents/test_agent_filtering.py` with comprehensive test cases.
9.  Run all tests (`pytest`) and ensure they pass, debugging as necessary.

---

## 3. Anticipated Issues & Considerations

*   **Filter Logic Complexity:** Combining `client_ids`, `include_filters`, and `exclude_filters` requires careful implementation, especially regarding precedence (exclude > include > client_ids availability).
*   **Error Clarity:** Ensure errors clearly distinguish between a component being filtered out for the *specific agent* versus being unavailable entirely or ambiguous across allowed clients.
*   **Performance:** For hosts with many clients and components, filtering might add minor overhead, but likely negligible for typical use cases.
*   **Component Name Consistency:** The `type:name` convention must be strictly adhered to in configs and code.
