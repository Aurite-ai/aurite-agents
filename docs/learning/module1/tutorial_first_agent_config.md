# Module 1: Tutorial - Your First Agent via Configuration Files

**Welcome to your first hands-on experience with the Aurite Agents framework!** In this tutorial, you'll configure, run, and interact with a basic AI agent by directly editing configuration files and running a Python script. This will help solidify the concepts you learned in "What is an AI Agent?" and introduce you to the code-centric way of managing Aurite projects.

**Learning Objectives:**

**Primary Goal: Framework Setup and Initial Agent Execution**
*   Successfully install the Aurite framework and its prerequisites, including setting up a Python virtual environment.
*   Initialize a new Aurite project and configure your OpenAI API key in a `.env` file.
*   Run a pre-configured example agent to verify your setup and ensure the framework is operational.

**Secondary Goal: Understanding and Building Your First Agent via Configuration**
*   Grasp the fundamental role of the `aurite_config.json` file in defining agents within an Aurite project.
*   Learn to configure a new agent by directly editing the `aurite_config.json` file, utilizing pre-defined LLM and MCP server (client) configurations.
*   Understand the purpose and structure of the `run_example_project.py` script for programmatically executing agents.
*   Modify the `run_example_project.py` script to execute your custom-configured agent.
*   Successfully run your newly configured agent, observe its output, and gain a practical understanding of how a basic AI agent operates within the Aurite framework.

---

## Pre-Requisite Steps

Before you begin the tutorial, please complete the following pre-requisite steps to set up your development workspace:

