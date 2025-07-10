# Aurite TUI Guide

The Aurite framework includes two powerful Textual User Interfaces (TUIs) to enhance your development experience directly in the terminal: the **Interactive Chat TUI** and the **Configuration Editor TUI**.

This guide provides a detailed overview of how to launch and use both interfaces.

---

## 1. Interactive Chat TUI

The Chat TUI provides a rich, interactive environment for conversing with your agents, viewing tool calls in real-time, and managing conversation history.

### Launching the Chat TUI

The Chat TUI is launched using the `aurite run` command when you specify an agent's name **without** providing a user message.

**Usage:**

```bash
aurite run <agent_name>
```

**Example:**

```bash
aurite run my_chat_agent
```

You can also specify a session ID to continue a previous conversation:

```bash
aurite run my_chat_agent --session-id "some-previous-session-id"
```

### Interface Overview

The chat interface is composed of several key areas:

1.  **Header:** Displays the application title, including the agent name and the current session ID.
2.  **Agent Info Panel:** A box at the top showing key details about the currently running agent, such as its system prompt, configured LLM, associated MCP servers, and source file path.
3.  **Chat History:** The main area of the screen where the conversation is displayed. It shows user messages, agent responses, tool calls, and tool outputs in distinct, formatted blocks.
4.  **User Input:** A text area at the bottom where you can compose your messages to the agent.
5.  **Footer:** Displays key bindings, such as `Ctrl+Enter` to send a message.

### How to Use

-   **Sending a Message:** Type your message in the input area at the bottom and press **`Ctrl+Enter`** to send it to the agent.
-   **Viewing Responses:** The agent's response will be streamed into the chat history in real-time. If the agent uses tools, you will see messages indicating the tool call and its result.
-   **Scrolling:** You can scroll through the chat history using your mouse or keyboard arrow keys.
-   **Exiting:** Press **`Ctrl+C`** to exit the chat application.

---

## 2. Configuration Editor TUI

The Configuration Editor TUI (`aurite edit`) is a powerful tool for creating, viewing, and modifying all your component configurations without having to manually edit JSON or YAML files.

### Launching the Editor TUI

You can launch the editor in two ways:

1.  **General Mode:** To open the editor and browse all configurations.
    ```bash
    aurite edit
    ```
2.  **Direct Edit Mode:** To open the editor and jump directly to a specific component.
    ```bash
    aurite edit <component_name>
    ```

### Interface Overview

The editor uses a three-pane layout for efficient navigation and editing:

1.  **Navigation Tree (Left):** This pane displays a tree of all available component types (e.g., `agent`, `llm`, `mcp_server`). Select a type here to see its components.
2.  **Component List (Middle):** This data table lists all the components for the type you selected in the navigation tree. It shows the component's name and a brief description.
3.  **Configuration Editor (Right):** This is where the editing happens. After selecting a component from the list, its configuration fields appear here. The editor uses different widgets (text inputs, dropdowns, text areas) depending on the data type of each field.

### How to Use

1.  **Select a Component Type:** Use the arrow keys to navigate the **Navigation Tree** on the left and press `Enter` to select a type.
2.  **Select a Component:** The **Component List** in the middle will populate. Use the arrow keys to select the component you wish to edit.
3.  **Edit the Configuration:** The **Configuration Editor** on the right will show all the fields for the selected component.
    -   Use `Tab` and `Shift+Tab` to move between fields.
    -   For simple text fields, just type your changes.
    -   For dropdowns (like `llm_config_id`), press `Enter` to open the options and select one.
    -   For special fields like `mcp_servers`, an "Edit" button will appear, opening a modal window for easier selection.
4.  **Save Your Changes:** Once you are done editing, navigate to the **"Save Configuration"** button at the bottom of the editor pane and press `Enter`. This will write your changes back to the original configuration file.
5.  **Exiting:** Press **`Ctrl+C`** to exit the editor.
