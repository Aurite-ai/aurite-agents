#!/usr/bin/env python3
"""
Simple test to verify Input widget functionality.
"""

from textual.app import App, ComposeResult
from textual.widgets import Input, Static


class SimpleInputApp(App):
    def compose(self) -> ComposeResult:
        yield Static("Simple Input Test")
        yield Input(placeholder="Type something here...")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.notify(f"You typed: {event.value}")


if __name__ == "__main__":
    app = SimpleInputApp()
    app.run()
