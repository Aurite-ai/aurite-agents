# Projects and Workspaces

The Aurite framework uses a powerful hierarchical configuration system to manage components like agents, LLMs, and MCP servers. This system is built on two core concepts: **Projects** and **Workspaces**. Understanding how they work is key to organizing your configurations effectively.

## The `.aurite` Anchor File

The entire configuration system is driven by a special file named `.aurite`. This file acts as an "anchor," telling the framework that a directory is the root of either a project or a workspace.

When you run a command, the framework searches upwards from your current directory, looking for all `.aurite` files. This creates a chain of contexts, allowing for powerful and flexible configuration management.

### Defining a Project

A **Project** is the most common organizational unit. It's a self-contained directory that holds all the necessary configurations for a specific task or set of related tasks.

To define a project, create a `.aurite` file in its root directory with the following content:

```toml
# .aurite
[aurite]
type = "project"
include_configs = ["config"]
```

-   **`type = "project"`**: This line is mandatory and identifies the directory as a project root.
-   **`include_configs = ["config"]`**: This tells the `ConfigManager` to look inside the `config/` directory (relative to the `.aurite`) for your component configuration files (`.json` or `.yaml`). You can list multiple directories here to add the configurations located in those directories to the project.

### Defining a Workspace

A **Workspace** is a higher-level container that can manage multiple projects. This is useful when you have several related projects that might share common configurations (like a set of standard LLMs or MCP servers).

To define a workspace, create a `.aurite` file in its root directory:

```toml
# .aurite
[aurite]
type = "workspace"
projects = ["project-a", "project-b"]
include_configs = ["workspace-config"]
```

-   **`type = "workspace"`**: Identifies the directory as a workspace root.
-   **`projects = [...]`**: An optional list of subdirectories that are individual projects. The `ConfigManager` will be aware of these projects when operating from the workspace root.
-   **`include_configs = [...]`**: Specifies directories containing shared, workspace-level configurations.

## Configuration Loading and Priority

When the framework looks for a component (e.g., an agent named `my-agent`), it searches the contexts in a specific order of priority, from most specific to most general. A component found in a higher-priority context will override one with the same name from a lower-priority context.
The priority is as follows:

1.  **Project Level**: Configurations found in the `include_configs` directories of the current project's `.aurite` file.
2.  **Workspace Level**: Configurations found in the `include_configs` directories of the parent workspace's `.aurite` file.
3.  **User Level**: Global configurations located in your home directory at `~/.aurite/`.

This hierarchy allows you to define a default "development" LLM at the user level, a "standard-production" LLM at the workspace level, and a highly specialized "task-specific" LLM at the project level, all using the same component name. The framework will automatically pick the most specific one based on your current location.

## Duplicate Component Names
The configuration folders are listed by priority, so a configuration folder that is first in the include_configs list will have a higher priority than the ones that come after it.

## How Paths are Resolved

When you define a component that references a local file, such as an `mcp_server` with a `server_path` or a `custom_workflow` with a `module_path`, you can use a relative path.

The framework is smart about resolving these paths. **All relative paths are resolved from the location of the `.aurite` file that defines their context.**

**Example:**

-   Your workspace is at `/path/to/my-workspace/`.
-   Its `.aurite` file is at `/path/to/my-workspace/.aurite`.
-   You have a shared MCP server defined in `/path/to/my-workspace/workspace-config/servers.json`.
-   The server's `server_path` is set to `mcp_servers/shared_server.py`.

The framework will correctly resolve the full path to `/path/to/my-workspace/mcp_servers/shared_server.py`. This makes your configurations portable and easy to share.
