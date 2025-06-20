# Packaged Directory Structure Refactor Plan

## 1. Overview

This refactor plan addresses inconsistencies between the directory structure created by the `aurite init` command and the source template directories in `src/aurite/packaged/`. The goal is to align the packaged template structure with what users actually receive when they initialize a new project.

## 2. Current State Analysis

### Current `src/aurite/packaged/` Structure
```
src/aurite/packaged/
├── component_configs/            # ❌ Should be renamed to 'config'
│   ├── agents/
│   ├── custom_workflows/
│   ├── llms/
│   ├── mcp_servers/
│   ├── projects/
│   └── workflows/
├── example_custom_workflows/     # ❌ Should be renamed to 'custom_workflows'
├── example_mcp_servers/          # ❌ Should be renamed to 'mcp_servers'
├── static_ui/
│   └── assets/
└── testing/
```

### What `aurite init` Creates for Users
```
user_project/
├── config/                       # ✅ This is what users expect
│   ├── agents/
│   ├── llms/
│   ├── mcp_servers/
│   ├── workflows/
│   ├── custom_workflows/
│   └── testing/
├── mcp_servers/          # ✅ This is what users expect
├── custom_workflows/     # ✅ This is what users expect
└── aurite_config.json
```

### Additional Issues
- `src/aurite/components/servers/` contains MCP servers that should be moved to the packaged directory
- `src/aurite/storage/` folder name conflicts with storage-related MCP servers, causing confusion

## 3. Refactor Changes

### 3.1 Rename Directories to Match `aurite init` Output

**Changes needed:**
1. `src/aurite/packaged/component_configs/` → `src/aurite/packaged/config/`
2. `src/aurite/packaged/example_custom_workflows/` → `src/aurite/packaged/custom_workflows/`
3. `src/aurite/packaged/example_mcp_servers/` → `src/aurite/packaged/mcp_servers/`

**Rationale:** The `aurite init` command creates directories with specific names (`config/`, `example_mcp_servers/`, `example_custom_workflows/`) but the source template directories have different names. This creates confusion and inconsistency between the template source and what users receive.

### 3.2 Move MCP Servers from Components to Packaged

**Move from:** `src/aurite/components/servers/`
**Move to:** `src/aurite/packaged/mcp_servers/`

**Files to Move:**
```
src/aurite/components/servers/
├── management/
│   ├── __init__.py
│   ├── evaluation_server.py
│   ├── planning_server.py
│   └── plans/
│       ├── san_francisco_what_to_wear.meta.json
│       └── san_francisco_what_to_wear.txt
├── memory/
│   ├── __init__.py
│   ├── mem0_hosted_server.py
│   ├── mem0_server.py
│   └── test.py
├── speech/
│   ├── __init__.py
│   ├── speech_server.py
│   ├── speech_workflow.py
│   └── test_audio/
│       └── speech_commercial_mono.wav
└── storage/
    ├── __init__.py
    ├── file_server.py
    └── sql/
        ├── __init__.py
        ├── sql_server.py
        └── vector/
            ├── __init__.py
            └── pgvector_server.py
```

### 3.3 Rename Storage Module to Avoid Confusion

**Current:** `src/aurite/storage/`
**New:** `src/aurite/persistence/`

**Rationale:** The current `storage` folder name conflicts with storage-related MCP servers, creating confusion about whether it refers to the framework's database persistence layer or MCP storage tools. Only the folder name will change - the files inside will keep their current names.

**Note:** This storage module is only used in `src/aurite/execution/facade.py`, making the refactor relatively contained.

## 4. Implementation Steps

### Step 1: Rename Packaged Template Directories
```bash
# Rename directories to match aurite init output
mv src/aurite/packaged/component_configs src/aurite/packaged/config
mv src/aurite/packaged/example_custom_workflows src/aurite/packaged/custom_workflows
mv src/aurite/packaged/example_mcp_servers src/aurite/packaged/mcp_servers
```

### Step 2: Move Component Servers to Packaged Directory
```bash
# Move all server categories to the packaged directory
mv src/aurite/components/servers/* src/aurite/packaged/mcp_servers/
```

### Step 3: Update CLI Main Script
Update `src/aurite/bin/cli/main.py` to reference the correct source paths:

