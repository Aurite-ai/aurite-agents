# :material-file-tree: Projects and Workspaces

The Aurite framework uses a powerful hierarchical configuration system built on two core concepts: **Projects** and **Workspaces**. This system is driven by a special anchor file named `.aurite`, which tells the framework how to discover and prioritize configurations.

!!! info "The `.aurite` Anchor File"
The framework finds configurations by searching upwards from your current directory for `.aurite` files. This file marks a directory as a **Project** or a **Workspace** root and specifies which subdirectories contain configuration files.

---

## Configuration Contexts

Your configurations are organized into contexts, allowing for both separation of concerns and sharing of common components.

=== ":material-folder-home-outline: Project"

    A **Project** is a self-contained directory for a specific task or set of related tasks. It's the most common organizational unit.

    To define a project, create an `.aurite` file in its root directory.

    **`.aurite` File Fields:**

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `type` | `string` | Yes | Must be set to `"project"`. |
    | `include_configs` | `list[string]` | Yes | A list of directories (relative to the `.aurite` file) where component configurations are stored. |

    **Example `.aurite`:**
    ```toml
    # .aurite
    [aurite]
    type = "project"
    include_configs = ["config", "shared_components"]
    ```

=== ":material-folder-multiple-outline: Workspace"

    A **Workspace** is a higher-level container that can manage multiple projects and shared configurations.

    **`.aurite` File Fields:**

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `type` | `string` | Yes | Must be set to `"workspace"`. |
    | `include_configs` | `list[string]` | Yes | A list of directories containing shared, workspace-level configurations. |
    | `projects` | `list[string]` | No | An optional list of subdirectories that are individual projects. |

    **Example `.aurite`:**
    ```toml
    # .aurite
    [aurite]
    type = "workspace"
    projects = ["project-a", "project-b"]
    include_configs = ["workspace_config"]
    ```

---

## :material-sort-variant: Priority Resolution

When the framework looks for a component, it searches contexts in a specific order. A component found in a higher-priority context overrides one with the same name from a lower-priority context.

The priority is as follows, from highest to lowest:

1.  **In-Memory**: Programmatically registered components (highest priority).
2.  **Project Level**: Configurations from the current project's `include_configs` directories.
3.  **Workspace Level**: Configurations from the parent workspace's `include_configs` directories.
4.  **Other Projects**: Configurations from other projects within the same workspace.
5.  **User Level**: Global configurations in `~/.aurite/` (lowest priority).

!!! example "Overriding Example"
You could define a default `dev-llm` at the user level, a `standard-llm` at the workspace level, and a `task-specific-llm` at the project level. The framework automatically picks the most specific one based on your current directory.

---

## :material-map-marker-path: Path Resolution

When a component configuration references a local file (e.g., `server_path` in an MCP server), you can use a relative path.

**All relative paths are resolved from the location of the `.aurite` file that defines their context.**

This makes your configurations portable and easy to share.

!!! abstract "Path Resolution Example" - Your workspace is at `/path/to/my-workspace/`. - Its `.aurite` file is at `/path/to/my-workspace/.aurite`. - A shared server is defined in `/path/to/my-workspace/workspace-config/servers.json`. - The server's `server_path` is set to `mcp_servers/shared_server.py`.

    The framework will correctly resolve the full path to `/path/to/my-workspace/mcp_servers/shared_server.py`.
