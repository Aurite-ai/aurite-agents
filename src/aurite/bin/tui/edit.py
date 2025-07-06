import json
import logging
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.logging import TextualHandler
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    TextArea,
    Tree,
)

from aurite import Aurite

# This MUST be at the top of the file, before other imports,
# to ensure it runs before the aurite framework configures logging.
logging.basicConfig(
    level="INFO",
    handlers=[TextualHandler()],
)


class MCPServersEditorScreen(ModalScreen):
    """A modal screen for selecting MCP servers."""

    def __init__(self, all_servers: list[str], selected_servers: list[str]) -> None:
        self.all_servers = all_servers
        self.selected_servers = selected_servers
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="mcp-editor-container"):
            with VerticalScroll():
                for server_name in self.all_servers:
                    yield Checkbox(
                        server_name,
                        value=server_name in self.selected_servers,
                        id=f"mcp-checkbox-{server_name}",
                    )
            with Horizontal(id="mcp-editor-buttons"):
                yield Button("Save & Close", variant="primary", id="save-mcp")
                yield Button("Cancel", id="cancel-mcp")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-mcp":
            selected = []
            for checkbox in self.query(Checkbox):
                if checkbox.value:
                    selected.append(str(checkbox.label))
            self.dismiss((True, selected))
        elif event.button.id == "cancel-mcp":
            self.dismiss((False, None))


class SystemPromptEditorScreen(ModalScreen):
    """A modal screen for editing the system prompt."""

    def __init__(self, prompt_text: str) -> None:
        self.prompt_text = prompt_text
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="prompt-editor-container"):
            yield TextArea(self.prompt_text, language="markdown", id="prompt-editor")
            with Horizontal(id="prompt-editor-buttons"):
                yield Button("Save & Close", variant="primary", id="save-prompt")
                yield Button("Cancel", id="cancel-prompt")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-prompt":
            editor = self.query_one("#prompt-editor", TextArea)
            self.dismiss((True, editor.text))
        elif event.button.id == "cancel-prompt":
            self.dismiss((False, None))


