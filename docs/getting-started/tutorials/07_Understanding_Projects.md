# Module 1: Tutorial - Your First Agent via Configuration Files

**Welcome to your first hands-on experience with the Aurite Agents framework!** In this tutorial, you'll configure, run, and interact with a basic AI agent by directly editing configuration files and running a Python script. This will help solidify the concepts you learned in "What is an AI Agent?" and introduce you to the code-centric way of managing Aurite projects.

**Learning Objectives:**

**Primary Goal: Framework Setup and Initial Agent Execution**

- Successfully install the Aurite framework and its prerequisites, including setting up a Python virtual environment.
- Initialize a new Aurite project and configure your OpenAI API key in a `.env` file.
- Run a pre-configured example agent to verify your setup and ensure the framework is operational.

**Secondary Goal: Understanding and Building Your First Agent via Configuration**

- Grasp the fundamental role of the `aurite_config.json` file in defining agents within an Aurite project.
- Learn to configure a new agent by directly editing the `aurite_config.json` file, utilizing pre-defined LLM and MCP server (client) configurations.
- Understand the purpose and structure of the `run_example_project.py` script for programmatically executing agents.
- Modify the `run_example_project.py` script to execute your custom-configured agent.
- Successfully run your newly configured agent, observe its output, and gain a practical understanding of how a basic AI agent operates within the Aurite framework.

---

## Prerequisites

⚠️ **Before you begin this tutorial, please ensure you have completed all the steps in the [Package Installation Guide](../installation_guides/package_installation_guide.md).**

This includes:

- Installing Python 3.12+
- Setting up your workspace and Python virtual environment.
- Obtaining an OpenAI API key and configuring it in a `.env` file in your workspace root.
- Installing the `aurite` package.
- Initializing your first Aurite project (e.g., `my_first_aurite_project`) using `aurite init`.
- Successfully running the example agent via `python run_example_project.py` from within your project directory.

Once these prerequisites are met, you are ready to proceed with configuring your first custom agent.

### 1. Understanding `aurite_config.json`

The `aurite_config.json` file, located at the root of your project (e.g., `your_project_name/aurite_config.json`), is the central configuration hub for your Aurite project. It defines the agents, LLMs, clients (MCP servers), and workflows that are part of your project.

When you ran `aurite init`, this file was created with some example configurations. We will modify it to define our new weather forecast agent.

- **Open `aurite_config.json` in your text editor.**

You'll see sections for `llms`, `mcp_servers`, and `agents`, among others. For this tutorial, we'll focus on:

- The `llms` array: Lists available Large Language Model configurations.
- The `mcp_servers` array: Lists configurations for MCP servers, which provide tools to your agents. `aurite init` includes an example `weather_server`.
- The `agents` array: This is where we will define our new agent.

_(The `aurite_config.json` file also includes sections for `linear_workflows` and `custom_workflows`. These allow you to define sequences of agents or more complex programmatic workflows, respectively. While not covered in this introductory tutorial, they demonstrate how you can orchestrate multiple components within your Aurite project.)_

### 2. Modifying `aurite_config.json` - Configure Your First Agent

Now, let's configure your "MyCLIWeatherAssistant" agent. The `aurite init` command provides a default `aurite_config.json` which already includes a pre-configured LLM for OpenAI (`my_openai_gpt4_turbo`) and an example `weather_server` client. We will use these existing components for our new agent.

1.  **Add Your New Agent Configuration:**
    - Open your `aurite_config.json` file.
    - Locate the `agents` array.
    - Add the following JSON object as a new element within this `agents` array. Since the default configuration already includes other agents, you'll be adding your "MyCLIWeatherAssistant" alongside them.

