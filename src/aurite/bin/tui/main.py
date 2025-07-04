import json
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, DataTable, RichLog, Input, Button
from textual.containers import Container
from textual.widgets.tree import TreeNode

from ...host_manager import Aurite


class AuriteTUI(App):
    """A Textual TUI for the Aurite framework."""

    BINDINGS = [
        ("right", "focus_next", "Focus Next"),
        ("left", "focus_previous", "Focus Previous"),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    #left-container {
        width: 40;
        height: 100%;
        layout: vertical;
    }
    #navigation-pane {
        height: 50%;
    }
    #list-pane {
        height: 50%;
    }
    #detail-pane {
        width: 1fr;
    }
    #output-pane {
        height: 20;
    }
    #navigation-pane, #list-pane, #detail-pane, #output-pane {
        border: solid $accent;
        padding: 0 1;
    }
    #run-input, #run-button {
        margin-top: 1;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="main-container"):
            with Container(id="left-container"):
                with Container(id="navigation-pane"):
                    yield Tree("Component Types", id="nav-tree")
                with Container(id="list-pane"):
                    yield DataTable(id="list-table")
            with Container(id="detail-pane"):
                yield RichLog(id="detail-log", wrap=True, highlight=True)
                yield Input(
                    placeholder="Enter message...", id="run-input", disabled=True
                )
                yield Button("▶ Run", id="run-button", disabled=True)
        with Container(id="output-pane"):
            yield RichLog(id="output-log", wrap=True, highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.aurite = Aurite()
        self.current_comp_type: str | None = None
        tree = self.query_one(Tree)
        tree.root.expand()
        all_configs = self.aurite.config_manager.get_all_configs()

        for comp_type in all_configs.keys():
            node = tree.root.add_leaf(comp_type.replace("_", " ").title())
            node.data = comp_type

        table = self.query_one(DataTable)
        table.add_column("Name")

        # Disable focus on logs and focus the tree
        self.query_one("#detail-log").can_focus = False
        self.query_one("#output-log").can_focus = False
        tree.focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Called when a node in the tree is selected."""
        node: TreeNode = event.node
        if not node.data:
            self.current_comp_type = None
            return

        self.current_comp_type = node.data
        if not self.current_comp_type:
            return
        configs = self.aurite.config_manager.list_configs(self.current_comp_type)

        table = self.query_one(DataTable)
        table.clear()

        # Add columns dynamically based on component type
        if configs:
            sample_config = configs[0]
            headers = list(sample_config.keys())
            # A bit of cleanup for better display
            if "_origin" in headers:
                headers.remove("_origin")
            if "name" in headers:
                headers.remove("name")
                headers.insert(0, "name")

            table.columns.clear()
            for header in headers:
                table.add_column(header.replace("_", " ").title())

            for config in configs:
                row_data = []
                for header in headers:
                    value = config.get(header, "")
                    # Ensure all data is string for the table
                    row_data.append(str(value) if value is not None else "")
                table.add_row(*row_data, key=config.get("name"))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Called when a row in the data table is selected."""
        row_key = event.row_key.value
        if not row_key:
            return

        # We need to know the current component type to fetch the full config
        if not self.current_comp_type:
            return

        config = self.aurite.config_manager.get_config(self.current_comp_type, row_key)

        detail_log = self.query_one("#detail-log", RichLog)
        run_input = self.query_one("#run-input", Input)
        run_button = self.query_one("#run-button", Button)

        detail_log.clear()
        if config:
            pretty_json = json.dumps(config, indent=2, default=str)
            detail_log.write(pretty_json)

        runnable_types = ["agents", "simple_workflows", "custom_workflows"]
        is_runnable = self.current_comp_type in runnable_types

        run_input.disabled = not is_runnable
        run_button.disabled = not is_runnable

        if is_runnable:
            run_input.focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Called when a button is pressed."""
        if event.button.id == "run-button":
            table = self.query_one(DataTable)
            if table.cursor_row is None:
                return

            component_name = table.get_row_at(table.cursor_row)[0]

            if not self.current_comp_type:
                return

            component_type = self.current_comp_type

            run_input = self.query_one("#run-input", Input)
            user_message = run_input.value

            output_log = self.query_one("#output-log", RichLog)
            output_log.clear()
            output_log.write(f"Running {component_type} '{component_name}'...")

            self.run_worker(
                self.execute_component(component_type, component_name, user_message),
                exclusive=True,
            )

    async def execute_component(
        self, component_type: str, component_name: str, user_message: str
    ):
        """Executes the component in a worker thread."""
        output_log = self.query_one("#output-log", RichLog)
        async with self.aurite:
            try:
                if component_type == "agents":
                    async for event in self.aurite.execution.stream_agent_run(
                        agent_name=component_name, user_message=user_message
                    ):
                        self.call_from_thread(output_log.write, f"EVENT: {event}")
                elif component_type == "simple_workflows":
                    result = await self.aurite.execution.run_simple_workflow(
                        workflow_name=component_name, initial_input=user_message
                    )
                    self.call_from_thread(output_log.write, str(result))
                elif component_type == "custom_workflows":
                    try:
                        parsed_input = json.loads(user_message)
                    except json.JSONDecodeError:
                        parsed_input = user_message
                    result = await self.aurite.execution.run_custom_workflow(
                        workflow_name=component_name, initial_input=parsed_input
                    )
                    self.call_from_thread(output_log.write, str(result))
                else:
                    self.call_from_thread(
                        output_log.write,
                        f"[bold red]Error: Unknown runnable component type '{component_type}'[/bold red]",
                    )
            except Exception as e:
                self.call_from_thread(
                    output_log.write, f"[bold red]Execution Error: {e}[/bold red]"
                )


if __name__ == "__main__":
    app = AuriteTUI()
    app.run()
