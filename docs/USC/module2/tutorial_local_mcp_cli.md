# Module 2: Tutorial - Configuring & Running an Agent with a Local MCP Server

In the previous tutorials, you learned how to run agents and use pre-packaged, cloud-based tools. In this tutorial, you'll learn how to configure and run an agent that uses a **local MCP server**—a Python script running directly on your machine.

This is a fundamental skill for developing your own custom tools for Aurite agents.

**Learning Objectives:**
*   Understand how local MCP servers are defined in their own configuration files.
*   Learn to configure a new agent in `config/agents/agents.json` to use a local tool server.
*   Modify the `run_example_project.py` script to execute your new agent.
*   Successfully run an agent that uses tools from a local Python script.

---

## Prerequisites

Before you start, ensure you have:
1.  **Completed Module 1 & the Notebooks:** You should be comfortable with the basic concepts of agents, tools, and project configuration.
2.  **`aurite` Package Installed & Project Initialized:**
    *   You should have an Aurite project created (e.g., `aurite init my_local_project`).
    *   You should be able to `cd my_local_project` and have your virtual environment active.
3.  **Environment Variables Set:** Your `.env` file in your workspace root should contain your `OPENAI_API_KEY`.

---

## Tutorial Steps

We will configure an agent to use the `weather_mcp_server.py` script that was created in your project by `aurite init`.

### 1. Review Your Project Structure

After running `aurite init`, your project directory contains a folder named `example_mcp_servers/`. Inside, you'll find `weather_mcp_server.py`. This is a simple Python script that acts as a self-contained MCP server, providing a `weather_lookup` tool.

The framework needs to know how to run this script. This is defined in `config/mcp_servers/example_mcp_servers.json`.

*   **Open `config/mcp_servers/example_mcp_servers.json` in your text editor.**

You will see a configuration object for the `weather_server`.

```json
[
  {
    "name": "weather_server",
    "server_path": "example_mcp_servers/weather_mcp_server.py",
    "capabilities": ["tools"],
    "timeout": 10.0
  }
]
```
*   **Key Fields:**
    *   `name`: A unique name for this server configuration.
    *   `server_path`: The path to the Python script to run, **relative to your project root**. This is how the framework knows which script to execute for the "weather_server".

### 2. Configure an Agent to Use the Local Server

Now, let's create a new agent that is specifically designed to use this local server.

1.  **Open `config/agents/agents.json`:** This file contains a list of all agent configurations for your project.
2.  **Add a New Agent Configuration:** Add the following JSON object to the list in `agents.json`. Remember to add a comma after the preceding agent configuration if necessary to keep the JSON valid.

    ```json
    {
      "name": "LocalWeatherAgent",
      "system_prompt": "You are a helpful assistant that uses local tools to find the weather.",
      "llm_config_id": "my_openai_gpt4_turbo",
      "mcp_servers": ["weather_server"]
    }
    ```
    *   **Explanation:**
        *   `name`: We've given it a unique name, "LocalWeatherAgent".
        *   `llm_config_id`: We're using the default OpenAI LLM config provided by `aurite init`.
        *   `mcp_servers`: This is the crucial part. We've given it `["weather_server"]`, which matches the `name` of the local server we just reviewed in `example_mcp_servers.json`.

3.  **Save `config/agents/agents.json`**.

### 3. Modify `run_example_project.py` to Execute Your New Agent

The `run_example_project.py` script is your entry point for running agents. We'll make a small change to tell it to run our new `LocalWeatherAgent`.

1.  **Open `run_example_project.py` in your text editor.**
2.  **Update the Agent Name:**
    *   Find the line where `aurite.run_agent` is called.
        ```python
        # ...
        agent_result = await aurite.run_agent(
            agent_name="My Weather Agent", # <--- CHANGE THIS LINE
            user_message=user_query,
        )
        # ...
        ```
    *   Change the `agent_name` from `"My Weather Agent"` to `"LocalWeatherAgent"`.
        ```python
        agent_name="LocalWeatherAgent",
        ```
3.  **Save `run_example_project.py`**.

### 4. Run Your Agent

Now you're ready to run the agent.

1.  **Navigate to Your Project Directory** in your terminal (e.g., `cd my_local_project`).
2.  **Run the Script:**
    ```bash
    python run_example_project.py
    ```
3.  **Observe the Output:** You will see logs indicating the framework is starting the `weather_mcp_server.py` script as a subprocess. Then, you'll see the agent's response, which should be a weather report for New York.

    ```
    INFO:aurite.host.host:Starting local MCP server process for 'weather_server' from path: ...
    ...
    --- Agent Result ---
    Agent's response: The weather in New York is 22°C with partly cloudy skies.
    ```

---

## Success Criteria / Verification

You've successfully completed this tutorial if:

*   You correctly added the `LocalWeatherAgent` configuration to `config/agents/agents.json`.
*   You updated `run_example_project.py` to call your new agent.
*   Running the script executed without errors and produced a weather forecast, confirming that the framework successfully ran the local `weather_mcp_server.py` script and the agent used its tool.

---

**Congratulations!** You now understand how to connect an agent to a local tool server. This is the foundation for creating your own custom Python tools to give your agents any capability you can imagine.
