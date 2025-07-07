# Implementation Plan: Fix API Component Type Naming Inconsistency

**Type:** Bug Fix
**Date:** 2025-01-07
**Author:** Ryan
**Issue:** API endpoints return 404 for components due to plural/singular naming mismatch

## Goal
Fix the naming inconsistency between component types in configuration files (singular) and API endpoint paths (plural).

## Context
The API returns 404 errors when accessing components via plural paths (e.g., `/config/mcp_servers/weather_server`) because:
- Component types in config files use singular forms: `mcp_server`, `agent`, `llm`
- The API test suite uses plural forms: `mcp_servers`, `agents`, `llms`
- The CLI has built-in plural-to-singular mapping, but the API does not

## Root Cause Analysis
- **Expected Behavior:** API should accept both plural and singular forms, or consistently use one
- **Actual Behavior:** API only works with exact component type names (singular)
- **Root Cause:** No plural-to-singular mapping in API routes like the CLI has
- **Affected Components:**
  - `tests/e2e/api/config_manager_routes.json` (uses plural forms)
  - `src/aurite/bin/api/routes/config_manager_routes.py` (no plural handling)

## Implementation Steps

### Option 1: Update Tests to Use Singular Forms (Simplest)
1. **Action:** Update `tests/e2e/api/config_manager_routes.json`
   - Change `/config/mcp_servers` to `/config/mcp_server`
   - Change `/config/mcp_servers/weather_server` to `/config/mcp_server/weather_server`
2. **Action:** Update any other test files that use plural forms
3. **Verification:** Run the updated tests to confirm they pass

### Option 2: Add Plural-to-Singular Mapping in API (More User-Friendly)
1. **Action:** Create a mapping dictionary in `src/aurite/bin/api/routes/config_manager_routes.py`
   ```python
   PLURAL_TO_SINGULAR = {
       "agents": "agent",
       "llms": "llm",
       "mcp_servers": "mcp_server",
       "simple_workflows": "simple_workflow",
       "custom_workflows": "custom_workflow"
   }
   ```
2. **Action:** Update route handlers to check for plural forms and convert
3. **Action:** Add tests for both singular and plural forms
4. **Verification:** Run original tests without modification

### Recommended Approach
Option 2 is recommended as it provides a better user experience and maintains consistency with the CLI behavior.

## Testing Strategy
- Run `tests/e2e/api/config_manager_routes.json` to verify the fix
- Create additional tests for multi-project workspace scenarios
- Verify no regression in CLI functionality

## Documentation Updates
- Update `docs/config/projects_and_workspaces.md` to clarify API behavior in workspaces
- Add notes about workspace context in API documentation

## Changelog
- v1.0 (2025-01-07): Initial plan
- v1.1 (2025-01-07): Implemented Option 2 - Added plural-to-singular mapping in API routes
  - Added PLURAL_TO_SINGULAR dictionary in config_manager_routes.py
  - Updated list_components_by_type to convert plural to singular
  - Updated get_component_by_id to convert plural to singular
  - All tests now pass without modification