**Current references to update:**
- `"component_configs/projects/default_project.json"` → `"config/projects/default_project.json"`
- `"component_configs/llms/example_llms.json"` → `"config/llms/example_llms.json"`
- `"component_configs/mcp_servers/example_mcp_servers.json"` → `"config/mcp_servers/example_mcp_servers.json"`
- `"component_configs/agents/example_agents.json"` → `"config/agents/example_agents.json"`
- `"component_configs/custom_workflows/example_custom_workflow.json"` → `"config/custom_workflows/example_custom_workflow.json"`
- `"example_custom_workflows/__init__.py"` → `"custom_workflows/__init__.py"`
- `"example_custom_workflows/example_workflow.py"` → `"custom_workflows/example_workflow.py"`
- `"example_mcp_servers/weather_mcp_server.py"` → `"mcp_servers/weather_mcp_server.py"`
- `"example_mcp_servers/planning_server.py"` → `"mcp_servers/planning_server.py"`

### Step 4: Rename Storage Module
```bash
# Rename the storage directory
mv src/aurite/storage src/aurite/persistence
```

### Step 5: Update Import References for Storage Module
Update the single import reference in `src/aurite/execution/facade.py`:
- `from ..storage.db_manager import StorageManager` → `from ..persistence.db_manager import StorageManager`

**Note:** Based on the codebase analysis, this is the only file that imports from the storage module, making this change very contained.

### Step 6: Update Documentation
Update all documentation files that reference the old directory structure:
- `.clinerules/package_development_rules.md`
- `docs/layers/framework_overview.md`
- Any other documentation mentioning the old paths

## 5. Files That Need Updates

### Python Files with Import Changes
- `src/aurite/execution/facade.py` (only file that imports from storage module)
- Test files in `tests/storage/` (directory should also be renamed to `tests/persistence/`)

### CLI Script Updates
- `src/aurite/bin/cli/main.py` - Update all packaged file paths to match new directory structure:
  - All `component_configs/` references → `config/`
  - All `example_custom_workflows/` references → `custom_workflows/`
  - All `example_mcp_servers/` references → `mcp_servers/`

### Configuration Files
- `MANIFEST.in` - Ensure new directory structure is included in package
- Any configuration files referencing old paths

### Documentation Updates
- All `.clinerules/*.md` files
- `docs/layers/*.md` files
- `README.md` and `README_packaged.md`
- Package installation guides

## 6. Testing Strategy

### Before Refactor
1. Run full test suite to establish baseline
2. Test `aurite init` command to document current behavior
3. Verify package build process works correctly

### After Refactor
1. Run full test suite to ensure no regressions
2. Test `aurite init` command with new structure
3. Verify all moved MCP servers are accessible
4. Test package build and installation process
5. Verify all documentation links and references work

### Specific Tests
- `pip install -e .` - Ensure editable install works
- `aurite init test_project` - Verify project scaffolding
- Import tests for renamed storage/persistence module
- MCP server functionality tests for moved servers

## 7. Risk Assessment

### Low Risk
- Renaming `example_mcp_servers` to `mcp_servers` in packaged templates
- Moving MCP servers from components to packaged directory

### Medium Risk
- Renaming storage module (affects imports across codebase)
- Updating CLI script paths

### Mitigation Strategies
- Perform changes in separate commits for easy rollback
- Test each step independently
- Update documentation immediately after code changes
- Use IDE refactoring tools for import updates where possible

## 8. Post-Refactor Validation

### User Experience Validation
1. Create a fresh project with `aurite init`
2. Verify all expected directories and files are present
3. Test that example MCP servers work correctly
4. Confirm no broken imports or missing files

### Developer Experience Validation
1. Verify all tests pass
2. Confirm package builds successfully
3. Test that development workflow remains intact
4. Validate that all documentation is accurate

## 9. Timeline

**Estimated Duration:** 1-2 days

**Phase 1 (Day 1):**
- Step 1: Rename packaged template directories to match `aurite init` output
- Step 2: Move component servers to packaged directory
- Step 3: Update CLI script with new paths
- Initial testing

**Phase 2 (Day 2):**
- Step 4: Rename storage module
- Step 5: Update storage import reference
- Step 6: Update documentation
- Comprehensive testing
- Final validation

## 10. Success Criteria

- [ ] `aurite init` creates consistent directory structure matching template source
- [ ] All packaged template directories match their intended user-facing names
- [ ] All MCP servers are accessible in their new location
- [ ] CLI script correctly references all new paths
- [ ] Storage module renamed without breaking functionality
- [ ] No broken imports or missing files
- [ ] All tests pass
- [ ] Package builds and installs correctly
- [ ] Documentation accurately reflects new structure
- [ ] No confusion between persistence module and storage MCP servers
