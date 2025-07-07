# Implementation Plan: Configuration API Endpoints

**Type:** Feature Development
**Date:** 2025-01-07
**Author:** Ryan
**Design Doc:** N/A

## Goal
Implement comprehensive Configuration Manager API endpoints to provide full CRUD operations for components, project/workspace management, configuration file operations, and template support. This includes updating the frontend client library and tests to ensure end-to-end functionality.

## Context
Currently, only basic read operations are implemented for the Configuration Manager API. We need to expand this to include full CRUD operations and additional management features. The API structure follows the pattern established in the Slack discussion, organizing endpoints under `/config/` with logical sub-paths.

## Architecture Impact
- **Affected Layers:** Entrypoints (API), Orchestration (ConfigManager)
- **New Components:** None
- **Modified Components:**
  - `src/aurite/bin/api/routes/config_manager_routes.py`
  - `src/aurite/config/config_manager.py`
  - `frontend/src/routes/ConfigManagerClient.ts`
  - `frontend/src/routes/ConfigManagerClient.test.ts`
  - `frontend/test-integration.ts`

## Implementation Steps

### Phase 1: Complete Component CRUD Operations

#### Backend Implementation
1. **Update existing routes to use new structure**
   - Change `/config/` to `/config/components`
   - Update `/config/{component_type}` to `/config/components/{component_type}`
   - Update `/config/{component_type}/{component_id}` to `/config/components/{component_type}/{component_id}`

2. **Implement POST endpoint for creating components**
   - Add `POST /config/components/{component_type}` route
   - Implement validation logic
   - Add create_config method to ConfigManager if needed

3. **Implement PUT endpoint for updating components**
   - Add `PUT /config/components/{component_type}/{component_id}` route
   - Implement update logic with validation
   - Add update_config method to ConfigManager if needed

4. **Implement DELETE endpoint for deleting components**
   - Add `DELETE /config/components/{component_type}/{component_id}` route
   - Implement safe deletion with dependency checking
   - Add delete_config method to ConfigManager if needed

5. **Implement validation endpoint**
   - Add `POST /config/components/{component_type}/{component_id}/validate` route
   - Implement component-specific validation logic

#### Frontend Implementation
6. **Update ConfigManagerClient routes**
   - Update all existing methods to use `/config/components/` prefix
   - Update the `reloadConfigs()` method to use `/config/refresh`

7. **Add validation method to ConfigManagerClient**
   - Add `validateConfig(configType: string, name: string)` method

#### Testing
8. **Update ConfigManagerClient.test.ts**
   - Update all test URLs to use new route structure
   - Add tests for validation method

9. **Update test-integration.ts**
   - Add test scenarios for create, update, delete operations
   - Add validation testing

10. **Update e2e test documentation**
    - Update `tests/e2e/api/config_manager_routes.json` with new endpoints

### Phase 2: Configuration File Operations

11. **Implement file listing endpoints**
    - Add `GET /config/sources` - List configuration sources
    - Add `GET /config/files` - List all configuration files

12. **Implement file CRUD operations**
    - Add `GET /config/files/{file_path}` - Get file content
    - Add `POST /config/files` - Create new file
    - Add `PUT /config/files/{file_path}` - Update file
    - Add `DELETE /config/files/{file_path}` - Delete file

13. **Implement utility endpoints**
    - Add `POST /config/refresh` - Force refresh cache
    - Add `POST /config/validate` - Validate all configurations

14. **Add ConfigManager methods for file operations**
    - Implement file management methods in ConfigManager
    - Add proper error handling for file operations

15. **Update frontend client with file operations**
    - Add corresponding methods to ConfigManagerClient
    - Add comprehensive tests

### Phase 3: Project & Workspace Management

16. **Implement project endpoints**
    - Add all project management endpoints as specified
    - Implement project switching logic
    - Add active project tracking

17. **Implement workspace endpoints**
    - Add workspace management endpoints
    - Implement workspace isolation

18. **Update ConfigManager for project/workspace support**
    - Add methods for project and workspace management
    - Ensure proper configuration isolation

19. **Update frontend client**
    - Add project and workspace methods
    - Add integration tests

### Phase 4: Configuration Templates

20. **Implement template endpoints**
    - Add `GET /config/templates` - List all templates
    - Add `GET /config/templates/{component_type}` - Get template
    - Add `POST /config/templates/{component_type}` - Create from template

21. **Add template support to ConfigManager**
    - Implement template loading and instantiation
    - Add template validation

22. **Update frontend client**
    - Add template methods
    - Add tests for template operations

## Testing Strategy
- Unit tests for each new ConfigManager method
- API route tests for each endpoint
- Frontend unit tests for each client method
- Integration tests covering full workflows
- E2E test documentation updates

## Documentation Updates
- Update `docs/usage/api_reference.md` as endpoints are implemented
- Update `docs/architecture/layers/1_entrypoints.md` with new routes
- Update `openapi.yaml` with new endpoint specifications

## Changelog
- v1.0 (2025-01-07): Initial plan
- v1.1 (2025-01-07): Completed Phase 1 - Component CRUD Operations
  - Updated routes to use `/config/components/` structure
  - Implemented POST, PUT, DELETE endpoints (with placeholders for ConfigManager methods)
  - Implemented validation endpoint with basic validation logic
  - Updated frontend client and tests to use new routes
  - Added validateConfig method to frontend client
  - Note: Need to implement create_config and delete_config methods in ConfigManager
  - Note: Need to implement /config/refresh endpoint
