# Module 2: Tutorial - Configuring & Running an Agent with a Local MCP Server via CLI

In this tutorial, you'll move beyond the UI and learn how to configure and run an Aurite agent by directly editing the `aurite_config.json` project file and using the command-line interface (CLI). This will give you a deeper understanding of how the framework operates.

**Learning Objectives:**
*   Learn to define a `ClientConfig` for a local MCP server in `aurite_config.json`.
*   Understand how to reference this `ClientConfig` in an `AgentConfig` within the same file.
*   Successfully use the `aurite` CLI commands `start-api` and `run-cli` to execute an agent that uses tools from the configured local MCP server.
*   Gain familiarity with inspecting agent-tool interactions through CLI output.

---

## Prerequisites

Before you start, ensure you have:
1.  **Completed Module 1:** You should understand basic agent concepts and have your Aurite environment set up.
2.  **`aurite` Package Installed & Project Initialized:**
    *   `pip install aurite`
    *   `aurite init my_aurite_cli_project` (or your preferred project name)
    *   `cd my_aurite_cli_project`
3.  **Environment Variables Set:** Your `.env` file in the project root should contain your `API_KEY` and any necessary LLM API keys (e.g., `ANTHROPIC_API_KEY`).
4.  **Basic JSON Understanding:** You'll be editing a JSON file.
5.  **Command-Line Familiarity:** This tutorial heavily uses the terminal.
6.  **Text Editor:** A code editor like VS Code, Sublime Text, or even a simple text editor to modify `aurite_config.json`.

---

## Tutorial Steps

We'll configure an agent to use the local `weather_mcp_server.py` (which should have been created in your project by `aurite init`) and then run it using the CLI.

### 1. Review Your Project Structure

After running `aurite init`, your project directory (`my_aurite_cli_project` or similar) should contain:
*   `aurite_config.json`: The main project configuration file. This is our focus.
*   `mcp_servers/`: A directory containing example MCP server scripts.
    *   `weather_mcp_server.py`: A simple Python script that acts as an MCP server providing weather lookup tools.
*   Other configuration folders (`config/agents/`, `config/llms/`, etc.) and potentially example custom workflow files.

For this tutorial, we will directly edit the main `aurite_config.json` file.

### 2. Configure the Local MCP Server as a Client

1.  **Open `aurite_config.json`:** Open the `aurite_config.json` file located in your project's root directory with your text editor.
    It will look something like this (content may vary slightly):
    ```json
    {
      "project_name": "my_aurite_cli_project",
      "description": "Default Aurite project configuration.",
      "llms": [
        // Default LLM configurations might be here
      ],
      "clients": [
        // Default Client configurations might be here
      ],
      "agents": [
        // Default Agent configurations might be here
      ],
      "simple_workflows": [],
      "custom_workflows": []
    }
    ```

2.  **Add or Modify a `ClientConfig` for the Weather Server:**
    *   Locate the `"clients"` list in the JSON structure.
    *   We need to ensure there's a configuration for our local weather server. If `aurite init` already provided one, you can verify it. If not, or if you want to create a specific one for this tutorial, add the following JSON object to the `"clients"` list. If the list already contains items, remember to add a comma before this new entry if it's not the last one.

    ```json
    {
      "client_id": "local_weather_service_cli",
      "server_path": "mcp_servers/weather_mcp_server.py",
      "capabilities": ["tools"],
      "timeout": 10.0
    }
    ```
    *   **Explanation of fields:**
        *   `client_id`: A unique identifier for this client configuration within your project. We're using `"local_weather_service_cli"` to distinguish it.
        *   `server_path`: The path to the MCP server script, relative to the directory containing `aurite_config.json` (your project root).
        *   `capabilities`: An array indicating what this client provides. For tool servers, it's `["tools"]`.
        *   `timeout`: (Optional) How long (in seconds) the framework should wait for the server to respond.

    *   Your `"clients"` section might now look like this (ensure correct JSON syntax with commas if there are other clients):
    ```json
    "clients": [
      {
        "client_id": "local_weather_service_cli",
        "server_path": "mcp_servers/weather_mcp_server.py",
        "capabilities": ["tools"],
        "timeout": 10.0
      }
      // ... any other client configs
    ],
    ```

