#!/usr/bin/env python3
"""Quick test to verify Static widget markup rendering."""

from textual.app import App, ComposeResult
from textual.widgets import Static, Label
from textual.screen import Screen


class MarkupTestScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("=== Testing Static Widget Markup ===")
        yield Label("")

        # Test 1: Simple cyan text
        yield Static("[cyan]This should be CYAN[/cyan]")

        # Test 2: Multi-line with each line wrapped
        lines = [
            "[cyan]╔═ Header Line[/cyan]",
            "[cyan]║  Content line 1[/cyan]",
            "[cyan]║  Content line 2[/cyan]",
            "[cyan]╚════════════[/cyan]"
        ]
        yield Static("\n".join(lines))

        yield Label("")
        yield Label("Press 'q' to quit")


class MarkupTestApp(App):
    BINDINGS = [("q", "quit", "Quit")]

    def on_mount(self) -> None:
        self.push_screen(MarkupTestScreen())


if __name__ == "__main__":
    app = MarkupTestApp()
    app.run()