- **You will need to add a comma `,` after the closing curly brace `}` of the agent definition that comes before where you paste your new agent's configuration.**

  ```json
  {
    "name": "MyCLIWeatherAssistant",
    "system_prompt": "You are a helpful assistant. Your task is to use the available tools to find and report the weather for the location specified by the user. Only provide the temperature and a brief description of the conditions.",
    "llm_config_id": "my_openai_gpt4_turbo",
    "mcp_servers": ["weather_server"]
  }
  ```

  Let's break down these fields for your new agent:

  | Field             | Description                                                                                                                                                                                                |
  | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | `"name"`          | `"MyCLIWeatherAssistant"`: A unique name for your agent.                                                                                                                                                   |
  | `"system_prompt"` | Instructions defining the agent's role and task. (e.g., "You are a helpful assistant...")                                                                                                                  |
  | `"llm_config_id"` | `"my_openai_gpt4_turbo"`: Tells your agent to use the pre-defined OpenAI GPT-4 Turbo LLM configuration. This `llm_id` is already set up in the `llms` array of your `aurite_config.json` by `aurite init`. |
  | `"mcp_servers"`   | `["weather_server"]`: A list of MCP Server names the agent can use for tools. `"weather_server"` is an example server provided by `aurite init`.                                                           |

1.  **Save `aurite_config.json`**.

### 3. Modifying `run_example_project.py` to Execute Your Agent

The `aurite init` command creates an example script `run_example_project.py` in your project root. This script is pre-configured to run the default "Weather Agent". We only need to make one small change to tell it to run your newly configured "MyCLIWeatherAssistant" instead.

1.  **Open `run_example_project.py` in your text editor.**
    You'll find that the script already contains the necessary logic to initialize Aurite, run an agent, and print its response.

2.  **Update the Agent Name:**

    - Locate the section in the script where the `aurite.run_agent` function is called. It will look similar to this (line numbers may vary slightly):

      ```python
      # ... other code ...

      agent_result = await aurite.run_agent(
          agent_name="My Weather Agent", # <--- CHANGE THIS LINE
          user_message=user_query,
      )

      # ... other code ...
      ```

    - Change the value of the `agent_name` parameter from `"My Weather Agent"` to `"MyCLIWeatherAssistant"` (the name you gave your agent in `aurite_config.json`).
      The line should now look like:
      ```python
      agent_name="MyCLIWeatherAssistant", # Must match the name in aurite_config.json
      ```

3.  **Save `run_example_project.py`**.

That's the only change needed for this script! The rest of the script, including how it sets the `user_query` and prints the `agent_result`, can remain as is for this tutorial.

### 4. Running Your Modified Agent

Now it's time to see your "MyCLIWeatherAssistant" in action!

1.  **Navigate to Your Project Directory:**

    - Ensure your Python virtual environment (from the [Package Installation Guide](../installation_guides/package_installation_guide.md)) is active.
    - In your terminal, make sure you are in the root directory of your Aurite project (e.g., `my_first_aurite_project`).

2.  **Run the Script:**

    - Execute the `run_example_project.py` script (which you modified in Step 5):
      ```bash
      python run_example_project.py
      ```

3.  **Observe the Terminal Output:**

    - You should now see output from your "MyCLIWeatherAssistant" providing a weather report for New York, similar to before but this time executed using your agent's configuration. For example:

      ```
      Running agent 'MyCLIWeatherAssistant' with query: 'What's the weather like in New York?'

      --- Agent Result ---
      Agent's response: The temperature in New York is 22°C with partly cloudy skies.
      ```

      _(The exact weather details will vary. The key is that it's your "MyCLIWeatherAssistant" running.)_

---

## Success Criteria / Verification

You've successfully completed this tutorial if:

- Your `aurite_config.json` file was correctly modified to include the new "MyCLIWeatherAssistant" agent configuration.
- Your `run_example_project.py` script was updated to call your new agent by name.
- Running `python run_example_project.py` in your project's root directory executed without Python errors.
- The terminal output showed a weather forecast for the queried location (e.g., New York), indicating your agent successfully used the LLM and the weather tool.

---

**Congratulations!** You've successfully configured and executed your first AI agent by directly editing configuration files and running a Python script. This demonstrates a powerful way to manage and deploy Aurite agents.

In the next module, you'll dive deeper into how tools work by learning more about the Model Context Protocol (MCP) and potentially building or configuring more complex MCP clients.