1.  **Python Version Check (>= 3.12):**
    *   The Aurite framework requires Python version 3.12 or higher.
    *   To check your Python version, open your terminal or command prompt and run:
        ```bash
        python --version
        ```
        or
        ```bash
        python3 --version
        ```
    *   If your Python version is less than 3.12, please upgrade your Python installation before proceeding. You can download the latest version from [https://www.python.org/downloads/](https://www.python.org/downloads/). If you are having trouble with your Python installation or upgrade, see this guide: [https://realpython.com/installing-python/](https://realpython.com/installing-python/).

2.  **Prepare Your Workspace and Activate a Python Virtual Environment:**
    *   First, decide on a directory on your computer where you want to create your Aurite projects. This will be your main workspace folder. Let's refer to this as `/path/to/your_workspace/`.
    *   Open your terminal or command prompt and navigate into this chosen workspace directory:
        ```bash
        cd /path/to/your_workspace/
        ```
    *   It's highly recommended to work within a Python virtual environment. Create one within your workspace (e.g., named `.venv`):
        ```bash
        python -m venv .venv
        ```
        (On some systems, you might need to use `python3` instead of `python`)
    *   Activate the virtual environment:
        *   **Windows (Command Prompt):**
            ```bash
            .venv\Scripts\activate
            ```
        *   **Windows (PowerShell):**
            ```bash
            .venv\Scripts\Activate.ps1
            ```
        *   **macOS/Linux (bash/zsh):**
            ```bash
            source .venv/bin/activate
            ```
    *   Your terminal prompt should now indicate that the virtual environment is active. All subsequent Python and `pip` commands in this terminal session will use this environment.
    *   If you are having trouble creating or activating your virtual environment, see the official documentation [https://docs.python.org/3/library/venv.html](https://docs.python.org/3/library/venv.html) or this tutorial: [https://realpython.com/python-virtual-environments-a-primer/](https://realpython.com/python-virtual-environments-a-primer/).

3.  **Obtain an OpenAI API Key:**
    *   This tutorial uses an OpenAI model (GPT-4 Turbo). To interact with it, you'll need an API key from OpenAI.
    *   Navigate to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) to create or retrieve your API key.
    *   **Important:** Copy your new key immediately if you create one and store it in a safe, private place. You may not be able to see it again after closing the creation dialog.
    *   If you are having trouble obtaining or accessing your API key, see this tutorial for guidance: [https://dataaspirant.com/access-openai-api-keys/](https://dataaspirant.com/access-openai-api-keys/)
    *   **Note on Costs:** Be aware that using the OpenAI API incurs costs based on your usage. Monitor your usage and set spending limits if necessary through your OpenAI account dashboard.

4.  **Configure Your OpenAI API Key in a `.env` file:**
    *   In your workspace directory (`/path/to/your_workspace/`), create the `.env` file.
    *   Add your OpenAI API key to this `.env` file in the following format:
        ```env
        OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        ```
    *   Replace `sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` with your actual API key.
    *   **IDE Note:** When you open your workspace folder (e.g., `/path/to/your_workspace/`) in an IDE like VS Code, the IDE will typically load environment variables from a `.env` file found in this workspace root.
    *   **Important Reminder:** After you initialize your project folder using `aurite init` in the "Tutorial Steps", **do not move this `.env` file into the project folder.** It must remain in the main workspace directory to be correctly loaded.

*   At this stage, your workspace might look like this:
```tree
/path/to/your_workspace/
├── .env                      <-- CREATE YOUR .env FILE HERE
└── .venv/                    <-- Your virtual environment
```
With these pre-requisites completed, you are ready to proceed with the tutorial steps below.

## Tutorial Steps

Let's build a simple weather assistant by configuring it directly!

### 1. Initialize Your Project and Run the Example Agent

**➡️ Important: With your workspace, virtual environment, and OpenAI API key configured as per the "Pre-Requisite Steps" above, you can now initialize your first Aurite project.**

1.  **`aurite` Package Installed:**
    *   Ensure your virtual environment (created in the Pre-Requisite Steps) is active.
    *   Install the `aurite` Python package:
        ```bash
        pip install aurite
        ```
2.  **Project Initialized:**
    *   Make sure you are in your main workspace directory (e.g., `/path/to/your_workspace/`) in your terminal.
    *   Create your new project folder. This command will create a new directory named `my_first_aurite_project` (or your chosen name) inside your current workspace directory.
        ```bash
        aurite init my_first_aurite_project
        ```
        (You can replace `my_first_aurite_project` with any name you like).
    *   Then, navigate into your newly created project directory:
        ```bash
        cd my_first_aurite_project
        ```
3.  **Run the Example Agent:**
    *   The `aurite init` command creates a script named `run_example_project.py` in your project root (e.g., `my_first_aurite_project/run_example_project.py`). This script is pre-configured to run an example "Weather Agent".
    *   Since your `OPENAI_API_KEY` is set in the `.env` file in your workspace root (as per the Pre-Requisite Steps), the script should be able to access it.
    *   In your terminal, while inside the project root directory (e.g., `my_first_aurite_project`), run the script:
        ```bash
        python run_example_project.py
        ```
    *   You should see output indicating the "Weather Agent" is running and then a weather report for London. This confirms your basic setup and API key are working.
        ```
        Running agent 'Weather Agent' with query: 'What is the weather in London?'

        --- Agent Result ---
        Agent's response: The temperature in London is XX°C with [description].
        ```
        *(The exact agent response will vary slightly each time you run it. Also, note that this example agent provides its response as a natural language sentence (non-structured output) rather than a fixed data format like JSON.)*
    *   Seeing this output means you're ready to move on to understanding the configuration files and then creating your own agent.

### 2. Understanding `aurite_config.json`

The `aurite_config.json` file, located at the root of your project (e.g., `your_project_name/aurite_config.json`), is the central configuration hub for your Aurite project. It defines the agents, LLMs, clients (MCP servers), and workflows that are part of your project.

When you run `aurite init`, this file is created with some example configurations. We will modify it to define our weather assistant.

*   **Open `aurite_config.json` in your text editor.**

You'll see sections for `llms`, `clients`, and `agents`, among others. For this tutorial, we'll focus on:
*   The `llms` array: Lists available Large Language Model configurations.
*   The `clients` array: Lists configurations for MCP servers, which provide tools to your agents. `aurite init` includes an example `weather_server`.
*   The `agents` array: This is where we will define our new agent.

*(The `aurite_config.json` file also includes sections for `simple_workflows` and `custom_workflows`. These allow you to define sequences of agents or more complex programmatic workflows, respectively. While not covered in this introductory tutorial, they demonstrate how you can orchestrate multiple components within your Aurite project.)*

### 3. Modifying `aurite_config.json` - Configure Your First Agent

Now, let's configure your "MyCLIWeatherAssistant" agent. The `aurite init` command provides a default `aurite_config.json` which already includes a pre-configured LLM for OpenAI (`my_openai_gpt4_turbo`) and an example `weather_server` client. We will use these existing components for our new agent.

1.  **Add Your New Agent Configuration:**
    *   Open your `aurite_config.json` file.
    *   Locate the `agents` array.
    *   Add the following JSON object as a new element within this `agents` array. Since the default configuration already includes other agents (like "Weather Agent" and "Weather Planning Workflow Step 2"), you'll be adding your "MyCLIWeatherAssistant" alongside them. **You will need to add a comma `,` after the closing curly brace `}` of the agent definition that comes before where you paste your new agent's configuration.**

    ```json
    {
      "name": "MyCLIWeatherAssistant",
      "system_prompt": "You are a helpful assistant. Your task is to use the available tools to find and report the weather for the location specified by the user. Only provide the temperature and a brief description of the conditions.",
      "llm_config_id": "my_openai_gpt4_turbo",
      "client_ids": ["weather_server"]
    }
    ```

    Let's break down these fields for your new agent:

    | Field             | Description                                                                                                                                                                                             |
    |-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | `"name"`          | `"MyCLIWeatherAssistant"`: A unique name for your agent.                                                                                                                                                |
    | `"system_prompt"` | Instructions defining the agent's role and task. (e.g., "You are a helpful assistant...")                                                                                                               |
    | `"llm_config_id"` | `"my_openai_gpt4_turbo"`: Tells your agent to use the pre-defined OpenAI GPT-4 Turbo LLM configuration. This `llm_id` is already set up in the `llms` array of your `aurite_config.json` by `aurite init`. |
    | `"client_ids"`    | `["weather_server"]`: A list of MCP client IDs the agent can use for tools. `"weather_server"` is an example client provided by `aurite init`.                                                          |

2.  **Save `aurite_config.json`**.

### 4. Understanding `run_example_project.py`

The `aurite init` command also creates a Python script named `run_example_project.py` in your project root. This script demonstrates how to programmatically initialize the Aurite framework and execute components like agents or workflows. We will modify this script to run our newly configured `MyCLIWeatherAssistant`.

### 5. Modifying `run_example_project.py` to Execute Your Agent

The `aurite init` command creates an example script `run_example_project.py` in your project root. This script is pre-configured to run the default "Weather Agent". We only need to make one small change to tell it to run your newly configured "MyCLIWeatherAssistant" instead.

1.  **Open `run_example_project.py` in your text editor.**
    You'll find that the script already contains the necessary logic to initialize Aurite, run an agent, and print its response.

2.  **Update the Agent Name:**
    *   Locate the section in the script where the `aurite.execution.run_agent` function is called. It will look similar to this (line numbers may vary slightly):
        ```python
        # ... other code ...

        agent_result = await aurite.execution.run_agent(
            agent_name="Weather Agent", # <--- CHANGE THIS LINE
            user_message=user_query,
            session_id=session_id,
        )

        # ... other code ...
        ```
    *   Change the value of the `agent_name` parameter from `"Weather Agent"` to `"MyCLIWeatherAssistant"` (the name you gave your agent in `aurite_config.json`).
        The line should now look like:
        ```python
        agent_name="MyCLIWeatherAssistant", # Must match the name in aurite_config.json
        ```

3.  **Save `run_example_project.py`**.

That's the only change needed for this script! The rest of the script, including how it sets the `user_query` and prints the `agent_result`, can remain as is for this tutorial.

### 6. Running Your Modified Agent

Now it's time to see your "MyCLIWeatherAssistant" in action!

1.  **Ensure Prerequisites for Running:**
    *   Make sure your Python virtual environment is active in your terminal.
    *   Confirm you are in the root directory of your Aurite project (e.g., `my_first_aurite_project`).
    *   Double-check that your `OPENAI_API_KEY` is correctly set up in the `.env` file in your main workspace directory.
    *   *(These are the same conditions required when you first ran the example agent in "Tutorial Step 1.3".)*

2.  **Run the Script:**
    *   Execute the `run_example_project.py` script (which you modified in Step 5):
        ```bash
        python run_example_project.py
        ```

3.  **Observe the Terminal Output:**
    *   You should now see output from your "MyCLIWeatherAssistant" providing a weather report for London, similar to before but this time executed using your agent's configuration. For example:
        ```
        Running agent 'MyCLIWeatherAssistant' with query: 'What is the weather in London?'

        --- Agent Result ---
        Agent's response: The temperature in London is 15°C with scattered clouds.
        ```
        *(The exact weather details will vary. The key is that it's your "MyCLIWeatherAssistant" running.)*

---

## Success Criteria / Verification

You've successfully completed this tutorial if:

*   Your `aurite_config.json` file was correctly modified to include the new "MyCLIWeatherAssistant" agent configuration, which successfully utilizes the pre-defined "my_openai_gpt4_turbo" LLM configuration.
*   The "MyCLIWeatherAssistant" agent configuration correctly references your new LLM configuration via `llm_config_id`.
*   Your `run_example_project.py` script was updated as per the instructions.
*   Running `python run_example_project.py` in your project's root directory executed without Python errors.
*   The terminal output showed a weather forecast for the queried location (e.g., London), indicating your agent successfully used the LLM and the weather tool.

---

**Congratulations!** You've successfully configured and executed your first AI agent by directly editing configuration files and running a Python script. This demonstrates a powerful way to manage and deploy Aurite agents.

In the next module, you'll dive deeper into how tools work by learning more about the Model Context Protocol (MCP) and potentially building or configuring more complex MCP clients.
