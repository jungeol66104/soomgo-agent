#!/usr/bin/env python3
"""Interactive CLI for chatting with Soomgo agent."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress loguru logs
import os
os.environ["LOGURU_LEVEL"] = "WARNING"

from rich.console import Console
from src.agent import SoomgoAgent

console = Console()

# Color Palette
COLORS = {
    "primary": "rgb(105,59,242)",      # Main purple - for Agent
    "primary_dim": "rgb(130,90,255)",  # Lighter purple
    "user": "rgb(52,211,153)",         # Cyan/teal - for You
    "user_text": "rgb(209,250,229)",   # Light mint - for your messages
    "success": "rgb(46,213,115)",      # Green
    "warning": "rgb(255,159,67)",      # Orange
    "error": "rgb(255,71,87)",         # Red
    "text": "rgb(245,246,250)",        # Off-white - for agent messages
    "text_dim": "rgb(160,170,185)",    # Gray
    "bg": "rgb(30,32,38)",             # Dark bg
}


def print_banner():
    """Print welcome banner - simple, no boxes."""
    console.print()
    console.print(f"[bold {COLORS['primary']}]Soomgo Agent v0[/bold {COLORS['primary']}]")
    console.print(f"[{COLORS['text_dim']}]Interactive CLI Chat Interface[/{COLORS['text_dim']}]")
    console.print()
    console.print(f"[{COLORS['text_dim']}]Commands: /reset /clear /quit /help[/{COLORS['text_dim']}]")
    console.print(f"[{COLORS['text_dim']}]Input: Enter to send • Shift+Enter for new line[/{COLORS['text_dim']}]")
    console.print()


def get_input() -> str:
    """Get user input - simple and resize-proof."""
    from prompt_toolkit import prompt
    from prompt_toolkit.key_binding import KeyBindings

    bindings = KeyBindings()

    @bindings.add('enter')
    def _(event):
        """Enter submits the input."""
        event.current_buffer.validate_and_handle()

    @bindings.add('c-c')
    def _(event):
        """Ctrl+C cancels."""
        raise KeyboardInterrupt()

    @bindings.add('c-d')
    def _(event):
        """Ctrl+D cancels."""
        raise EOFError()

    try:
        # Simple multiline prompt - Enter to send, Shift+Enter (via iTerm2) for new line
        user_input = prompt(
            "> ",
            multiline=True,
            key_bindings=bindings,
        )
        return user_input.strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def main():
    """Main CLI loop."""
    print_banner()

    # Initialize agent - simple indicator
    console.print(f"[{COLORS['text_dim']}]Initializing agent...[/{COLORS['text_dim']}]", end="\r")
    try:
        agent = SoomgoAgent()
        # Clear the entire line and print success
        console.print(" " * 50, end="\r")  # Clear the line
        console.print(f"[{COLORS['success']}]✓ Agent ready![/{COLORS['success']}]")
        console.print()
    except Exception as e:
        console.print(" " * 50, end="\r")  # Clear the line
        console.print(f"[{COLORS['error']}]✗ Failed to initialize: {e}[/{COLORS['error']}]")
        return 1

    # Conversation history and state
    history = []
    gathered_info = None  # Track gathered information
    conversation_state = None  # Track conversation state
    last_closure_response = None  # Track last closure response

    # Main loop
    while True:
        try:
            # Print "You" label in cyan/teal
            console.print(f"[bold {COLORS['user']}]You[/bold {COLORS['user']}]")

            # Get user input (simple, no box)
            user_input = get_input()

            # Handle slash commands
            if user_input.lower() in ['/quit', '/exit', '/q']:
                break

            if user_input.lower() == '/reset':
                history = []
                gathered_info = None
                conversation_state = None
                last_closure_response = None
                console.print(f"[{COLORS['warning']}]✓ Conversation reset[/{COLORS['warning']}]")
                console.print()
                continue

            if user_input.lower() == '/clear':
                console.clear()
                print_banner()
                console.print(f"[{COLORS['success']}]✓ Display cleared[/{COLORS['success']}]")
                console.print()
                continue

            if user_input.lower() == '/help':
                console.print()
                console.print(f"[{COLORS['text_dim']}]Commands:[/{COLORS['text_dim']}]")
                console.print(f"  [bold {COLORS['user']}]/reset[/bold {COLORS['user']}] - Clear conversation history")
                console.print(f"  [bold {COLORS['user']}]/clear[/bold {COLORS['user']}] - Clear terminal display")
                console.print(f"  [bold {COLORS['user']}]/quit[/bold {COLORS['user']}] or [bold {COLORS['user']}]/exit[/bold {COLORS['user']}] - Exit")
                console.print(f"  [bold {COLORS['user']}]/help[/bold {COLORS['user']}] - Show this help")
                console.print()
                continue

            if not user_input:
                continue

            console.print()  # Blank line after user input

            # Get agent response
            console.print(f"[{COLORS['text_dim']}]Thinking...[/{COLORS['text_dim']}]", end="\r")
            response, gathered_info, conversation_state, last_closure_response = agent.chat(
                user_input, history, gathered_info, conversation_state, last_closure_response
            )

            # Display response with Agent label in purple
            console.print(" " * 20, end="\r")  # Clear "Thinking..."
            console.print(f"[bold {COLORS['primary']}]Agent[/bold {COLORS['primary']}]")
            console.print(f"[{COLORS['text']}]{response}[/{COLORS['text']}]")
            console.print()  # Spacing after response

            # Update history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            console.print()
            console.print(f"[{COLORS['text_dim']}]Type /quit to exit[/{COLORS['text_dim']}]")
            console.print()
            continue

        except Exception as e:
            console.print()
            console.print(f"[{COLORS['error']}]Error: {e}[/{COLORS['error']}]")
            console.print()
            continue

    return 0


if __name__ == "__main__":
    sys.exit(main())
