"""
Simulates a screenshot of the Textual devtools
"""

from textual.app import App
from textual.widgets import Static
from textual_dev.renderables import DevConsoleHeader


class ConsoleApp(App):
    def compose(self):
        yield Static(DevConsoleHeader())


app = ConsoleApp()