### 3. Configure an Agent to Use This Client

Now, let's define an agent that will use the `local_weather_service_cli`.

1.  **Locate the `"agents"` list** in `aurite_config.json`.
2.  **Add an `AgentConfig`:** Add the following JSON object to the `"agents"` list.

    ```json
    {
      "name": "CLIWeatherAgent",
      "system_prompt": "You are an assistant that uses tools to find the weather. Respond with only the weather information.",
      "llm_config_id": "default_anthropic_haiku",
      "client_ids": ["local_weather_service_cli"]
    }
    ```
    *   **Explanation of fields:**
        *   `name`: A unique name for your agent.
        *   `system_prompt`: The instructions for your agent.
        *   `llm_config_id`: The ID of an LLM configuration defined in your `"llms"` list. `aurite init` usually creates a `"default_anthropic_haiku"` or similar. If you don't have this exact ID, check your `"llms"` list and use an available one, or add a default LLM config (see `docs/components/llm.md` or examples from `aurite init`).
        *   `client_ids`: A list of `client_id` strings that this agent can use. Crucially, this includes `"local_weather_service_cli"`.

3.  **Save `aurite_config.json`** after making these changes.

### 4. Run the Agent using the CLI

This is a two-terminal process: one for the API server, one for the CLI client.

1.  **Terminal 1: Start the API Server**
    *   Open a terminal window.
    *   Navigate to your project directory (e.g., `my_aurite_cli_project`).
    *   Run the command:
        ```bash
        start-api
        ```
    *   You should see output indicating the server is starting up (e.g., "Uvicorn running on http://0.0.0.0:8000"). Keep this terminal window open; the API server needs to be running for the CLI to work.

2.  **Terminal 2: Execute the Agent via `run-cli`**
    *   Open a **new, separate** terminal window.
    *   Navigate to the **same** project directory.
    *   Now, run the command to execute your agent. Replace `"CLIWeatherAgent"` with the name you gave your agent if different, and feel free to change the message:
        ```bash
        run-cli execute agent "CLIWeatherAgent" "What's the weather like in London?"
        ```
    *   **Command Breakdown:**
        *   `run-cli`: The Aurite CLI tool.
        *   `execute agent`: Subcommand to execute an agent.
        *   `"CLIWeatherAgent"`: The name of the agent to execute (must match an agent `name` in your `aurite_config.json`).
        *   `"What's the weather like in London?"`: The initial message/input for the agent.

3.  **Observe the Output:**
    *   In Terminal 2 (where you ran `run-cli`), you should see output from the agent. This might include some logging information and then the agent's final response.
    *   In Terminal 1 (where `start-api` is running), you'll likely see log messages indicating API requests, tool calls, etc. This can be useful for debugging.

---

## Success Criteria / Verification

You've successfully completed this tutorial if:

*   The `start-api` command runs without errors and stays running.
*   The `run-cli execute agent ...` command executes in the second terminal and returns a response from the agent.
*   The agent's response indicates it successfully used the `local_weather_service_cli` to get the weather for London. The exact format will depend on your system prompt and the LLM, but it should contain weather information.

Example of expected output in Terminal 2 (may vary):
```
INFO: Sending execution request for agent: CLIWeatherAgent
INFO: Agent execution successful.
INFO: Agent Response:
Weather for London:
Temperature: 15°C
Condition: Rainy
Humidity: 90%
```

---

**Congratulations!** You've successfully configured an agent and its tool client directly in `aurite_config.json` and executed it using the Aurite CLI. This workflow is fundamental for more advanced agent and workflow development.

In the assignment for this module, you'll practice configuring different types of MCP clients.
