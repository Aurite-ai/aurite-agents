# Module 1: Tutorial - Your First Agent via the Developer UI

**Welcome to your first hands-on experience with the Aurite Agents framework!** In this tutorial, you'll use the Aurite Developer UI to configure, run, and interact with a basic AI agent. This will help solidify the concepts you learned in "What is an AI Agent?"

**Learning Objectives:**
*   Successfully start the Aurite Agents development UI (`aurite studio`).
*   Navigate the UI to create and configure a new agent.
*   Define an agent's name, system prompt, select an LLM, and assign an MCP client (which provides tools).
*   Execute your configured agent and observe its interaction with a tool.

---

## Prerequisites

Before you begin, please ensure you have the following set up:

1.  **`aurite` Package Installed:**
    *   You should have the `aurite` Python package installed. If not, open your terminal and run:
        ```bash
        pip install aurite
        ```
2.  **Project Initialized:**
    *   You need an Aurite project directory. If you haven't created one, navigate to where you want your project to live and run:
        ```bash
        aurite init my_first_aurite_project
        ```
        (You can replace `my_first_aurite_project` with any name you like).
    *   Then, navigate into your project directory:
        ```bash
        cd my_first_aurite_project
        ```
3.  **Environment Variables:**
    *   Ensure your environment variables are configured as per the main `aurite` package README. This is crucial for the framework to connect to LLM providers and for the backend API to function. Key variables include:
        *   `ANTHROPIC_API_KEY`
        *   `API_KEY` (a secret key you define for securing your Aurite backend API). You'll need to create a `.env` file in your project root (e.g., `my_first_aurite_project/.env`) and add this key, for example:
            ```env
            API_KEY=your_secret_api_key_here
            ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
            ```
---

## Tutorial Steps

Let's build a simple weather assistant!

### 1. Launch the Aurite Development Environment

1.  **Open your terminal.** Make sure you are in the root directory of the project you initialized (e.g., `my_first_aurite_project`).
2.  **Run the `aurite studio` command:**
    ```bash
    aurite studio
    ```
3.  **Observe Terminal Output:** You should see messages indicating that the backend API server has started (likely on a port like `8000`) and the frontend development server has started (often on port `5173`).
    *   `[Screenshot: Terminal output showing 'aurite studio' successfully starting backend and frontend]`
4.  **Open Your Web Browser:** Navigate to the address of the frontend UI, which is typically `http://localhost:5173`.
5.  **API Key Prompt (If Applicable):** The UI might prompt you to enter the `API_KEY` for the Aurite backend. This is the key you set in your `.env` file. Enter it to proceed.
    *   `[Screenshot: UI prompt for API Key, if it exists]`

### 2. Create a Simple Weather Agent via the UI

Now that the UI is open, let's create your agent.

1.  **Navigate to "Build":** In the top navigation bar of the Aurite UI, click on the "Build" section.
    *   `[Screenshot: UI top navigation bar with "Build" highlighted]`
2.  **Select "Agents":** A sidebar or sub-menu should appear. Click on "Agents" to go to the agent configuration area.
    *   `[Screenshot: UI "Build" section sidebar with "Agents" highlighted]`
3.  **Configure Your Agent:** You'll now see a form to define your agent. Fill in the fields as follows:

    *   **Name:** Give your agent a descriptive name.
        *   Example: `MyWeatherAssistant`
        *   `[Screenshot: UI Agent configuration form - "Name" field filled]`

    *   **System Prompt:** This is where you tell the agent its role and task.
        *   Example:
            ```
            You are a helpful assistant. Your task is to use the available tools to find and report the weather for the location specified by the user. Only provide the temperature and a brief description of the conditions.
            ```
        *   `[Screenshot: UI Agent configuration form - "System Prompt" field filled]`

    *   **LLM Configuration:** Select the Large Language Model your agent will use. The `aurite init` command should have set up a default LLM (e.g., using Anthropic's Haiku model if you have an `ANTHROPIC_API_KEY`).
        *   From the "LLM Configuration" dropdown, choose an available LLM.
        *   Example: `default_anthropic_haiku` (or similar based on your setup).
        *   `[Screenshot: UI Agent configuration form - "LLM Configuration" dropdown with selection]`

    *   **Client (Tool) Selection:** Agents use "Clients" to access tools. A client represents a connection to an MCP server that provides these tools. The `aurite init` command should also set up an example weather MCP server.
        *   From the "Clients" or "Tool Sets" dropdown/multi-select, choose the client that provides weather tools: `weather_mcp_server`
        *   `[Screenshot: UI Agent configuration form - "Clients" selection with weather client chosen]`

4.  **Save Your Agent:** Once all fields are filled, click the "Save" or "Create Agent" button.
    *   `[Screenshot: UI Agent configuration form - "Save" button highlighted]`

### 3. Execute Your Agent via the UI

With your "MyWeatherAssistant" configured, it's time to test it!

1.  **Navigate to "Execute":** In the top navigation bar, click on the "Execute" section.
    *   `[Screenshot: UI top navigation bar with "Execute" highlighted]`
2.  **Select "Agents":** In the sidebar or sub-menu that appears, click on "Agents".
    *   `[Screenshot: UI "Execute" section sidebar with "Agents" highlighted]`
3.  **Choose Your Agent:** You should see a list of available agents. Select the agent you just created, "MyWeatherAssistant".
    *   `[Screenshot: UI "Execute Agents" page with "MyWeatherAssistant" selected from a list]`
4.  **Interact with Your Agent:** You should now see a chat interface.
    *   In the chat input field at the bottom, type a message to ask for the weather.
        *   Example: `What is the weather in London?`
        *   *(Note to student: The example `weather_mcp_server` that comes with `aurite init` is a test fixture. It might only support a limited set of locations for testing purposes. 'London' is often a reliable choice.)*
    *   `[Screenshot: UI Chat interface with "What is the weather in London?" typed in input field]`
    *   Click the "Send" button or press Enter.

5.  **Observe the Response:**
    *   Watch the chat interface. The agent should process your request. You might see indicators that it's "thinking" or "using a tool."
    *   After a moment, the agent should respond with the weather information for London.
    *   `[Screenshot: UI Chat interface showing the agent's response with weather for London]`

---

## Success Criteria / Verification

You've successfully completed this tutorial if:

*   The `aurite studio` command launched without errors, and you were able to access the UI.
*   You were able to create and configure "MyWeatherAssistant" through the UI.
*   When you asked "What is the weather in London?", your agent responded with a weather forecast for London (e.g., temperature and conditions).
*   (Optional) If the UI provides logs or indicators of tool use, you might see evidence that the weather tool was called.

---

**Congratulations!** You've built and interacted with your first AI agent using the Aurite Developer UI. You've seen how the system prompt, LLM selection, and tool client come together to create a functional agent.

In the next module, you'll dive deeper into how tools work by learning about the Model Context Protocol (MCP) and configuring MCP clients directly.
