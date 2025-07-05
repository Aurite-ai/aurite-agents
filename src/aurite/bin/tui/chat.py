"""
Textual-based chat interface for interactive agent conversations.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static

from ...host_manager import Aurite, disable_all_logging
from ..ui_utils import (
    format_agent_message,
    format_tool_call_message,
    format_tool_output_message,
    format_user_message,
)


class TextualChatApp(App):
    """A Textual TUI application for interactive agent chat."""

    CSS_PATH = "chat.tcss"

    def __init__(
        self,
        aurite: Optional[Aurite] = None,
        agent_name: str = "",
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        start_dir: Optional[Path] = None,
    ):
        super().__init__()
        # Disable logging globally before creating Aurite instance
        if aurite is None:
            disable_all_logging()
            self.aurite = Aurite(start_dir=start_dir or Path.cwd(), disable_logging=True)
        else:
            self.aurite = aurite
        self.agent_name = agent_name
        self.session_id = session_id or str(uuid.uuid4())
        self.system_prompt = system_prompt
        self.conversation_active = False

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        yield Static(f"Agent: {self.agent_name} | Session: {self.session_id[:8]}...")
        with VerticalScroll(id="chat-history"):
            yield Static("Welcome! Type a message below to start chatting.")
        yield Input(placeholder="Type your message here and press Enter...", id="message-input")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        pass

    def _add_user_message(self, message: str) -> None:
        """Add a user message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)
        formatted_message = format_user_message(message)
        user_widget = Static(formatted_message, classes="user-message")
        user_widget.border_title = "User"
        chat_history.mount(user_widget)
        chat_history.scroll_end()

    def _add_agent_message(self, message: str) -> None:
        """Add an agent message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)
        formatted_message = format_agent_message(message)
        agent_widget = Static(formatted_message, classes="agent-message")
        chat_history.mount(agent_widget)
        chat_history.scroll_end()

    def _create_agent_response_widget(self) -> Container:
        """Create a new agent response widget for streaming."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        agent_container = Container(
            Static("[bold cyan]Agent:[/bold cyan]", classes="agent-label"),
            Markdown("", classes="agent-response", id="current-agent-response"),
            classes="agent-message",
            id="current-agent-container",
        )
        agent_container.border_title = self.agent_name
        chat_history.mount(agent_container)
        chat_history.scroll_end()
        return agent_container

    def _update_agent_response_widget(self, widget: Container, content: str) -> None:
        """Update the current agent response widget with new content."""
        try:
            response_widget = self.query_one("#current-agent-response", Markdown)
            response_widget.update(content)

            # Scroll to keep the latest content visible
            chat_history = self.query_one("#chat-history", VerticalScroll)
            chat_history.scroll_end()
        except Exception:
            # Widget might not exist yet, ignore
            pass

    def _finalize_agent_response(self, widget: Container, content: str) -> None:
        """Finalize the agent response by replacing the streaming widget with a static one."""
        try:
            chat_history = self.query_one("#chat-history", VerticalScroll)

            # Remove the current streaming widget
            widget.remove()

            # Add a final static widget using shared formatting
            formatted_message = format_agent_message(content)
            final_widget = Static(formatted_message, classes="agent-message")
            final_widget.border_title = self.agent_name
            chat_history.mount(final_widget)
            chat_history.scroll_end()
        except Exception:
            # If something goes wrong, just ignore
            pass

    def _add_tool_call_message(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Add a tool call message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        formatted_message = format_tool_call_message(tool_name, tool_input)
        tool_widget = Static(formatted_message, classes="tool-message")
        tool_widget.border_title = f"Tool Call: {tool_name}"
        chat_history.mount(tool_widget)
        chat_history.scroll_end()

    def _add_tool_output_message(self, tool_name: str, tool_output: str) -> None:
        """Add a tool output message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        formatted_message = format_tool_output_message(tool_name, tool_output)
        tool_widget = Static(formatted_message, classes="tool-output-message")
        tool_widget.border_title = f"Tool Result: {tool_name}"
        chat_history.mount(tool_widget)
        chat_history.scroll_end()

    @on(Input.Submitted)
    def handle_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        if self.conversation_active:
            self.notify("Please wait for the current response to complete.", severity="warning")
            return

        message = event.value.strip()
        if not message:
            return

        # Clear the input
        event.input.clear()

        # Add user message to chat
        self._add_user_message(message)

        # Start the agent conversation
        self.run_agent_conversation(message)

    @work(exclusive=True)
    async def run_agent_conversation(self, user_message: str) -> None:
        """Run the agent conversation in a background worker."""
        self.conversation_active = True

        try:
            # Stream the agent response
            current_response = ""
            current_agent_widget = None

            async for event in self.aurite.stream_agent(
                agent_name=self.agent_name,
                user_message=user_message,
                system_prompt=self.system_prompt,
                session_id=self.session_id,
            ):
                event_type = event.get("type")
                event_data = event.get("data", {})

                if event_type == "llm_response_start":
                    # Create the agent response widget
                    current_agent_widget = self._create_agent_response_widget()

                elif event_type == "llm_response":
                    # Accumulate response content
                    content = event_data.get("content", "")
                    current_response += content

                    # Update the agent response widget
                    if current_agent_widget:
                        self._update_agent_response_widget(current_agent_widget, current_response)

                elif event_type == "llm_response_stop":
                    # Response is complete - finalize the response
                    if current_agent_widget and current_response:
                        self._finalize_agent_response(current_agent_widget, current_response)

                elif event_type == "tool_call":
                    tool_name = event_data.get("name", "Unknown")
                    tool_input = event_data.get("input", {})
                    self._add_tool_call_message(tool_name, tool_input)

                elif event_type == "tool_output":
                    tool_name = event_data.get("name", "Unknown")
                    tool_output = event_data.get("output", "")
                    self._add_tool_output_message(tool_name, tool_output)

                elif event_type == "error":
                    error_message = event_data.get("message", "An error occurred")
                    self.notify(f"Agent Error: {error_message}", severity="error")

        except Exception as e:
            self.notify(f"Unexpected error: {str(e)}", severity="error")
        finally:
            self.conversation_active = False

    def action_quit(self) -> None:
        """Override quit action to ensure clean shutdown."""
        self.exit()
