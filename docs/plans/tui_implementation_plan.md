# Implementation Plan: Aurite Textual TUI

**Version:** 1.0
**Date:** 2025-07-04
**Author(s):** Ryan, Gemini
**Related Design Document:** [Aurite Textual TUI Design](docs/design/tui.md)

## 1. Goals

*   To create a functional, interactive Textual TUI for the Aurite framework.
*   To provide a user-friendly interface for listing, inspecting, and running all major Aurite components.
*   To structure the TUI code in a modular and maintainable way.

## 2. Scope

*   **In Scope:**
    *   A new TUI application file (`src/aurite/bin/tui/main.py`).
    *   A new CLI command `aurite tui` to launch the application.
    *   Implementation of all panes described in the design document (Navigation, List, Detail/Action, Output/Log).
    *   Integration with `ConfigManager` to display components.
    *   Integration with `ExecutionFacade` to run components and stream output.
*   **Out of Scope:**
    *   Editing component configurations directly from the TUI. (This can be a future enhancement).
    *   Advanced features like saving/loading TUI state, custom themes, etc.

## 3. Implementation Steps

The implementation is broken down into phases, starting with the core application structure and progressively adding interactive features.

### Phase 1: Core Application Setup

1.  **Step 1.1: Create TUI Application File**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   Create a new directory `src/aurite/bin/tui/` and an empty `__init__.py` file within it.
        *   Create `main.py`.
        *   Define a basic `TextualApp` class (e.g., `AuriteTUI`).
        *   Use the `compose` method to set up the static layout using `Header`, `Footer`, and placeholder `Static` widgets for the four main panes as defined in the design document.
        *   Add basic CSS for the layout grid.
    *   **Verification:** Running `python -m src.aurite.bin.tui.main` should display the static layout with headers, footers, and placeholders.

2.  **Step 1.2: Add `tui` command to CLI**
    *   **File(s):** `src/aurite/bin/cli/main.py`
    *   **Action:**
        *   Import the `AuriteTUI` app from `src.aurite.bin.tui.main`.
        *   Add a new Typer command `@app.command() def tui():`.
        *   Inside this function, instantiate `AuriteTUI` and call `app.run()`.
    *   **Verification:** Running `aurite tui` from the terminal should launch the basic TUI application.

### Phase 2: Displaying Component Information

1.  **Step 2.1: Integrate `ConfigManager` and Populate Navigation Pane**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   In the `AuriteTUI` class, initialize an instance of `Aurite()` in the `on_mount` handler.
        *   Replace the placeholder for the Navigation Pane with a `Tree` widget.
        *   In `on_mount`, after initializing `Aurite`, get the component types from `aurite.config_manager.get_all_configs().keys()`.
        *   Populate the `Tree` with these component types as top-level nodes.
    *   **Verification:** The TUI should launch and display the component types (Agents, LLMs, etc.) in the navigation tree.

2.  **Step 2.2: Populate List Pane based on Navigation**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   Replace the placeholder for the List Pane with a `DataTable` widget.
        *   Implement an `on(Tree.NodeSelected)` message handler.
        *   Inside the handler, get the selected component type, clear the `DataTable`, and use `aurite.config_manager.list_configs()` to fetch the list of components.
        *   Add the components as rows to the `DataTable`.
    *   **Verification:** Clicking a node in the navigation tree should populate the data table with the correct list of components.

3.  **Step 2.3: Populate Detail Pane based on List Selection**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   Replace the placeholder for the Detail/Action pane with a container that includes a `RichLog` or `Static` widget for displaying details.
        *   Implement an `on(DataTable.RowSelected)` message handler.
        *   Inside the handler, get the selected component name, use `aurite.config_manager.get_config()` to fetch its full configuration.
        *   Pretty-print the configuration dictionary (e.g., using `json.dumps` or by iterating) and display it in the detail widget.
    *   **Verification:** Clicking a row in the data table should display the full configuration of that component in the detail pane.

### Phase 3: Component Execution

1.  **Step 3.1: Add Execution Controls to Detail Pane**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   Modify the `on(DataTable.RowSelected)` handler. If the selected component is runnable (agent or workflow), dynamically add an `Input` and a `Button("▶ Run")` to the Detail/Action pane.
    *   **Verification:** When an agent or workflow is selected, the input field and run button should appear. When an LLM or MCP server is selected, they should not.

2.  **Step 3.2: Implement Run Logic**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   Replace the placeholder for the Output/Log pane with a `RichLog` widget.
        *   Implement an `on(Button.Pressed)` message handler.
        *   Inside the handler, identify which button was pressed (the "Run" button).
        *   Retrieve the component type, name, and the user message from the `Input` widget.
        *   Call the appropriate `aurite.execution` method (e.g., `stream_agent_run`) in a non-blocking way using `self.run_worker()`.
        *   Clear the `RichLog` and write a "Running..." message.
    *   **Verification:** Pressing the run button should trigger the execution logic and show a "Running..." message in the log.

3.  **Step 3.3: Stream Execution Output**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   In the worker method that calls `stream_agent_run`, iterate over the async generator.
        *   For each event yielded by the stream, use `self.call_from_thread()` to post a custom message back to the main app thread containing the event data.
        *   Create a message handler for this custom message that writes the formatted event data to the `RichLog`.
    *   **Verification:** Running an agent should display the full, real-time stream of its execution in the output pane, with appropriate color-coding.

## 4. Testing Strategy

*   **Manual Verification:** Each step will be manually verified by running the TUI (`aurite tui`) and checking that the UI behaves as described in the verification criteria for that step.
*   **Component Testing:** The test will use the existing project configuration (`.aurite` pointing to `src/aurite/init_templates`) to ensure the TUI can correctly load and run the example components.
