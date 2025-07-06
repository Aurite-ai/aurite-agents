# Package Installation Guide

This guide walks you through installing the `aurite` Python package and setting up your first Aurite Agents project. This is the recommended path for users who want to build applications using the Aurite framework without needing to manage the full source code repository.

For instructions on setting up the framework from the main repository (e.g., for development or contribution), please see the [Repository Installation Guide](../repository_installation_guide.md).

## Prerequisites & Setup

Follow these steps to prepare your environment before creating an Aurite project.

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
    *   The example project uses OpenAI, but other tools in the packaged toolbox may require other keys (like `SMITHERY_API_KEY`). The `.env.example` file created by `aurite init` provides a template for all the keys you might need.
    *   **IDE Note:** When you open your workspace folder (e.g., `/path/to/your_workspace/`) in an IDE like VS Code, the IDE will typically load environment variables from a `.env` file found in this workspace root.
    *   **Important Reminder:** After you initialize your project folder using `aurite init` in the "Tutorial Steps", **do not move this `.env` file into the project folder.** It must remain in the main workspace directory (e.g., `/path/to/your_workspace/`) to be correctly loaded by your IDE and Python scripts run from that workspace.

*   At this stage, your workspace might look like this:
```tree
/path/to/your_workspace/
├── .env                      <-- CREATE YOUR .env FILE HERE
└── .venv/                    <-- Your virtual environment
```
With these pre-requisites completed, you are ready to proceed with the tutorial steps below.

## Project Initialization & First Run

With your environment prepared, you can now initialize your Aurite project.

### 1. Initialize Your Project and Run the Example Agent

**➡️ Important: With your workspace, virtual environment, and LLM API key configured as per the "Prerequisites & Setup" steps above, you can now initialize your first Aurite project.**

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
    *   The `aurite init` command creates a script named `run_example_project.py` in your project root (e.g., `my_first_aurite_project/run_example_project.py`). This script is pre-configured to run an example "My Weather Agent".
    *   Since your `OPENAI_API_KEY` is set in the `.env` file in your workspace root (as per the Pre-Requisite Steps), the script should be able to access it.
    *   In your terminal, while inside the project root directory (e.g., `my_first_aurite_project`), run the script:
        ```bash
        python run_example_project.py
        ```
    *   You should see output indicating the "My Weather Agent" is running and then a weather report for New York. This confirms your basic setup and API key are working.
        ```
        Running agent 'My Weather Agent' with query: 'What's the weather like in New York?'

        --- Agent Result ---
        Agent's response: The temperature in New York is 22°C with partly cloudy skies.
        ```
        *(The exact agent response will vary slightly each time you run it. Also, note that this example agent provides its response as a natural language sentence (non-structured output) rather than a fixed data format like JSON.)*
    *   Seeing this output means you're ready to move on to understanding the configuration files and then creating your own agent.
