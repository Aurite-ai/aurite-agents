# :material-application-braces-outline: TUI Guide

The Aurite framework includes two powerful Textual User Interfaces (TUIs) to enhance your development experience directly in the terminal: the **Interactive Chat TUI** and the **Configuration Editor TUI**.

---

## TUI Interfaces

=== ":material-chat-processing: Interactive Chat TUI"

    The Chat TUI provides a rich, interactive environment for conversing with your agents, viewing tool calls in real-time, and managing conversation history.

    !!! info "How to Launch"
        The Chat TUI is launched using the `aurite run` command when you specify an agent's name **without** providing a user message.

        ```bash
        # Launch a new chat session with an agent
        aurite run my_chat_agent

        # Continue a previous conversation
        aurite run my_chat_agent --session-id "some-previous-session-id"
        ```

    **Interface Overview:**

    1.  **Header:** Displays the agent name and the current session ID.
    2.  **Agent Info Panel:** Shows key details about the agent (system prompt, LLM, etc.).
    3.  **Chat History:** The main panel displaying the conversation, including user messages, agent responses, and tool calls.
    4.  **User Input:** The text area at the bottom for composing messages.
    5.  **Footer:** Displays key bindings.

    !!! tip "Key Bindings"
        -   **`Ctrl+Enter`**: Send the message to the agent.
        -   **`Ctrl+C`**: Exit the chat application.

=== ":material-file-edit: Configuration Editor TUI"

    The Configuration Editor TUI (`aurite edit`) is a powerful tool for creating, viewing, and modifying all your component configurations without manually editing JSON or YAML files.

    !!! info "How to Launch"
        You can launch the editor in two ways:

        ```bash
        # General Mode: Browse all configurations
        aurite edit

        # Direct Edit Mode: Open a specific component
        aurite edit my_agent
        ```

    **Interface Overview:**

    The editor uses a three-pane layout for efficient navigation:

    1.  **Navigation Tree (Left):** A tree of all component types (`agent`, `llm`, etc.).
    2.  **Component List (Middle):** A table listing all components of the selected type.
    3.  **Configuration Editor (Right):** An interactive form for editing the selected component's fields.

    !!! tip "How to Use"
        1.  **Navigate:** Use arrow keys to move between panes and select items.
        2.  **Edit:** Use `Tab` to move between fields in the editor. Press `Enter` on dropdowns or buttons to open them.
        3.  **Save:** Navigate to the "Save Configuration" button and press `Enter` to write your changes to the file.
        4.  **Exit:** Press `Ctrl+C` to exit the editor.
