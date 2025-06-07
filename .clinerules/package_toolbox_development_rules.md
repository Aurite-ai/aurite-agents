# Project Rules: Packaged Toolbox Development

## 1. Objective

This document outlines the specific workflow for adding new pre-configured ("packaged") components to the `aurite` package's toolbox. This currently focuses on MCP Servers but will be expanded to include other components like Agents and Workflows. The goal is to ensure that new packaged components are tested, correctly configured, and well-documented for end-users.

## 2. Workflow for Adding Packaged MCP Servers

Follow these steps to add a new MCP server to the `aurite` package.

### Step 1: Identify and Test the Server

First, identify an MCP server that can be run via the command line (transport types `local` or `http_stream`). Use the functional MCP client to ensure it works as expected. The test should not just list the available tools, but should be a series of queries that require the LLM to actually use each of the tools to ensure they are all functioning correctly. Each tool's functionality must be fully working and verified before the server is added to the package.

*   **Action:** Run the server with a functional test query that validates a specific tool's behavior. If a tool requires data from another tool, the query should be phrased to execute both tools in sequence.
*   **Example:**
    ```bash
    python tests/functional_mcp_client.py '{"command": "npx", "args": ["-y", "@user/some-mcp-server"]}' "Use the 'search' tool to find an item, then use the 'get_details' tool to get the details of the first result."
    ```

### Step 2: Add Server Configuration

Once tested, add the server's configuration to a relevant JSON file in the `src/aurite/packaged/component_configs/mcp_servers/` directory. Group servers by category (e.g., `web_search_servers.json`, `data_science_tools.json`). If a server is generally useful but has specific tools that are broken or deprecated, you can use the `exclude` property in the server's configuration to disable them.

*   **Action:** Create or edit a JSON file in `src/aurite/packaged/component_configs/mcp_servers/`.
*   **Example:** Adding a server to `data_science_tools.json`:
    ```json
    [
      {
        "name": "my_data_tool_server",
        "transport_type": "http_stream",
        "command": "npx",
        "args": [
          "-y",
          "@smithery/cli@latest",
          "run",
          "@user/data-tool-mcp",
          "--key",
          "{SMITHERY_API_KEY}"
        ],
        "capabilities": ["tools"],
        "timeout": 20.0
      }
    ]
    ```

### Step 3: Create or Update the Category Documentation

Create or update the documentation file for the server's category in `docs/toolbox/servers/`. Use the `docs/toolbox/servers/template.md` as a base.

*   **Action:** Create or edit a markdown file in `docs/toolbox/servers/`.
*   **Example:** Creating `docs/toolbox/servers/data_science_servers.md` with details about the tools the server provides.

### Step 4: Update the Toolbox Directory

Add a link to your new category documentation file in the main directory document.

*   **Action:** Edit `docs/toolbox/mcp_server_directory.md` and add a new list item.
*   **Example:**
    ```markdown
    ## Server Categories
    *   **[Example Servers](servers/example_mcp_servers.md):** ...
    *   **[Data Science Tools](servers/data_science_servers.md):** Tools for data analysis and exploration.
    ```

### Step 5: Create or Update Agent Configuration

Create or update an agent configuration for the server in `src/aurite/packaged/component_configs/agents/`. The file should have the same name as the tool server's configuration file, but with 'agents' instead of 'servers'.

*   **Action:** Create or edit a JSON file in `src/aurite/packaged/component_configs/agents/`.
*   **Example:**
    ```json
    [
      {
        "name": "my_data_tool_agent",
        "mcp_servers": ["my_data_tool_server"],
        "system_prompt": "You are an agent that can use the my_data_tool_server to answer questions."
      }
    ]
    ```

### Step 6: Update Server Documentation

Update the relevant server documentation to include a reference to the new agent.

*   **Action:** Edit the markdown file in `docs/toolbox/servers/`.
*   **Example:**
    ```markdown
    **Relevant Agents:**
    *   **`my_data_tool_agent`**: An agent that can use the my_data_tool_server to answer questions.
        *   **Configuration File**: `config/agents/my_data_tool_agents.json`
    ```

### Step 7: Verify Changes

After adding the new server and its documentation, reinstall the package locally and run `aurite init` to ensure the new files are correctly scaffolded into a new project.

*   **Action:** Run `pip install -e .` and then `aurite init test_project`.
*   **Example:**
    ```bash
    pip install -e .
    cd ..
    aurite init my_test_project
    # Now, inspect my_test_project/config/mcp_servers/ to ensure the new JSON file is present.
