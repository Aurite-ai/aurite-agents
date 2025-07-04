# Implementation Plan: Aurite Textual TUI (v2 - Incremental Layout)

**Version:** 2.0
**Date:** 2025-07-04
**Author(s):** Ryan, Gemini
**Related Design Document:** [Aurite Textual TUI Design](docs/design/tui.md)

## 1. Goals

*   To create a functional and stable Textual TUI for the Aurite framework, with a correct and robust layout.
*   To provide a user-friendly interface for listing, inspecting, and running Aurite components.
*   To build the TUI incrementally, verifying each layout and functional step before proceeding to the next.

## 2. Core Strategy: Incremental Build

This plan abandons the "all-at-once" layout approach. We will build the UI in small, verifiable steps, ensuring the grid layout is correct at each stage before adding complexity. This minimizes debugging and isolates layout issues immediately.

## 3. Implementation Steps

### Phase 1: Foundational Layout & Core Structure

This phase focuses exclusively on getting the 2x2 grid layout correct with simple placeholders.

1.  **Step 1.1: Clean Slate & Basic App**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   Delete all existing content in `main.py`.
        *   Create a minimal `AuriteTUI(App)` class.
        *   Add a `CSS_PATH` attribute.
        *   Add a `compose` method that yields a `Header` and a `Footer`.
    *   **Verification:** Running the app shows only a header and footer.

2.  **Step 1.2: Establish the Main Grid Container**
    *   **File(s):** `src/aurite/bin/tui/main.py`, `src/aurite/bin/tui/main.css`
    *   **Action:**
        *   In `compose`, yield a `Container` with `id="app-grid"` between the `Header` and `Footer`.
        *   In `main.css`, style `#app-grid` with `layout: grid;`, `grid-size: 2 2;`, `grid-gutter: 1;`, and make it take up the remaining space (`width: 100%; height: 1fr;`).
    *   **Verification:** The app runs, but the grid is invisible as it has no content.

3.  **Step 1.3: Add the Navigation Pane (Top-Left)**
    *   **File(s):** `src/aurite/bin/tui/main.py`, `src/aurite/bin/tui/main.css`
    *   **Action:**
        *   Inside the `#app-grid` container in `compose`, yield a `Static` widget with `id="nav-pane"`.
        *   In `main.css`, style `#nav-pane` with a border and background color. Set its `row-span: 2;` to make it occupy the entire left column.
    *   **Verification:** The app displays a single pane on the left, spanning the full height between the header and footer.

4.  **Step 1.4: Add the Detail and Output Panes (Right Column)**
    *   **File(s):** `src/aurite/bin/tui/main.py`, `src/aurite/bin/tui/main.css`
    *   **Action:**
        *   In `compose`, after the `#nav-pane`, yield two more `Static` widgets: `#detail-pane` (top-right) and `#output-pane` (bottom-right).
        *   In `main.css`, give them distinct borders/backgrounds. They should automatically fill the second column.
    *   **Verification:** The app now shows a 2x1 layout: a tall left pane and two stacked panes on the right. This is still not the final layout, but it's a key intermediate step.

5.  **Step 1.5: Finalize the 2x2 Grid Layout**
    *   **File(s):** `src/aurite/bin/tui/main.py`, `src/aurite/bin/tui/main.css`
    *   **Action:**
        *   Modify the `compose` method. The first widget in the grid should be for the top-left (`#nav-pane`), the second for the top-right (`#detail-pane`), the third for the bottom-left (`#list-pane`), and the fourth for the bottom-right (`#output-pane`).
        *   Remove the `row-span: 2;` from `#nav-pane`.
        *   Create a new `Static` widget with `id="list-pane"` and place it correctly in the `compose` order.
        *   Adjust CSS to have four distinct panes.
    *   **Verification:** The app now displays a stable 2x2 grid of four placeholder panes. **This is the critical milestone for this phase.**

### Phase 2: Widget Integration

Now, we replace the `Static` placeholders with the real, functional widgets.

1.  **Step 2.1: Integrate Navigation `Tree`**
    *   **Action:** Replace the `#nav-pane` `Static` widget with a `Tree` widget. Populate it with static, dummy data for now.
    *   **Verification:** The top-left pane contains a `Tree` widget, and the layout remains a stable 2x2 grid.

2.  **Step 2.2: Integrate List `DataTable`**
    *   **Action:** Replace the `#list-pane` `Static` widget with a `DataTable`. Add dummy columns and rows.
    *   **Verification:** The bottom-left pane contains a `DataTable`, and the layout remains stable.

3.  **Step 2.3: Integrate Detail `RichLog`**
    *   **Action:** Replace the `#detail-pane` `Static` widget with a `RichLog`.
    *   **Verification:** The top-right pane contains a `RichLog`, and the layout remains stable.

4.  **Step 2.4: Integrate Output `RichLog` and Controls**
    *   **Action:** Replace the `#output-pane` `Static` widget with a `Container` holding an `Input` and a `Button`, and below them, a `RichLog`.
    *   **Verification:** The bottom-right pane contains the specified controls, and the layout remains stable.

### Phase 3: Backend Integration & Interactivity

This phase mirrors the logic from the original plan, but is built upon a now-stable layout.

1.  **Step 3.1: Connect `ConfigManager` to Navigation `Tree`**
    *   **Action:** In `on_mount`, initialize `Aurite()` and populate the `Tree` with actual component types from `config_manager`.
    *   **Verification:** The navigation tree shows the real component types from the project.

2.  **Step 3.2: Connect `Tree` to `DataTable`**
    *   **Action:** Implement `on(Tree.NodeSelected)` to populate the `DataTable` with the list of components for the selected type.
    *   **Verification:** Clicking a tree node populates the `DataTable`.

3.  **Step 3.3: Connect `DataTable` to Detail Pane**
    *   **Action:** Implement `on(DataTable.RowSelected)` to display the selected component's configuration in the detail `RichLog`.
    *   **Verification:** Clicking a table row shows the component's JSON config.

4.  **Step 3.4: Implement Execution Logic**
    *   **Action:** Implement `on(Button.Pressed)` to trigger `execution.stream_agent_run` (or similar) using `run_worker`. Stream the results back to the output `RichLog` using `call_from_thread`.
    *   **Verification:** Entering a message and clicking "Run" executes the selected agent/workflow, and the output streams into the bottom-right pane.

## 4. Testing Strategy

*   **Incremental Manual Verification:** Each step in Phase 1 and 2 MUST be manually run and visually confirmed to work as described before proceeding.
*   **Functional Testing:** Phase 3 will be tested by running the TUI and interacting with the example project components to ensure they load and run correctly.
