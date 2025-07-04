# Aurite Textual TUI Design

**Author(s):** Ryan, Gemini
**Version:** 1.0
**Date:** 2025-07-04

## 1. Overview

This document outlines the design for a Textual-based Terminal User Interface (TUI) for the Aurite framework. The TUI aims to provide an interactive, user-friendly alternative to the command-line interface for managing, viewing, and running Aurite components like Agents and Workflows.

## 2. Core Principles

*   **Intuitive Navigation:** Users should be able to easily discover and inspect all configured components within their project and workspace.
*   **Interactive Execution:** Running agents and workflows should be simple, with clear input mechanisms and real-time feedback.
*   **Framework-Powered:** The TUI will be a frontend layer that leverages the existing, robust logic within the `aurite` package's core classes (`Aurite`, `ConfigManager`, `ExecutionFacade`). It will not reimplement any core framework logic.
*   **Asynchronous:** The TUI will be built on Textual's async capabilities to seamlessly integrate with Aurite's async execution model.

## 3. High-Level Layout

The TUI will use a multi-pane layout to present information clearly and efficiently.

```
+--------------------------------------------------------------------------+
| Header: Aurite TUI - Project: [Project Name]                             |
+----------------------------------+---------------------------------------+
|                                  |                                       |
|         [1] Navigation         |         [3] Detail / Action           |
|         (Tree View)              |         (Static, Input, Button)       |
|                                  |                                       |
|----------------------------------+                                       |
|                                  |                                       |
|         [2] List View            |                                       |
|         (Data Table)             |                                       |
|                                  |                                       |
+----------------------------------+---------------------------------------+
|                                                                          |
|         [4] Output / Log                                                 |
|         (RichLog)                                                        |
|                                                                          |
+--------------------------------------------------------------------------+
| Footer: [Status Messages] [Key Bindings: Ctrl+Q to Quit]                 |
+--------------------------------------------------------------------------+
```

## 4. Pane-by-Pane Breakdown

### 4.1. Navigation Pane (Top-Left)

*   **Widget:** `textual.widgets.Tree`
*   **Functionality:** This pane provides the primary navigation structure. It will be populated by querying the `ConfigManager` for all available component types.
*   **Initial State:** The tree will display top-level nodes for each major component type:
    *   `Agents`
    *   `Simple Workflows`
    *   `Custom Workflows`
    *   `LLMs`
    *   `MCP Servers`
*   **Interaction:** When a user clicks on a node in the tree, a message will be posted to update the **List Pane** with the corresponding components.

### 4.2. List Pane (Bottom-Left)

*   **Widget:** `textual.widgets.DataTable`
*   **Functionality:** This pane lists the specific components of the type selected in the Navigation Pane. It will be populated by calling `ConfigManager.list_configs(<component_type>)`.
*   **Example:** If "Agents" is selected in the Navigation Pane, this table will display all configured agents with relevant columns like "Name", "LLM Config", and "MCP Servers".
*   **Interaction:** When a user selects a row in the table, a message will be posted to update the **Detail / Action Pane** with the full details of the selected component.

### 4.3. Detail / Action Pane (Right)

*   **Widget:** A container holding `textual.widgets.Static`, `textual.widgets.Input`, and `textual.widgets.Button`.
*   **Functionality:** This is a context-sensitive pane that serves two primary purposes:
    1.  **Detail View:** Displays the complete configuration of the component selected in the List Pane. The data will be retrieved from `ConfigManager.get_config(...)` and displayed in a readable, formatted way using `Static` widgets.
    2.  **Action View:** For runnable components (Agents, Workflows), this pane will also include:
        *   An `Input` widget for the user to provide the `user_message` or initial input.
        *   A "▶ Run" `Button` to trigger the execution.
*   **Interaction:** Clicking the "Run" button will capture the input and initiate the execution process via the `ExecutionFacade`.

### 4.4. Output / Log Pane (Bottom)

*   **Widget:** `textual.widgets.RichLog`
*   **Functionality:** This pane provides real-time feedback during component execution.
    *   It will display initial status messages (e.g., "Initializing Aurite...", "Running agent 'Weather Agent'...").
    *   It will subscribe to the `ExecutionFacade.stream_agent_run` async generator to display the live stream of events from the agent's execution, including tool calls, intermediate steps, and the final response.
    *   Output will be color-coded for readability (e.g., green for success, red for errors, yellow for warnings/tool calls).

## 5. Data Flow and Logic

1.  **Initialization:**
    *   The TUI application will start and initialize an instance of the `Aurite` class.
    *   It will use the `aurite.config_manager` to populate the initial state of the Navigation Pane.
2.  **Navigation:**
    *   User selects a component type in the **Navigation Pane**.
    *   The TUI calls `aurite.config_manager.list_configs()` and updates the **List Pane**.
3.  **Inspection:**
    *   User selects a specific component in the **List Pane**.
    *   The TUI calls `aurite.config_manager.get_config()` and updates the **Detail / Action Pane**.
4.  **Execution:**
    *   User enters input and clicks the "Run" button in the **Detail / Action Pane**.
    *   The TUI calls the appropriate method on the `aurite.execution` facade (e.g., `stream_agent_run`).
    *   The TUI awaits results from the async generator and streams them to the **Output / Log Pane**.
5.  **Lifecycle Management:**
    *   The `Aurite` instance will be managed within an `async with` block to ensure its `__aenter__` and `__aexit__` methods are called correctly, guaranteeing proper startup and shutdown of underlying services like MCP servers.
