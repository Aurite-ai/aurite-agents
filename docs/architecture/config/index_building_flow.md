# Configuration Index Building Flow

This document explains how the Aurite Framework builds its configuration index by discovering and processing `.aurite` files throughout the project hierarchy.

## Overview

The configuration system uses a three-phase process to build a comprehensive index of all available components (agents, LLMs, MCP servers, workflows). The system respects a priority hierarchy where the current context (project or workspace) takes precedence.

## Core Concepts

### Priority Principle
**Current context always has highest priority:**
- If you're in a project → that project's configs win
- If you're in the workspace → workspace configs win

### File Structure Example

```
my_workspace/
├── .aurite                          # type="workspace"
│   # projects: ["project_alpha", "project_bravo"]
│   # include_configs: ["config"]
│
├── config/                          # Workspace-level shared configs
│   ├── agents/
│   │   └── shared_agents.json
│   ├── mcp_servers/
│   │   └── shared_servers.json
│   └── llms/
│       └── company_llms.json
│
├── project_alpha/
│   ├── .aurite                      # type="project"
│   │   # include_configs: ["config", "shared_config"]
│   ├── config/
│   │   ├── agents/
│   │   │   └── alpha_agents.json
│   │   └── workflows/
│   │       └── alpha_workflows.json
│   └── shared_config/
│       └── alpha_shared.json
│
└── project_bravo/
    ├── .aurite                      # type="project"
    │   # include_configs: ["config"]
    └── config/
        ├── agents/
        │   └── bravo_agents.json
        └── mcp_servers/
            └── bravo_servers.json
```

## Three-Phase Index Building Process

### Phase 1: Context Discovery and Ordering

**Goal:** Find all `.aurite` files and establish the configuration hierarchy with proper priority ordering.

```
┌─────────────────┐
│ ConfigManager   │
│ .__init__()     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ find_anchor_    │────▶│ Search upward    │
│ files()         │     │ from CWD for     │
│                 │     │ .aurite files    │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Parse each      │────▶│ Determine type:  │
│ .aurite file    │     │ - workspace      │
│                 │     │ - project        │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│ Build initial   │
│ context map     │
└─────────────────┘
```

**Priority Rules:**

When CWD is a **PROJECT**:
```
1. Current Project (highest priority)
2. Workspace (shared configs)
3. Other Projects (in workspace order)
4. User Global (~/.aurite)
```

When CWD is the **WORKSPACE**:
```
1. Workspace (highest priority)
2. All Projects (in workspace order)
3. User Global (~/.aurite)
```

**Example Results:**

*Scenario 1: Running from `project_bravo/`*
```
Context Order:
project_bravo → /path/to/my_workspace/project_bravo
my_workspace → /path/to/my_workspace
project_alpha → /path/to/my_workspace/project_alpha
```

*Scenario 2: Running from `my_workspace/`*
```
Context Order:
my_workspace → /path/to/my_workspace
project_alpha → /path/to/my_workspace/project_alpha
project_bravo → /path/to/my_workspace/project_bravo
```

### Phase 2: Configuration Source Discovery

**Goal:** Extract `include_configs` paths from each `.aurite` file in priority order.

```
┌─────────────────┐
│ _initialize_    │
│ sources()       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ For each        │────▶│ Read .aurite     │
│ context in      │     │ include_configs  │
│ priority order  │     │ list             │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Resolve paths   │────▶│ Convert relative │
│ relative to     │     │ paths to         │
│ .aurite location│     │ absolute         │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│ Build ordered   │
│ source list     │
└─────────────────┘
```

**Example Configuration Sources (from project_bravo):**
```
1. /path/to/my_workspace/project_bravo/config        (current project - highest)
2. /path/to/my_workspace/config                      (workspace shared)
3. /path/to/my_workspace/project_alpha/config        (other project)
4. /path/to/my_workspace/project_alpha/shared_config (other project)
5. ~/.aurite                                         (user global - lowest)
```

### Phase 3: Component Indexing

**Goal:** Scan configuration directories and build the final component index.

```
┌─────────────────┐
│ _build_         │
│ component_      │
│ index()         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ For each source │────▶│ Scan for:        │
│ directory       │     │ - *.json         │
│ (in order)      │     │ - *.yaml/*.yml   │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ For each file   │────▶│ Parse as array   │
│                 │     │ of components    │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ For each        │────▶│ Check if already │
│ component       │     │ indexed (first   │
│                 │     │ wins)            │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│ Add to index    │
│ with metadata   │
└─────────────────┘
```

**Component Metadata:**
Each indexed component includes:
- `_source_file`: Full path to the configuration file
- `_context_path`: Root directory of the context (project/workspace)
- `_context_level`: "project", "workspace", or "user"
- `_project_name`: Name of the project (if applicable)
- `_workspace_name`: Name of the workspace (if applicable)

## Conflict Resolution

When the same component name exists in multiple locations, the **first occurrence wins** based on the priority order.

**Example:**
If "Weather Agent" exists in:
1. `project_bravo/config/agents/agents.json` (when running from project_bravo)
2. `my_workspace/config/agents/shared_agents.json`
3. `project_alpha/config/agents/agents.json`

The version from `project_bravo` will be used because it has the highest priority.

## Use Cases

### Workspace-Level Development
When running commands from the workspace root, workspace configurations take precedence. This is useful for:
- Testing shared components
- Managing workspace-wide settings
- Running administrative tasks

### Project-Level Development
When running commands from a project directory, that project's configurations take precedence. This ensures:
- Project-specific overrides work correctly
- Development is isolated from other projects
- Shared resources are still accessible

## Implementation Details

### Key Methods

1. **`find_anchor_files(start_path)`** - Searches upward for `.aurite` files
2. **`_initialize_sources()`** - Builds the ordered list of configuration sources
3. **`_build_component_index()`** - Scans sources and builds the component index
4. **`_parse_and_index_file()`** - Processes individual configuration files

### Code References

The implementation can be found in:
- `src/aurite/config/config_manager.py` - Main ConfigManager class
- `src/aurite/config/config_utils.py` - Utility functions like `find_anchor_files`

## Best Practices

1. **Organize by Context**: Keep project-specific configs in project directories, shared configs in workspace
2. **Use Descriptive Names**: Avoid naming conflicts by using descriptive component names
3. **Document Overrides**: When overriding a shared component, document why in the component description
4. **Test from Different Contexts**: Verify behavior by running from both project and workspace directories

## Future Considerations

As we implement the file operations API, we'll need to ensure that:
- New files are created in the appropriate context
- The priority system is respected when creating components
- Users can explicitly choose where to place new configurations
