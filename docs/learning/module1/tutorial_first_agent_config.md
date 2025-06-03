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
        (The exact weather details will vary.)
    *   Seeing this output means you're ready to move on to understanding the configuration files and then creating your own agent.

### 2. Understanding `aurite_config.json`

The `aurite_config.json` file, located at the root of your project (e.g., `your_project_name/aurite_config.json`), is the central configuration hub for your Aurite project. It defines the agents, LLMs, clients (MCP servers), and workflows that are part of your project.

When you run `aurite init`, this file is created with some example configurations. We will modify it to define our weather assistant.

*   **Open `aurite_config.json` in your text editor.**

You'll see sections for `llms`, `clients`, and `agents`.
*   The `llms` array lists available Large Language Model configurations.
*   The `clients` array lists configurations for MCP servers, which provide tools to your agents. `aurite init` includes an example `weather_server`.
*   The `agents` array is where we will define our agent.

### 3. Modifying `aurite_config.json` - Your First Agent

Let's configure your "MyCLIWeatherAssistant".

1.  **Add Your New LLM Configuration:**
    Before creating the agent, let's define an LLM configuration that our agent will use.
    *   Navigate to the `llms` array in your `aurite_config.json`.
    *   Add the following JSON object to this array. If the `llms` array already contains configurations, add this as a new element, ensuring correct comma placement.

    ```json
    {
      "llm_id": "my_openai_gpt4_turbo",
      "provider": "openai",
      "model_name": "gpt-4-turbo-preview",
      "temperature": 0.7,
      "max_tokens": 1500,
      "default_system_prompt": "You are a helpful AI assistant.",
      "api_key_env_var": "OPENAI_API_KEY"
    }
    ```
    Let's break down these LLM configuration fields:
    *   `"llm_id": "my_openai_gpt4_turbo"`: A unique identifier for this LLM configuration. We'll use this ID in our agent configuration.
    *   `"provider": "openai"`: Specifies the LLM provider (e.g., "openai", "anthropic").
    *   `"model_name": "gpt-4-turbo-preview"`: The specific model name from the provider.
    *   `"temperature": 0.7`: Controls the randomness of the output. Higher values make the output more random.
    *   `"max_tokens": 1500`: The maximum number of tokens (words/sub-words) the model can generate in a single response.
    *   `"default_system_prompt"`: A general system prompt if the agent doesn't provide a more specific one.
    *   `"api_key_env_var": "OPENAI_API_KEY"`: Specifies the environment variable that holds the API key for this provider. Ensure you have `OPENAI_API_KEY` set in your `.env` file.

2.  **Add Your New Agent Configuration:**
    Now, add the following JSON object to the `agents` array in your `aurite_config.json` file. If the `agents` array was empty after the first step, your new array will look like `[ { ...your agent... } ]`. If other agents exist, add yours as another element in the array, ensuring correct comma placement.

    ```json
    {
      "name": "MyCLIWeatherAssistant",
      "system_prompt": "You are a helpful assistant. Your task is to use the available tools to find and report the weather for the location specified by the user. Only provide the temperature and a brief description of the conditions.",
      "llm_config_id": "my_openai_gpt4_turbo",
      "client_ids": ["weather_server"]
    }
    ```

    Let's break down these fields:
    *   `"name": "MyCLIWeatherAssistant"`: A unique name for your agent.
    *   `"system_prompt"`: Instructions defining the agent's role and task.
    *   `"llm_config_id": "my_openai_gpt4_turbo"`: This tells the agent which LLM configuration to use. **Crucially, this ID must match the `llm_id` of the LLM configuration you just added.**
    *   `"client_ids": ["weather_server"]`: This lists the MCP clients the agent can use for tools. `"weather_server"` is an example client provided by `aurite init` that connects to a simple weather tool. This ID should match a `client_id` in the `clients` array.

3.  **Save `aurite_config.json`**.

### 4. Understanding `run_example_project.py`

The `aurite init` command also creates a Python script named `run_example_project.py` in your project root. This script demonstrates how to programmatically initialize the Aurite framework and execute components like agents or workflows. We will modify this script to run our newly configured `MyCLIWeatherAssistant`.

### 5. Modifying `run_example_project.py` to Execute Your Agent

The `aurite init` command creates an example script `run_example_project.py` in your project root. This script typically demonstrates running a pre-configured example, often a custom workflow. We need to modify it to run our `MyCLIWeatherAssistant` agent instead.

1.  **Open `run_example_project.py` in your text editor.**
    This script contains an example usage of the package. It will show you how to initialize the main `Aurite` class, and how to use it to execute a custom workflow.

