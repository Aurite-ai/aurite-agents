# Implementation Plan: Configuration CRUD API

**Type:** Feature Development
**Date:** 2025-01-08
**Author:** Ryan
**Design Doc:** docs/usage/routes/config_manager_routes.md

## Goal
Implement a complete Configuration CRUD API system with:
- Separation of file operations into a dedicated `FileManager` class
- Enhanced `ConfigManager` to use the FileManager for all file operations
- Updated API routes with intelligent component creation logic
- Complete TypeScript client with tests
- Manual verification script for development testing

## Context
The current system has basic CRUD operations but lacks:
- File operation endpoints (list sources, list files, get/create/update/delete files)
- Intelligent component creation with decision tree logic
- Proper separation of concerns between configuration logic and file operations
- Enhanced response information (context, project/workspace details)

## Architecture Impact
- **New Components:**
  - `FileManager` class in `src/aurite/config/file_manager.py`
  - Test script `scripts/list_index_test.py` for manual verification
- **Modified Components:**
  - `ConfigManager` - refactored to use FileManager
  - `config_manager_routes.py` - new endpoints and enhanced logic
  - `ConfigManagerClient.ts` - new methods for file operations
- **Affected Layers:** Configuration layer, API layer, Frontend client

## Implementation Steps

### Phase 1: Create FileManager and Test Script
1. **Action:** Create `src/aurite/config/file_manager.py` with the FileManager class
   - Define class structure with initialization
   - Add path validation utilities
   - Add file format detection (JSON/YAML)
2. **Action:** Create `scripts/list_index_test.py` for manual verification
   - Basic script to instantiate ConfigManager
   - Print current index state
   - Show priority ordering
3. **Action:** Implement `list_config_sources()` method in FileManager
   - Return all configuration source directories with context info
4. **Action:** Write unit tests for FileManager initialization and list_config_sources
5. **Verification:** Run test script and unit tests to ensure basic structure works

### Phase 2: Update Priority System (moved from Phase 7)
6. **Action:** Refactor ConfigManager's `_initialize_sources()` to implement correct priority logic
   - Current context (project/workspace) has highest priority
   - Proper ordering based on execution context
7. **Action:** Update test script to verify priority resolution
8. **Action:** Write tests to verify priority resolution
9. **Verification:** Test configuration resolution from different contexts

### Phase 3: Implement File Listing Operations (formerly Phase 2)
10. **Action:** Add `list_config_files()` method to FileManager
    - Scan all sources for config files
    - Extract component metadata from each file
    - Include context information
11. **Action:** Update ConfigManager to expose file listing through FileManager
12. **Action:** Add GET `/config/sources` route
13. **Action:** Add GET `/config/files` route
14. **Action:** Update `scripts/list_index_test.py` to test file listing
15. **Action:** Update TypeScript client with `listConfigSources()` and `listConfigFiles()`
16. **Action:** Write tests for file listing operations
17. **Verification:** Test file listing through API and test script

### Phase 4: Implement File Content Operations (formerly Phase 3)
18. **Action:** Add `get_file_content()` method to FileManager
    - Validate file path
    - Read and return file content
19. **Action:** Update ConfigManager to expose file reading
20. **Action:** Add GET `/config/files/{file_path}` route
21. **Action:** Update test script to verify file content reading
22. **Action:** Update TypeScript client with `getFileContent()`
23. **Action:** Write tests for file reading
24. **Verification:** Test file reading through API and test script

### Phase 5: Implement File Creation (formerly Phase 4)
25. **Action:** Add `create_config_file()` method to FileManager
    - Validate path and content
    - Create directories if needed
    - Write file with proper formatting
26. **Action:** Update ConfigManager to expose file creation
27. **Action:** Add POST `/config/files` route with validation
28. **Action:** Update test script to verify file creation
29. **Action:** Update TypeScript client with `createConfigFile()`
30. **Action:** Write tests for file creation
31. **Verification:** Test file creation with various scenarios

### Phase 6: Implement File Update/Delete (formerly Phase 5)
32. **Action:** Add `update_config_file()` method to FileManager
33. **Action:** Add `delete_config_file()` method to FileManager
34. **Action:** Update ConfigManager to expose update/delete operations
35. **Action:** Add PUT `/config/files/{file_path}` route
36. **Action:** Add DELETE `/config/files/{file_path}` route
37. **Action:** Update test script to verify update/delete operations
38. **Action:** Update TypeScript client with `updateConfigFile()` and `deleteConfigFile()`
39. **Action:** Write tests for update/delete operations
40. **Verification:** Test all file operations

### Phase 7: Implement Intelligent Component Creation (formerly Phase 6)
41. **Action:** Add `find_or_create_component_file()` method to FileManager
    - Implement decision tree logic from documentation
    - Handle project/workspace context determination
    - Support file_path resolution
42. **Action:** Add `add_component_to_file()` method to FileManager
43. **Action:** Refactor ConfigManager's component creation to use new methods
44. **Action:** Update POST `/config/components/{component_type}` route
    - Add project/workspace/file_path parameters
    - Implement decision tree logic
    - Return enhanced response with context info
45. **Action:** Update test script to verify component creation logic
46. **Action:** Update TypeScript client's `createConfig()` with new parameters
47. **Action:** Write comprehensive tests for component creation scenarios
48. **Verification:** Test all decision tree paths

### Phase 8: Integration Testing
49. **Action:** Update `frontend/test-integration.ts` with comprehensive test scenarios
    - File operations
    - Component CRUD with various contexts
    - Error handling
50. **Action:** Run full integration test suite
51. **Verification:** All integration tests pass

### Phase 9: Documentation Updates
52. **Action:** Update inline documentation in all modified files
53. **Action:** Update `docs/architecture/config/` if needed
54. **Action:** Ensure API documentation is current

## Testing Strategy
- Unit tests for each FileManager method
- Unit tests for updated ConfigManager methods
- API route tests for all endpoints
- TypeScript client unit tests
- Comprehensive integration tests
- Manual verification with `scripts/list_index_test.py` at each phase
- Test from both project and workspace contexts

## Manual Test Script Structure
The `scripts/list_index_test.py` will evolve with each phase:
```python
# Phase 1: Basic index display
# Phase 2: Add priority verification
# Phase 3: Add file listing
# Phase 4: Add file content reading
# Phase 5: Add file creation test
# Phase 6: Add update/delete tests
# Phase 7: Add component creation tests
```

## Documentation Updates
See `.clinerules/documentation_guide.md` for documentation update requirements.

## Changelog
- v1.0 (2025-01-08): Initial plan with FileManager and test script
- v1.1 (2025-01-08): Moved Priority System update from Phase 7 to Phase 2 for proper foundation

---
