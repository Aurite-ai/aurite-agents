# Tutorial 7 - Running Agents with the Aurite CLI

Welcome to the next step in your Aurite journey! In the previous tutorials, you learned how to configure agents in JSON files and run them using a Python script. Now, you'll learn a more direct and powerful way to interact with your agents: the **Aurite Command-Line Interface (CLI)**.

The CLI allows you to run any agent defined in your project's configuration without writing or modifying any Python code.

**Learning Objectives:**
*   Understand the purpose of the `aurite run agent` command.
*   Successfully execute a pre-configured agent from the command line.
*   Learn how to pass user messages to an agent via the CLI.
*   Gain confidence in using the CLI as a primary way to test and interact with your agents.

---

## Prerequisites

Before you start, ensure you have:
1.  **Completed Module 1 & the Notebooks:** You should have a project initialized and be familiar with the basic concepts.
2.  **Project Directory:** You should have an Aurite project created (e.g., `my_local_project`).
3.  **Active Virtual Environment:** Make sure you are in your project directory (`cd my_local_project`) and your Python virtual environment is active.
4.  **Environment Variables Set:** Your `.env` file in your workspace root must contain your `OPENAI_API_KEY`.

---

## Tutorial Steps

The `aurite init` command creates a project that is already populated with example configurations. We will use the CLI to run one of these pre-configured agents directly.

### 1. Discovering Available Agents

First, let's see what agents are available in the project. The `aurite run --help` command can show you the available subcommands. To see what agents you can run, you can inspect the `config/agents/agents.json` file.

For a new project, you'll find an agent named `My Weather Agent` is pre-configured to use the local `weather_server`. We will run this agent.

### 2. Running an Agent with the CLI

This is the core of the tutorial. We will use a single command to execute our agent.

1.  **Navigate to Your Project Directory:**
    *   If you're not already there, open a terminal and navigate to your project folder (e.g., `cd my_local_project`).
    *   Ensure your virtual environment is active.

2.  **Execute the Agent:**
    *   Run the following command in your terminal:
        ```bash
        aurite run agent "My Weather Agent" "What is the weather like in San Francisco?"
        ```
    *   **Command Breakdown:**
        *   `aurite run agent`: This is the command to execute a specific agent.
        *   `"My Weather Agent"`: The name of the agent to run. This **must** match the `name` of an agent in your `config/agents/agents.json` file.
        *   `"What is the weather like in San Francisco?"`: This is the user message that gets passed to the agent as the initial input.

3.  **Observe the Output:**
    *   You will see logs in your terminal as the Aurite framework starts up, launches the local `weather_mcp_server.py` script, and runs the agent.
    *   Finally, you will see the agent's response printed directly to the console.

    Example output:
    ```
    INFO:aurite.host.host:Starting local MCP server process for 'weather_server' from path: ...
    INFO:aurite.execution.facade:Running agent 'My Weather Agent'...
    ...
    INFO:root:Agent 'My Weather Agent' finished with response:
    The weather in San Francisco is 18°C with Foggy conditions.
    ```

---

## Success Criteria / Verification

You've successfully completed this tutorial if:

*   The `aurite run agent` command executed without errors.
*   The terminal output shows logs indicating the `weather_server` was started.
*   The command printed a weather forecast for San Francisco, confirming the agent ran, used its local tool, and returned a result.

---

**Congratulations!** You have now mastered a second, more direct way to execute your agents. Using the CLI is an excellent way to quickly test agents, run them in scripts, or integrate them into larger automated systems.

*   **Recap:**
    *   **Tutorial 1:** You learned to **configure** agents and run them via a Python script.
    *   **Tutorial 2:** You learned to **execute** any pre-configured agent directly from the **CLI**.

You are now well-equipped with the foundational skills to build and run your own custom agents and tools.
