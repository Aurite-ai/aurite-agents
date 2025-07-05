"""
Textual-based chat interface for interactive agent conversations.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static

from ...host_manager import Aurite, disable_all_logging


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
        with Container(id="main-container"):
            with Vertical(id="chat-container"):
                yield Static(
                    f"Agent: {self.agent_name}\n"
                    f"Session ID: {self.session_id}\n"
                    f"Type your message below. Press Ctrl+C to exit.",
                    id="chat-header",
                )
                with VerticalScroll(id="chat-history"):
                    pass  # Chat messages will be added here dynamically
                with Horizontal(id="input-container"):
                    yield Input(placeholder="Type your message here...", id="message-input")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Focus the input field
        self.query_one("#message-input", Input).focus()

        # Load any existing conversation history
        self._load_conversation_history()

    def _load_conversation_history(self) -> None:
        """Load existing conversation history if available."""
        if not self.aurite.kernel.cache_manager:
            return

        history = self.aurite.kernel.cache_manager.get_history(self.session_id)
        if not history:
            return

        for message in history:
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "user":
                self._add_user_message(content, add_to_history=False)
            elif role == "assistant":
                self._add_agent_message(content, add_to_history=False)

    def _add_user_message(self, message: str, add_to_history: bool = True) -> None:
        """Add a user message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        user_widget = Static(f"You: {message}", classes="user-message")
        chat_history.mount(user_widget)
        chat_history.scroll_end()

    def _add_agent_message(self, message: str, add_to_history: bool = True) -> None:
        """Add an agent message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        # Use Static widget for simpler display
        agent_widget = Static(f"Agent: {message}", classes="agent-message")
        chat_history.mount(agent_widget)
        chat_history.scroll_end()

    def _add_tool_call_message(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Add a tool call message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        tool_widget = Static(
            f"[yellow]🔧 Calling tool:[/yellow] [bold]{tool_name}[/bold]\n" f"[dim]Input: {tool_input}[/dim]",
            classes="tool-message",
        )
        chat_history.mount(tool_widget)
        chat_history.scroll_end()

    def _add_tool_output_message(self, tool_name: str, tool_output: str) -> None:
        """Add a tool output message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        # Truncate very long outputs for display
        display_output = tool_output
        if len(display_output) > 200:
            display_output = display_output[:200] + "..."

        tool_widget = Static(
            f"[green]✅ Tool result:[/green] [bold]{tool_name}[/bold]\n" f"[dim]{display_output}[/dim]",
            classes="tool-output-message",
        )
        chat_history.mount(tool_widget)
        chat_history.scroll_end()

    def _add_status_message(self, message: str, style: str = "dim") -> None:
        """Add a status message to the chat history."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        status_widget = Static(f"[{style}]{message}[/{style}]", classes="status-message")
        chat_history.mount(status_widget)
        chat_history.scroll_end()

    @on(Input.Submitted, "#message-input")
    def handle_message_input(self, event: Input.Submitted) -> None:
        """Handle user message submission."""
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
            # Add status message
            self._add_status_message("🤔 Agent is thinking...")

            # Stream the agent response
            current_response = ""

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
                    self._create_agent_response_widget()

                elif event_type == "llm_response":
                    # Accumulate response content
                    content = event_data.get("content", "")
                    current_response += content

                    # Update the agent response widget
                    self._update_agent_response(current_response)

                elif event_type == "llm_response_stop":
                    # Response is complete - finalize the response
                    if hasattr(self, "current_agent_widget") and current_response:
                        # Replace the streaming widget with a final static widget
                        self._finalize_agent_response(current_response)

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
                    self._add_status_message(f"❌ Error: {error_message}", "bold red")

        except Exception as e:
            self._add_status_message(f"❌ Unexpected error: {str(e)}", "bold red")
        finally:
            self.conversation_active = False

            # Remove the thinking status message
            self._remove_last_status_message()

    def _create_agent_response_widget(self) -> None:
        """Create a new agent response widget."""
        chat_history = self.query_one("#chat-history", VerticalScroll)

        self.current_agent_widget = Container(
            Static("[bold cyan]Agent:[/bold cyan]", classes="agent-label"),
            Markdown("", classes="agent-response", id="current-agent-response"),
            classes="agent-message",
        )
        chat_history.mount(self.current_agent_widget)
        chat_history.scroll_end()

    def _update_agent_response(self, content: str) -> None:
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

    def _finalize_agent_response(self, content: str) -> None:
        """Finalize the agent response by replacing the streaming widget with a static one."""
        try:
            chat_history = self.query_one("#chat-history", VerticalScroll)

            # Remove the current streaming widget
            if hasattr(self, "current_agent_widget"):
                self.current_agent_widget.remove()
                delattr(self, "current_agent_widget")

            # Add a final static widget
            final_widget = Static(f"Agent: {content}", classes="agent-message")
            chat_history.mount(final_widget)
            chat_history.scroll_end()
        except Exception:
            # If something goes wrong, just ignore
            pass

    def _remove_last_status_message(self) -> None:
        """Remove the last status message (thinking indicator)."""
        try:
            chat_history = self.query_one("#chat-history", VerticalScroll)
            status_messages = chat_history.query(".status-message")
            if status_messages:
                status_messages[-1].remove()
        except Exception:
            # Ignore if no status messages exist
            pass

    def action_quit(self) -> None:
        """Override quit action to ensure clean shutdown."""
        self.exit()
