#!/usr/bin/env python3
"""Diagnostic script to test terminal color support."""

import sys
import os

print("=" * 80)
print("TERMINAL COLOR DIAGNOSTICS")
print("=" * 80)
print()

# Test 1: Check environment
print("1. ENVIRONMENT VARIABLES:")
print(f"   TERM: {os.environ.get('TERM', 'NOT SET')}")
print(f"   COLORTERM: {os.environ.get('COLORTERM', 'NOT SET')}")
print(f"   TERM_PROGRAM: {os.environ.get('TERM_PROGRAM', 'NOT SET')}")
print()

# Test 2: Check if stdout is a terminal
print("2. STDOUT CHECK:")
print(f"   Is TTY: {sys.stdout.isatty()}")
print()

# Test 3: Test Rich console
print("3. RICH CONSOLE TEST:")
try:
    from rich.console import Console
    console = Console()
    print(f"   Color system: {console.color_system}")
    print(f"   Is terminal: {console.is_terminal}")
    print(f"   Legacy windows: {console.legacy_windows}")
    print()

    print("   Color output test:")
    console.print("   [red]Red text[/red]")
    console.print("   [cyan]Cyan text[/cyan]")
    console.print("   [green]Green text[/green]")
    console.print("   [yellow]Yellow text[/yellow]")
    console.print("   [bright_cyan]Bright cyan text[/bright_cyan]")
except Exception as e:
    print(f"   ERROR: {e}")
print()

# Test 4: Test ANSI escape codes directly
print("4. ANSI ESCAPE CODES TEST:")
print(f"   \033[31mRed (ANSI 31)\033[0m")
print(f"   \033[36mCyan (ANSI 36)\033[0m")
print(f"   \033[32mGreen (ANSI 32)\033[0m")
print(f"   \033[96mBright cyan (ANSI 96)\033[0m")
print()

# Test 5: Test Textual
print("5. TEXTUAL TEST:")
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Label, Static
    from textual.screen import Screen

    from rich.text import Text

    class ColorTestScreen(Screen):
        def compose(self) -> ComposeResult:
            yield Static("TEXTUAL COLOR TEST - FIXED VERSION (v2.0+)", id="header")
            yield Label("Normal text (Label)")
            yield Label("")

            # WRONG WAY #1 - Label with markup (doesn't work)
            yield Label("[red]❌ Label with markup (doesn't work)[/red]", markup=True)

            # WRONG WAY #2 - Static with Text() and style (doesn't work in v2.0+)
            wrong_text = Text("❌ Text() with style (doesn't work in v2.0+)", style="red")
            yield Static(wrong_text)

            yield Label("")

            # CORRECT WAY - Static with Text.from_markup() (works in v2.0+!)
            red_text = Text.from_markup("[red]✓ Text.from_markup with [red] (WORKS!)[/red]")
            yield Static(red_text)

            cyan_text = Text.from_markup("[cyan]✓ Cyan color with from_markup[/cyan]")
            yield Static(cyan_text)

            green_text = Text.from_markup("[green]✓ Green color with from_markup[/green]")
            yield Static(green_text)

            bright_cyan_text = Text.from_markup("[bright_cyan]✓ Bright cyan with from_markup[/bright_cyan]")
            yield Static(bright_cyan_text)

            yield Label("")
            yield Label("Press 'q' to quit")

    class ColorTestApp(App):
        BINDINGS = [("q", "quit", "Quit")]

        def on_mount(self) -> None:
            self.push_screen(ColorTestScreen())

    print("   Launching Textual color test app...")
    print("   (Press 'q' to quit and return)")
    print()

    app = ColorTestApp()
    app.run()

except Exception as e:
    print(f"   ERROR: {e}")

print()
print("=" * 80)
print("DIAGNOSTICS COMPLETE")
print("=" * 80)
