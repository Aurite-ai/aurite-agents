import json

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
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
)
from textual import work
from textual.message import Message

from aurite import Aurite


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
            self.dismiss(editor.text)
        elif event.button.id == "cancel-prompt":
            self.dismiss(None)


class AuriteTUI(App):
    """A Textual user interface for the Aurite framework."""

    class StreamMessage(Message):
        """A message to stream text to the output log."""

        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    CSS_PATH = "main.tcss"

    def __init__(self):
        super().__init__()
        self.aurite = Aurite()
        self.current_component_type: str | None = None
        self.current_component_name: str | None = None

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
                        yield Button("▶ Run", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        tree = self.query_one(Tree)
        tree.root.expand()

        # Populate the navigation tree
        component_types = self.aurite.config_manager.get_all_configs().keys()
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
        configs = self.aurite.config_manager.list_configs(self.current_component_type)

        for config in configs:
            # A simple description, can be improved
            description = config.get("description", "No description")
            table.add_row(config["name"], description)

        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Called when a row in the data table is selected."""
        if self.current_component_type is None:
            return

        detail_pane = self.query_one("#detail-pane", VerticalScroll)
        # Clear previous content
        detail_pane.remove_children()

        row_key = event.row_key
        if row_key is not None:
            self.current_component_name = event.data_table.get_row(row_key)[0]
            if self.current_component_name:
                config = self.aurite.config_manager.get_config(
                    self.current_component_type, self.current_component_name
                )
                if config:
                    for key, value in config.items():
                        # Don't show internal keys in the editor
                        if key.startswith("_"):
                            continue

                        # For complex values (lists, dicts), show as JSON string
                        display_value = (
                            json.dumps(value)
                            if isinstance(value, (dict, list))
                            else str(value)
                        )

                        new_label = Label(f"{key}:", classes="editor-label")

                        if key == "system_prompt":
                            # Special case for system_prompt
                            truncated_prompt = (
                                (display_value[:50] + "...")
                                if len(display_value) > 50
                                else display_value
                            )
                            prompt_label = Label(
                                truncated_prompt, classes="prompt-display"
                            )
                            edit_button = Button("Edit", id="edit-prompt-button")
                            # We still need a hidden input to store the full value for the main save logic
                            hidden_input = Input(
                                value=display_value,
                                id="input-system_prompt",
                                classes="hidden-input",
                            )
                            detail_pane.mount(hidden_input)
                            detail_pane.mount(
                                Horizontal(
                                    new_label,
                                    prompt_label,
                                    edit_button,
                                    classes="editor-row",
                                )
                            )
                        else:
                            new_input = Input(value=display_value, id=f"input-{key}")
                            detail_pane.mount(
                                Horizontal(new_label, new_input, classes="editor-row")
                            )

                    detail_pane.mount(
                        Button("Save", variant="success", id="save-button")
                    )

    def on_stream_message(self, message: StreamMessage) -> None:
        """Write stream message to the output log."""
        output_log = self.query_one("#output-pane", RichLog)
        output_log.write(message.text)

    @work(exclusive=True)
    async def execute_run(self, message: str):
        """Executes a component run in a worker thread."""
        output_log = self.query_one("#output-pane", RichLog)
        self.call_from_thread(output_log.clear)

        if not self.current_component_name:
            self.post_message(self.StreamMessage("Error: No component selected."))
            return

        if self.current_component_type == "agent":
            async for event in self.aurite.execution.stream_agent_run(
                self.current_component_name, message
            ):
                self.post_message(self.StreamMessage(str(event)))
        elif self.current_component_type == "simple_workflow":
            result = await self.aurite.execution.run_simple_workflow(
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
        elif self.current_component_name and self.current_component_type in [
            "agent",
            "simple_workflow",
        ]:
            run_input = self.query_one("#output-pane-controls Input", Input)
            message = run_input.value
            run_input.clear()
            self.execute_run(message)

    def edit_system_prompt(self) -> None:
        """Pushes the system prompt editor screen."""
        try:
            prompt_input = self.query_one("#input-system_prompt", Input)
            self.app.push_screen(
                SystemPromptEditorScreen(prompt_input.value), self.update_system_prompt
            )
        except Exception as e:
            self.notify(f"Error opening editor: {e}", severity="error")

    def update_system_prompt(self, new_prompt: str | None) -> None:
        """Callback to update the system prompt from the editor screen."""
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
                self.notify("System prompt updated. Click 'Save' to persist changes.")
            except Exception as e:
                self.notify(f"Error updating prompt: {e}", severity="error")

    def save_component_config(self) -> None:
        """Gathers data from editor inputs and saves the component."""
        if not self.current_component_name or not self.current_component_type:
            self.notify(
                "No component selected to save.", title="Error", severity="error"
            )
            return

        detail_pane = self.query_one("#detail-pane")
        inputs = detail_pane.query(Input)
        new_config = {}
        try:
            for input_widget in inputs:
                if input_widget.id is None:
                    continue
                key = input_widget.id.replace("input-", "")
                value = input_widget.value
                # Attempt to parse complex values back from JSON string
                try:
                    if value.strip().startswith(("[", "{")):
                        new_config[key] = json.loads(value)
                    else:
                        # Handle potential type conversions for non-string values if necessary
                        # For now, we treat them as strings.
                        new_config[key] = value
                except json.JSONDecodeError:
                    new_config[key] = value  # Keep as string if not valid JSON

            # We need to add back the 'name' as it's not an editable field
            new_config["name"] = self.current_component_name

            success = self.aurite.config_manager.upsert_component(
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