2.  **Modify the script to run your agent:**

    *   **Remove or Comment Out Existing Execution Logic:** Delete or comment out the lines that define input for and call `aurite_app.execution.run_custom_workflow` , and the lines that print its result.

    *   **Add Agent Inputs:** Define the `user_query` for your agent and an optional `session_id`:
        ```python
        user_query = "What is the weather in London?" # The question for our agent
        session_id = "cli_tutorial_session_001"    # Optional: for tracking conversation history
        ```

    *   **Call `run_agent`:** Add the line to execute your agent:
        ```python
        agent_result = await aurite_app.execution.run_agent(
            agent_name="MyCLIWeatherAssistant", # Must match the name in aurite_config.json
            user_message=user_query,
            session_id=session_id
        )
        ```

    *   **Add Result Handling for Agent:** Add the logic to parse and print the agent's response:
        ```python
        print("\n--- Agent Result ---")
        if agent_result and "final_response" in agent_result:
            final_response = agent_result.get("final_response", {})
            content_list = final_response.get("content", [{}])
            if content_list and isinstance(content_list, list) and len(content_list) > 0:
                message_text = content_list[0].get("text", "No text in agent's final response.")
                print(f"Agent's response: {message_text}")
            else:
                print("Agent's final response content is empty or not in the expected format.")
        else:
            print("No final_response found in agent_result or agent_result is None.")
            print("Full agent_result for debugging:", agent_result)
        ```

3.  **Your modified `run_example_project.py`** (within the `try` block) should now incorporate these changes. The overall structure of the file (imports, `async def main()`, `if __name__ == "__main__":`, path checking, and the `try/except/finally` block) should remain largely the same. The key is to replace the default execution logic with the agent execution logic.

    Here's how the relevant part of your `main` function should look after modifications:
    ```python
    import asyncio
    import logging
    from aurite import Aurite

    # Configure logging for visibility
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


    async def main():
        aurite = Aurite()

        try:
            await aurite.initialize()
            # logger.info("Aurite initialized successfully.") # If you have logging

            # --- MODIFIED SECTION ---
            user_query = "What is the weather in London?"  # The question for our agent
            session_id = (
                "cli_tutorial_session_001"  # Optional: for tracking conversation history
            )

            print(f"Running agent 'MyCLIWeatherAssistant' with query: '{user_query}'")

            if not aurite.execution:
                print(
                    "Error: Execution facade not initialized. This is unexpected after aurite_app.initialize()."
                )
                return

            agent_result = await aurite.execution.run_agent(
                agent_name="MyCLIWeatherAssistant",
                user_message=user_query,
                session_id=session_id,
            )

            print("\n--- Agent Result ---")
            if agent_result and "final_response" in agent_result:
                final_response = agent_result.get("final_response", {})
                content_list = final_response.get("content", [{}])
                if (
                    content_list
                    and isinstance(content_list, list)
                    and len(content_list) > 0
                ):
                    message_text = content_list[0].get(
                        "text", "No text in agent's final response."
                    )
                    print(f"Agent's response: {message_text}")
                else:
                    print(
                        "Agent's final response content is empty or not in the expected format."
                    )
            else:
                print("No final_response found in agent_result or agent_result is None.")
                print("Full agent_result for debugging:", agent_result)
            # --- END OF MODIFIED SECTION ---

        except Exception as e:
            # logger.error(f"An error occurred: {e}", exc_info=True) # If you have logging
            print(f"An error occurred: {e}")
        finally:
            if aurite.host:
                await aurite.shutdown()



    if __name__ == "__main__":
        asyncio.run(main())

    ```

4.  **Save `run_example_project.py`**.

### 6. Running Your Agent

Now it's time to see your agent in action!

1.  **Open your terminal.**
2.  **Ensure you are in the root directory** of your Aurite project (e.g., `my_first_aurite_project`). This is important so the script can find `aurite_config.json`.
3.  **Ensure your API keys** (e.g., `OPENAI_API_KEY`) are set in your `.env` file in the project root, or exported in your terminal session.
4.  **Run the script:**
    ```bash
    python run_example_project.py
    ```

5.  **Observe the Terminal Output:**
    You should see output similar to this (the exact weather details will vary):

    ```
    Running agent 'MyCLIWeatherAssistant' with query: 'What is the weather in London?'

    --- Agent Result ---
    Agent's response: The temperature in London is 15°C with scattered clouds.
    ```
    *(Note to student: The example `weather_mcp_server` that comes with `aurite init` is a test fixture. It might only support a limited set of locations or return mock data. 'London' is often a reliable choice for testing.)*

---

## Success Criteria / Verification

You've successfully completed this tutorial if:

*   Your `aurite_config.json` file was correctly modified to include your new LLM configuration ("my_openai_gpt4_turbo") and the "MyCLIWeatherAssistant" agent configuration.
*   The "MyCLIWeatherAssistant" agent configuration correctly references your new LLM configuration via `llm_config_id`.
*   Your `run_example_project.py` script was updated as per the instructions.
*   Running `python run_example_project.py` in your project's root directory executed without Python errors.
*   The terminal output showed a weather forecast for the queried location (e.g., London), indicating your agent successfully used the LLM and the weather tool.

---

**Congratulations!** You've successfully configured and executed your first AI agent by directly editing configuration files and running a Python script. This demonstrates a powerful way to manage and deploy Aurite agents.

In the next module, you'll dive deeper into how tools work by learning more about the Model Context Protocol (MCP) and potentially building or configuring more complex MCP clients.
