import json

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Tree, DataTable, RichLog, Input, Button
from textual import work
from textual.message import Message

from aurite import Aurite


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
                yield RichLog(id="detail-pane", wrap=True)
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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Called when a row in the data table is selected."""
        if self.current_component_type is None:
            return

        detail_pane = self.query_one("#detail-pane", RichLog)
        detail_pane.clear()

        row_key = event.row_key
        if row_key is not None:
            self.current_component_name = event.data_table.get_row(row_key)[0]
            if self.current_component_name:
                config = self.aurite.config_manager.get_config(
                    self.current_component_type, self.current_component_name
                )
                pretty_json = json.dumps(config, indent=2)
                detail_pane.write(pretty_json)

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
        """Called when the run button is pressed."""
        if self.current_component_name and self.current_component_type in [
            "agent",
            "simple_workflow",
        ]:
            input_widget = self.query_one(Input)
            message = input_widget.value
            input_widget.clear()
            self.execute_run(message)


if __name__ == "__main__":
    app = AuriteTUI()
    app.run()
