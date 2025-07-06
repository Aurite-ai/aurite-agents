# Implementation Plan: TUI Interactive Component Editor

**Version:** 1.0
**Date:** 2025-07-04
**Author(s):** Ryan, Gemini
**Related Design Document:** [Aurite Textual TUI Design](docs/design/tui.md)

## 1. Goals

*   To transform the TUI's detail pane from a static JSON viewer into a fully interactive editor for component configurations.
*   To implement a backend method (`upsert_component`) in `ConfigManager` that can safely update a component's configuration in its source file.
*   To provide a seamless user experience for viewing, editing, and saving component settings directly from the TUI.

## 2. Implementation Phases

### Phase 1: Backend Scaffolding & Index Enhancement

1.  **Step 1.1: Enhance Component Index**
    *   **File(s):** `src/aurite/config/config_manager.py`
    *   **Action:** Modify the `_parse_and_index_file` method. In addition to storing the `_origin` directory, also store the absolute path of the source file itself in the component's indexed data (e.g., under the key `_source_file`). This is critical for finding the correct file to write back to.
    *   **Verification:** After a refresh, `get_config` for any component should return a dictionary that includes the `_source_file` key.

2.  **Step 1.2: Scaffold `upsert_component` Method**
    *   **File(s):** `src/aurite/config/config_manager.py`
    *   **Action:** Add a new method `def upsert_component(self, component_type: str, component_name: str, new_config: Dict[str, Any]) -> bool:`. For now, this method will only log the arguments it received and return `True`.
    *   **Verification:** Calling `aurite.config_manager.upsert_component(...)` from the TUI will not error and will produce the expected log message.

### Phase 2: Building the Interactive Editor UI

1.  **Step 2.1: Replace `RichLog` with a `Container`**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:** In the `compose` method, replace the `RichLog` with `id="detail-pane"` with a `VerticalScroll` container.
    *   **Verification:** The top-right pane is now an empty, scrollable container.

2.  **Step 2.2: Dynamically Generate Editor Fields**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   Modify the `on_data_table_row_selected` handler.
        *   It should first clear the `detail-pane` container.
        *   Then, for each key-value pair in the selected component's config, it should mount a `Horizontal` container holding a `Label` (for the key) and an `Input` (for the value) into the `detail-pane`.
        *   Give each `Input` a unique ID based on the key (e.g., `id=f"input-{key}"`).
    *   **Verification:** Selecting a component in the `DataTable` populates the detail pane with a form-like view of its configuration.

3.  **Step 2.3: Add Save Button**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:** After generating the input fields, mount a `Button("Save", variant="success", id="save-button")` at the bottom of the `detail-pane`.
    *   **Verification:** A "Save" button appears below the generated form fields.

### Phase 3: Implementing Save Logic

1.  **Step 3.1: Implement `upsert_component` Backend Logic**
    *   **File(s):** `src/aurite/config/config_manager.py`
    *   **Action:**
        *   Flesh out the `upsert_component` method.
        *   Use the `_source_file` from the component's index entry to locate the file.
        *   Read the entire file content (JSON or YAML).
        *   Iterate through the top-level keys (component types) and the list of components within.
        *   Find the component dictionary that matches the `component_name`.
        *   Update this dictionary with the `new_config` data.
        *   Write the entire modified data structure back to the `_source_file`, overwriting it. Ensure JSON/YAML formatting is preserved.
    *   **Verification:** Manually calling this method with test data correctly modifies the target JSON/YAML file on disk.

2.  **Step 3.2: Connect Save Button to Backend**
    *   **File(s):** `src/aurite/bin/tui/main.py`
    *   **Action:**
        *   Create an `on(Button.Pressed)` handler that specifically checks for `id="save-button"`.
        *   Inside the handler, create an empty dictionary for the `new_config`.
        *   Iterate through all the `Input` widgets within the `detail-pane`.
        *   For each `Input`, extract the key from its ID and its current `value`. Populate the `new_config` dictionary.
        *   Call `self.aurite.config_manager.upsert_component()` with the current component type, name, and the newly constructed `new_config`.
        *   Optionally, display a notification or status message on success/failure.
    *   **Verification:** Editing values in the TUI and clicking "Save" successfully updates the underlying component configuration file. A subsequent selection of the same component shows the saved changes.
