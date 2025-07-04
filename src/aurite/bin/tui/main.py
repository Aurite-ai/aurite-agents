import json
import logging
import uuid
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.logging import TextualHandler
from textual.screen import ModalScreen
from textual.widgets import (
    Header,
    Footer,
    Tree,
    DataTable,
    RichLog,
    Input,
    Button,
    Label,
    TextArea,
    Select,
    Checkbox,
)
from textual import work
from textual.message import Message
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


class AuriteTUI(App):
    """A Textual user interface for the Aurite framework."""

    class StreamMessage(Message):
        """A message to stream text to the output log."""

        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    class ClearLogMessage(Message):
        """A message to clear the output log."""

        pass

    CSS_PATH = "main.tcss"

    def __init__(self):
        super().__init__()
        self.aurite = Aurite()
        self.current_component_type: str | None = None
        self.current_component_name: str | None = None
        self.current_session_id: str | None = None
        self.session_agent_name: str | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container():
            with Vertical(id="left-pane"):
                yield Tree("Components", id="nav-pane")
                yield DataTable(id="list-pane")
            with Vertical(id="right-pane"):
                yield VerticalScroll(id="detail-pane")
                with Vertical(id="output-pane-container"):
                    yield RichLog(wrap=True, id="output-pane")
                    with Horizontal(id="output-pane-controls"):
                        yield Input(placeholder="Enter message...")
                        yield Button("▶ Run", variant="primary", id="run-button")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        tree = self.query_one(Tree)
        tree.root.expand()

        # Populate the navigation tree
        component_types = self.aurite._core.config_manager.get_all_configs().keys()
        for component_type in component_types:
            tree.root.add(component_type)

        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "Description")
        # Initially populate with a default or empty state
        table.clear()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Called when a node in the tree is selected."""
        table = self.query_one(DataTable)
        table.clear()

        self.current_component_type = str(event.node.label)
        configs = self.aurite._core.config_manager.list_configs(
            self.current_component_type
        )

        for config in configs:
            # A simple description, can be improved
            description = config.get("description", "No description")
            table.add_row(config["name"], description)

        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Called when a row in the data table is selected."""
        if self.current_component_type is None:
            return

        # Clear the output pane when a new component is selected
        output_log = self.query_one("#output-pane", RichLog)
        output_log.clear()

        detail_pane = self.query_one("#detail-pane", VerticalScroll)
        detail_pane.remove_children()

        row_key = event.row_key
        if row_key is not None:
            self.current_component_name = event.data_table.get_row(row_key)[0]
            if self.current_component_name:
                config = self.aurite._core.config_manager.get_config(
                    self.current_component_type, self.current_component_name
                )
                if config:
                    widgets_to_mount = []
                    for key, value in config.items():
                        if key.startswith("_"):
                            continue

                        display_value = (
                            json.dumps(value)
                            if isinstance(value, (dict, list))
                            else str(value)
                        )
                        new_label = Label(f"{key}:", classes="editor-label")

                        if key == "system_prompt":
                            truncated_prompt = (
                                (display_value[:50] + "...")
                                if len(display_value) > 50
                                else display_value
                            )
                            prompt_label = Label(
                                truncated_prompt, classes="prompt-display"
                            )
                            edit_button = Button("Edit", id="edit-prompt-button")
                            hidden_input = Input(
                                value=display_value,
                                id="input-system_prompt",
                                classes="hidden-input",
                            )
                            widgets_to_mount.append(hidden_input)
                            widgets_to_mount.append(
                                Horizontal(
                                    new_label,
                                    prompt_label,
                                    edit_button,
                                    classes="editor-row",
                                )
                            )
                        elif key == "llm_config_id":
                            llm_configs = self.aurite._core.config_manager.list_configs(
                                "llms"
                            )
                            llm_names = [c["name"] for c in llm_configs]
                            select = Select(
                                options=[(name, name) for name in llm_names],
                                value=display_value,
                                id="select-llm_config_id",
                            )
                            widgets_to_mount.append(
                                Horizontal(new_label, select, classes="editor-row")
                            )
                        elif key == "mcp_servers":
                            current_servers = value if isinstance(value, list) else []
                            summary_text = (
                                ", ".join(current_servers)
                                if current_servers
                                else "None"
                            )
                            if len(summary_text) > 50:
                                summary_text = summary_text[:47] + "..."
                            servers_label = Label(
                                summary_text, classes="prompt-display"
                            )
                            edit_button = Button("Edit", id="edit-servers-button")
                            hidden_input = Input(
                                value=json.dumps(current_servers),
                                id="input-mcp_servers",
                                classes="hidden-input",
                            )
                            widgets_to_mount.append(hidden_input)
                            widgets_to_mount.append(
                                Horizontal(
                                    new_label,
                                    servers_label,
                                    edit_button,
                                    classes="editor-row",
                                    id="mcp_servers-row",
                                )
                            )
                        else:
                            new_input = Input(value=display_value, id=f"input-{key}")
                            widgets_to_mount.append(
                                Horizontal(new_label, new_input, classes="editor-row")
                            )

                    widgets_to_mount.append(
                        Button("Save", variant="success", id="save-button")
                    )
                    detail_pane.mount(Vertical(*widgets_to_mount))

    def on_stream_message(self, message: StreamMessage) -> None:
        """Write stream message to the output log."""
        try:
            output_log = self.query_one("#output-pane", RichLog)
            output_log.write(message.text)
        except Exception as e:
            self.notify(f"Error writing to log: {e}", severity="error")

    def on_clear_log_message(self, message: ClearLogMessage) -> None:
        """Clears the output log."""
        try:
            output_log = self.query_one("#output-pane", RichLog)
            output_log.clear()
        except Exception as e:
            self.notify(f"Error clearing log: {e}", severity="error")

    @work(exclusive=True)
    async def execute_run(self, message: str):
        """Executes a component run in a worker thread."""
        self.post_message(self.StreamMessage(f"\n[bold]You:[/bold] {message}"))

        if not self.current_component_name:
            self.post_message(self.StreamMessage("Error: No component selected."))
            return

        if self.current_component_type == "agents":
            # Session management
            if self.session_agent_name != self.current_component_name:
                self.session_agent_name = self.current_component_name
                self.current_session_id = str(uuid.uuid4())
                self.post_message(self.ClearLogMessage())
                self.post_message(
                    self.StreamMessage(
                        f"[dim]New chat session started (ID: {self.current_session_id})[/dim]\n"
                    )
                )

            self.post_message(self.StreamMessage("[bold]Agent:[/bold] "))
            async for event in self.aurite._core.execution.stream_agent_run(
                self.current_component_name, message, session_id=self.current_session_id
            ):
                if event.get("type") == "llm_response":
                    self.post_message(
                        self.StreamMessage(event.get("data", {}).get("content", ""))
                    )

        elif self.current_component_type == "simple_workflows":
            self.post_message(self.ClearLogMessage())
            result = await self.aurite._core.execution.run_simple_workflow(
                self.current_component_name, message
            )
            self.post_message(self.StreamMessage(str(result)))
        else:
            self.post_message(
                self.StreamMessage("This component type is not runnable.")
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Called when a button is pressed."""
        if event.button.id == "save-button":
            self.save_component_config()
        elif event.button.id == "edit-prompt-button":
            self.edit_system_prompt()
        elif event.button.id == "edit-servers-button":
            self.edit_mcp_servers()
        elif event.button.id == "run-button":
            if self.current_component_name and self.current_component_type in [
                "agents",
                "simple_workflows",
            ]:
                run_input = self.query_one("#output-pane-controls Input", Input)
                message = run_input.value
                run_input.clear()
                self.execute_run(message)
            else:
                self.notify(
                    "Please select a runnable component (agent or workflow) first.",
                    severity="warning",
                )

    def edit_system_prompt(self) -> None:
        """Pushes the system prompt editor screen."""
        try:
            prompt_input = self.query_one("#input-system_prompt", Input)
            self.app.push_screen(
                SystemPromptEditorScreen(prompt_input.value), self.update_system_prompt
            )
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
                truncated_prompt = (
                    (new_prompt[:50] + "...") if len(new_prompt) > 50 else new_prompt
                )
                prompt_label.update(truncated_prompt)

                if should_save:
                    self.save_component_config()
                else:
                    self.notify(
                        "System prompt updated locally. Click 'Save' to persist changes."
                    )
            except Exception as e:
                self.notify(f"Error updating prompt: {e}", severity="error")

    def edit_mcp_servers(self) -> None:
        """Pushes the MCP servers editor screen."""
        try:
            servers_input = self.query_one("#input-mcp_servers", Input)
            current_servers = json.loads(servers_input.value)
            all_server_configs = self.aurite._core.config_manager.list_configs(
                "mcp_servers"
            )
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
                servers_row = self.query_one("#mcp_servers-row")
                servers_label = servers_row.query_one(".prompt-display", Label)
                summary_text = ", ".join(new_servers) if new_servers else "None"
                if len(summary_text) > 50:
                    summary_text = summary_text[:47] + "..."
                servers_label.update(summary_text)

                if should_save:
                    self.save_component_config()
            except Exception as e:
                self.notify(f"Error updating MCP servers: {e}", severity="error")

    def save_component_config(self) -> None:
        """Gathers data from editor inputs and saves the component."""
        if not self.current_component_name or not self.current_component_type:
            self.notify(
                "No component selected to save.", title="Error", severity="error"
            )
            return

        detail_pane = self.query_one("#detail-pane")
        new_config = {}
        try:
            # Handle regular inputs
            for input_widget in detail_pane.query(Input):
                if input_widget.id is None or "input-" not in input_widget.id:
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

            # Handle the Select widget for llm_config_id
            try:
                select_widget = detail_pane.query_one("#select-llm_config_id", Select)
                if select_widget.value is not None:
                    new_config["llm_config_id"] = select_widget.value
            except Exception:
                pass  # Widget might not exist

            # The mcp_servers value is now stored in a hidden input, so it's handled by the main loop.
            # No special handling is needed here anymore.

            # We need to add back the 'name' as it's not an editable field
            new_config["name"] = self.current_component_name

            success = self.aurite._core.config_manager.upsert_component(
                self.current_component_type, self.current_component_name, new_config
            )

            if success:
                self.notify(
                    f"Component '{self.current_component_name}' saved successfully."
                )
            else:
                self.notify(
                    f"Failed to save component '{self.current_component_name}'.",
                    severity="error",
                )

        except Exception as e:
            self.notify(f"An error occurred while saving: {e}", severity="error")


if __name__ == "__main__":
    app = AuriteTUI()
    app.run()