class AuriteEditTUI(App):
    """A Textual user interface for editing Aurite configurations."""

    CSS_PATH = "edit.tcss"

    def __init__(self, component_name: str | None = None):
        super().__init__()
        self.aurite = Aurite()
        self.current_component_type: str | None = None
        self.current_component_name: str | None = None
        self.target_component_name = component_name
        self.target_component_type: str | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container():
            with Vertical(id="left-pane"):
                yield Tree("Components", id="nav-pane")
                yield DataTable(id="config-list-pane")
            # Right pane now takes full remaining width for configuration data editing
            yield VerticalScroll(id="config-data-pane")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        tree = self.query_one(Tree)
        tree.root.expand()

        # Populate the navigation tree
        component_types = self.aurite.kernel.config_manager.get_all_configs().keys()
        for component_type in component_types:
            tree.root.add(component_type)

        table = self.query_one("#config-list-pane", DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "Description")
        # Initially populate with a default or empty state
        table.clear()

        # If a target component name was provided, find and select it
        if self.target_component_name:
            self._find_and_select_component()

    def _find_and_select_component(self) -> None:
        """Find the component type for the target component name and auto-select it."""
        if not self.target_component_name:
            return

        # Search through all component types to find the target component
        all_configs = self.aurite.kernel.config_manager.get_all_configs()

        for component_type, configs in all_configs.items():
            if isinstance(configs, dict):
                # configs is a dict where keys are component names
                if self.target_component_name in configs:
                    self.target_component_type = component_type
                    break

        if not self.target_component_type:
            self.notify(f"Component '{self.target_component_name}' not found.", severity="warning")
            return

        # Auto-select the component type in the tree
        tree = self.query_one(Tree)
        for node in tree.root.children:
            if str(node.label) == self.target_component_type:
                tree.select_node(node)
                break

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Called when a node in the tree is selected."""
        table = self.query_one("#config-list-pane", DataTable)
        table.clear()

        self.current_component_type = str(event.node.label)
        configs = self.aurite.kernel.config_manager.list_configs(self.current_component_type)

        for config in configs:
            # A simple description, can be improved
            description = config.get("description", "No description")
            table.add_row(config["name"], description)

        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Called when a row in the data table is selected."""
        if self.current_component_type is None:
            return

        config_data_pane = self.query_one("#config-data-pane", VerticalScroll)
        config_data_pane.remove_children()

        row_key = event.row_key
        if row_key is not None:
            self.current_component_name = event.data_table.get_row(row_key)[0]
            if self.current_component_name:
                config = self.aurite.kernel.config_manager.get_config(
                    self.current_component_type, self.current_component_name
                )
                if config:
                    widgets_to_mount = []

                    # Process fields in a specific order for better UX
                    field_order = [
                        "name",
                        "description",
                        "system_prompt",
                        "include_history",
                        "llm_config_id",
                        "mcp_servers",
                    ]
                    other_fields = [
                        k for k in config.keys() if not k.startswith("_") and k not in field_order and k != "type"
                    ]
                    all_fields = field_order + other_fields

                    for key in all_fields:
                        if key not in config or key.startswith("_") or key == "type":
                            continue

                        value = config[key]
                        display_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)

                        # Add descriptive label
                        if key == "name":
                            widgets_to_mount.append(Label("Component Name:", classes="field-label"))
                        elif key == "description":
                            widgets_to_mount.append(Label("Description:", classes="field-label"))
                        elif key == "system_prompt":
                            widgets_to_mount.append(Label("System Prompt:", classes="field-label"))
                        elif key == "include_history":
                            widgets_to_mount.append(Label("Include History:", classes="field-label"))
                        elif key == "llm_config_id":
                            widgets_to_mount.append(Label("LLM Configuration:", classes="field-label"))
                        elif key == "mcp_servers":
                            widgets_to_mount.append(Label("MCP Servers:", classes="field-label"))
                        else:
                            widgets_to_mount.append(Label(f"{key.replace('_', ' ').title()}:", classes="field-label"))

                        # Add appropriate widget based on field type
                        if key == "name":
                            widget = Input(value=display_value, id=f"input-{key}", classes="field-input")
                            widgets_to_mount.append(widget)

                        elif key == "description":
                            widget = TextArea(
                                text=display_value,
                                id=f"textarea-{key}",
                                classes="field-textarea field-textarea-small",
                                soft_wrap=True,
                            )
                            widgets_to_mount.append(widget)

                        elif key == "system_prompt":
                            widget = TextArea(
                                text=display_value,
                                id=f"textarea-{key}",
                                classes="field-textarea field-textarea-large",
                                soft_wrap=True,
                            )
                            widgets_to_mount.append(widget)

                        elif key == "include_history":
                            # Convert string values to boolean for dropdown
                            bool_value = str(value).lower() in ("true", "1", "yes", "on")
                            select_options = [("True", "True"), ("False", "False")]
                            current_value = "True" if bool_value else "False"

                            widget = Select(
                                options=select_options,
                                value=current_value,
                                allow_blank=False,
                                id=f"select-{key}",
                                classes="field-select",
                            )
                            widgets_to_mount.append(widget)

                        elif key == "llm_config_id":
                            llm_configs = self.aurite.kernel.config_manager.list_configs("llm")
                            llm_names = [c["name"] for c in llm_configs]
                            select_options = [(name, name) for name in llm_names]
                            # Add current value if not in list
                            if display_value not in llm_names:
                                select_options.insert(0, (display_value, display_value))

                            widget = Select(
                                options=select_options,
                                value=display_value,
                                allow_blank=False,
                                id=f"select-{key}",
                                classes="field-select",
                            )
                            widgets_to_mount.append(widget)

                        elif key == "mcp_servers":
                            current_servers = value if isinstance(value, list) else []
                            summary_text = ", ".join(current_servers) if current_servers else "None selected"

                            # Create a container with summary and edit button
                            servers_container = Horizontal(
                                Label(summary_text, classes="servers-summary", id="servers-summary"),
                                Button("Edit Servers", id="edit-servers-button", classes="edit-button"),
                                classes="servers-row",
                            )

                            # Hidden input to store the actual data
                            hidden_input = Input(
                                value=json.dumps(current_servers),
                                id="input-mcp_servers",
                                classes="hidden-input",
                            )
                            widgets_to_mount.append(hidden_input)
                            widgets_to_mount.append(servers_container)

                        else:
                            # Default to Input for other fields
                            widget = Input(value=display_value, id=f"input-{key}", classes="field-input")
                            widgets_to_mount.append(widget)

                        # No spacing between fields to save vertical space

                    widgets_to_mount.append(
                        Button("Save Configuration", variant="success", id="save-button", classes="save-button")
                    )
                    config_data_pane.mount(Vertical(*widgets_to_mount))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Called when a button is pressed."""
        if event.button.id == "save-button":
            self.save_component_config()
        elif event.button.id == "edit-prompt-button":
            self.edit_system_prompt()
        elif event.button.id == "edit-servers-button":
            self.edit_mcp_servers()

    def edit_system_prompt(self) -> None:
        """Pushes the system prompt editor screen."""
        try:
            prompt_input = self.query_one("#input-system_prompt", Input)
            self.app.push_screen(SystemPromptEditorScreen(prompt_input.value), self.update_system_prompt)
        except Exception as e:
            self.notify(f"Error opening editor: {e}", severity="error")

    def update_system_prompt(self, result: Any) -> None:
        """Callback to update the system prompt from the editor screen."""
        if result is None:
            return

        should_save, new_prompt = result
        if new_prompt is not None:
            try:
                prompt_input = self.query_one("#input-system_prompt", Input)
                prompt_input.value = new_prompt
                # Also update the truncated label
                prompt_label = self.query_one(".prompt-display", Label)
                truncated_prompt = (new_prompt[:50] + "...") if len(new_prompt) > 50 else new_prompt
                prompt_label.update(truncated_prompt)

                if should_save:
                    self.save_component_config()
                else:
                    self.notify("System prompt updated locally. Click 'Save' to persist changes.")
            except Exception as e:
                self.notify(f"Error updating prompt: {e}", severity="error")

    def edit_mcp_servers(self) -> None:
        """Pushes the MCP servers editor screen."""
        try:
            servers_input = self.query_one("#input-mcp_servers", Input)
            current_servers = json.loads(servers_input.value)
            all_server_configs = self.aurite.kernel.config_manager.list_configs("mcp_server")
            all_server_names = [config["name"] for config in all_server_configs]

            self.app.push_screen(
                MCPServersEditorScreen(all_server_names, current_servers),
                self.update_mcp_servers,
            )
        except Exception as e:
            self.notify(f"Error opening MCP servers editor: {e}", severity="error")

    def update_mcp_servers(self, result: Any) -> None:
        """Callback to update the MCP servers from the editor screen."""
        if result is None:
            return

        should_save, new_servers = result
        if new_servers is not None:
            try:
                servers_input = self.query_one("#input-mcp_servers", Input)
                servers_input.value = json.dumps(new_servers)
                # Also update the summary label
                servers_summary = self.query_one("#servers-summary", Label)
                summary_text = ", ".join(new_servers) if new_servers else "None selected"
                servers_summary.update(summary_text)

                if should_save:
                    self.save_component_config()
            except Exception as e:
                self.notify(f"Error updating MCP servers: {e}", severity="error")

    def save_component_config(self) -> None:
        """Gathers data from editor inputs and saves the component."""
        if not self.current_component_name or not self.current_component_type:
            self.notify("No component selected to save.", title="Error", severity="error")
            return

        config_data_pane = self.query_one("#config-data-pane")
        new_config = {}
        try:
            # Handle Input widgets
            for input_widget in config_data_pane.query(Input):
                if input_widget.id is None or not input_widget.id.startswith("input-"):
                    continue
                key = input_widget.id.replace("input-", "")
                value = input_widget.value
                try:
                    if value.strip().startswith(("[", "{")):
                        new_config[key] = json.loads(value)
                    else:
                        new_config[key] = value
                except json.JSONDecodeError:
                    new_config[key] = value

            # Handle TextArea widgets
            for textarea_widget in config_data_pane.query(TextArea):
                if textarea_widget.id is None or not textarea_widget.id.startswith("textarea-"):
                    continue
                key = textarea_widget.id.replace("textarea-", "")
                new_config[key] = textarea_widget.text

            # Handle Select widgets
            for select_widget in config_data_pane.query(Select):
                if select_widget.id is None or not select_widget.id.startswith("select-"):
                    continue
                key = select_widget.id.replace("select-", "")
                value = select_widget.value

                # Convert boolean strings back to proper types
                if key == "include_history":
                    new_config[key] = value == "True"
                else:
                    new_config[key] = value

            # Ensure we have the component type and name
            new_config["type"] = self.current_component_type
            new_config["name"] = self.current_component_name

            success = self.aurite.kernel.config_manager.upsert_component(
                self.current_component_type, self.current_component_name, new_config
            )

            if success:
                self.notify(f"Component '{self.current_component_name}' saved successfully.")
            else:
                self.notify(
                    f"Failed to save component '{self.current_component_name}'.",
                    severity="error",
                )

        except Exception as e:
            self.notify(f"An error occurred while saving: {e}", severity="error")


if __name__ == "__main__":
    app = AuriteEditTUI()
    app.run()
