import logging
from textual.app import App, ComposeResult
from textual.widgets import RichLog
from textual.logging import TextualHandler
from textual.message import Message
from textual import work

from aurite import Aurite


class TempApp(App):
    """A temporary app to test agent execution."""

    class AgentResponseMessage(Message):
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    def compose(self) -> ComposeResult:
        yield RichLog(id="log", wrap=True)

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.run_agent_test()

    @work
    async def run_agent_test(self) -> None:
        """Runs the weather agent and posts the result."""
        aurite = Aurite()
        result = await aurite.run_agent(
            agent_name="Weather Agent",
            user_message="Weather in London?",
        )
        if result and result.primary_text:
            self.post_message(self.AgentResponseMessage(result.primary_text))
        else:
            self.post_message(
                self.AgentResponseMessage("Agent did not return a response.")
            )

    def on_temp_app_agent_response_message(self, message: AgentResponseMessage) -> None:
        """Write the agent response to the log."""
        log_widget = self.query_one("#log", RichLog)
        log_widget.write(message.text)


if __name__ == "__main__":
    # This is the key: configure logging here, after all imports,
    # to ensure it overrides any other logging setup.
    logging.basicConfig(
        level="INFO",
        handlers=[TextualHandler()],
        force=True,  # This will remove and replace any existing handlers.
    )
    app = TempApp()
    app.run()
