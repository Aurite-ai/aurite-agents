# Configuration Index Building Flow

This document explains how the Aurite Framework builds its configuration index by discovering and processing `.aurite` files throughout the project hierarchy.

## Overview

The configuration system uses a three-phase process to build a comprehensive index of all available components (agents, LLMs, MCP servers, workflows). The system respects a priority hierarchy where the current context (project or workspace) takes precedence.

## Core Concepts

### Priority Principle

**Priority order from highest to lowest:**

1. **In-Memory Registrations** (programmatic components for testing/notebooks)
2. **Current Context** (project if in project, workspace if in workspace)
3. **Shared Configurations** (workspace-level shared configs)
4. **Other Projects** (other projects in workspace, in order)
5. **User Global** (~/.aurite directory)

### File Structure Example

```tree
my_workspace/
├── .aurite
|   # type="workspace"
│   # projects: ["project_alpha", "project_bravo"]
│   # include_configs: ["config"]
│
├── config/
│   ├── agents/
│   │   └── shared_agents.json
│   ├── mcp_servers/
│   │   └── shared_servers.json
│   └── llms/
│       └── company_llms.json
│
├── project_alpha/
│   ├── .aurite
|   |   # type="project"
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
    ├── .aurite
    |   # type="project"
    │   # include_configs: ["config"]
    └── config/
        ├── agents/
        │   └── bravo_agents.json
        └── mcp_servers/
            └── bravo_servers.json
```

## Three-Phase Index Building Process

The ConfigManager builds its index through three distinct phases, each with specific responsibilities and outcomes. This ensures reliable configuration discovery and proper priority resolution.

=== "Phase 1: Context Discovery"

    **Objective**: Find all `.aurite` files and establish the configuration hierarchy with proper priority ordering.

    ```mermaid
    flowchart TD
        A[ConfigManager.__init__] --> B[find_anchor_files]
        B --> C{.aurite found?}
        C -->|Yes| D[Parse TOML content]
        C -->|No| E[Move up directory]
        E --> C
        D --> F{Determine type}
        F -->|workspace| G[Add to workspace context]
        F -->|project| H[Add to project context]
        G --> I[Build context hierarchy]
        H --> I
        I --> J[Context discovery complete]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style J fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style F fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style C fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
        style G fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
        style H fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
    ```

    **Key Steps**:

    **1. Search for .aurite files**:
    ```python
    def find_anchor_files(start_path: Path) -> List[Path]:
        anchor_files = []
        current_path = start_path.resolve()

        while True:
            anchor_file = current_path / ".aurite"
            if anchor_file.is_file():
                anchor_files.append(anchor_file)

            if current_path.parent == current_path:  # Filesystem root
                break
            current_path = current_path.parent

        return anchor_files  # Ordered from closest to furthest
    ```

    **2. Parse and categorize**:
    ```python
    # Parse each .aurite file to determine context type
    for anchor_path in anchor_files:
        with open(anchor_path, "rb") as f:
            settings = tomllib.load(f).get("aurite", {})

        context_type = settings.get("type")
        if context_type == "project":
            self.project_root = anchor_path.parent
        elif context_type == "workspace":
            self.workspace_root = anchor_path.parent
    ```

    **3. Build priority hierarchy**:

    **When in PROJECT context:**
    ```
    1. In-Memory Registrations (highest priority)
    2. Current Project
    3. Workspace (shared configs)
    4. Other Projects (in workspace order)
    5. User Global (~/.aurite)
    ```

    **When in WORKSPACE context:**
    ```
    1. In-Memory Registrations (highest priority)
    2. Workspace
    3. All Projects (in workspace order)
    4. User Global (~/.aurite)
    ```

    <!-- prettier-ignore -->
    !!! note "In-Memory Registration Priority"
        In-memory registrations always have the highest priority regardless of context. This supports:

        - **Testing Environments**: Override configurations for unit tests
        - **Jupyter Notebooks**: Programmatic component registration for experimentation
        - **Development Workflows**: Temporary configuration overrides without file modifications

    **Example Results**:

    **Running from project_bravo/**:
    ```
    Context Order:
    project_bravo → /path/to/my_workspace/project_bravo
    my_workspace → /path/to/my_workspace
    project_alpha → /path/to/my_workspace/project_alpha
    ```

    **Running from my_workspace/**:
    ```
    Context Order:
    my_workspace → /path/to/my_workspace
    project_alpha → /path/to/my_workspace/project_alpha
    project_bravo → /path/to/my_workspace/project_bravo
    ```

=== "Phase 2: Source Discovery"

    **Objective**: Extract `include_configs` paths from each `.aurite` file in priority order and build the ordered source list.

    ```mermaid
    flowchart TD
        A[_initialize_sources] --> B[For each context in priority order]
        B --> C[Read .aurite include_configs list]
        C --> D[Resolve paths relative to .aurite location]
        D --> E[Convert relative paths to absolute]
        E --> F{More contexts?}
        F -->|Yes| B
        F -->|No| G[Build ordered source list]
        G --> H[Source discovery complete]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style H fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style F fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
        style G fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style C fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
        style D fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
        style E fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
    ```

    **Key Activities**:
    - Extract `include_configs` paths from each `.aurite` file in priority order
    - Resolve paths relative to their `.aurite` file locations
    - Convert relative paths to absolute paths for consistent access
    - Build ordered source list respecting priority hierarchy

    **Example Configuration Sources (from project_bravo)**:
    ```
    1. /path/to/my_workspace/project_bravo/config        (current project - highest)
    2. /path/to/my_workspace/config                      (workspace shared)
    3. /path/to/my_workspace/project_alpha/config        (other project)
    4. /path/to/my_workspace/project_alpha/shared_config (other project)
    5. ~/.aurite                                         (user global - lowest)
    ```

=== "Phase 3: Component Indexing"

    **Objective**: Scan configuration directories and build the final component index with proper conflict resolution.

    ```mermaid
    flowchart TD
        A[_build_component_index] --> B[For each source directory in order]
        B --> C[Scan for config files]
        C --> D[*.json, *.yaml, *.yml]
        D --> E[For each file]
        E --> F[Parse as array of components]
        F --> G[For each component]
        G --> H{Already indexed?}
        H -->|Yes| I[Skip - first wins]
        H -->|No| J[Add to index with metadata]
        J --> K{More components?}
        I --> K
        K -->|Yes| G
        K -->|No| L{More files?}
        L -->|Yes| E
        L -->|No| M{More sources?}
        M -->|Yes| B
        M -->|No| N[Component indexing complete]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style N fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style H fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
        style J fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
        style I fill:#F44336,stroke:#D32F2F,stroke-width:2px,color:#fff
        style C fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
        style F fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
    ```

    **Key Activities**:
    - Scan configuration directories for JSON/YAML files
    - Parse files as arrays of component configurations
    - Apply first-found-wins conflict resolution
    - Add metadata fields for traceability and path resolution

    **Component Metadata**
    Each indexed component includes the following metadata fields:

    - `_source_file`: Full path to the configuration file
    - `_context_path`: Root directory of the context (project/workspace)
    - `_context_level`: `"project"`, `"workspace"`, or `"user"`
    - `_project_name`: Name of the project (if applicable)
    - `_workspace_name`: Name of the workspace (if applicable)

    **Conflict Resolution**: When the same component name exists in multiple locations, the **first occurrence wins** based on the priority order.

## References

- **Implementation**: `src/aurite/lib/config/config_manager.py` - Main ConfigManager class
- **Design Details**: [ConfigManager Design](../design/config_manager_design.md) - Architecture and design patterns
