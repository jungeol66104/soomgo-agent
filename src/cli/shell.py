"""Simple shell/launcher interface for Soomgo agent."""

from rich.console import Console
from prompt_toolkit import prompt

from .daemon import start_daemon, stop_daemon, show_status, show_logs, is_running

console = Console()

# Color Palette
COLORS = {
    "primary": "rgb(105,59,242)",
    "user": "rgb(52,211,153)",
    "success": "rgb(46,213,115)",
    "warning": "rgb(255,159,67)",
    "error": "rgb(255,71,87)",
    "text": "rgb(245,246,250)",
    "text_dim": "rgb(160,170,185)",
}


def print_banner(env):
    """Print welcome banner."""
    console.print()
    console.print(f"[bold {COLORS['primary']}]Soomgo Agent[/bold {COLORS['primary']}] [dim]({env.env_type} mode)[/dim]")
    console.print()
    console.print(f"[{COLORS['text_dim']}]Commands:[/{COLORS['text_dim']}]")
    console.print(f"  [bold {COLORS['user']}]/viewer[/bold {COLORS['user']}]  - Browse all conversations")
    console.print(f"  [bold {COLORS['user']}]/quit[/bold {COLORS['user']}] or [bold {COLORS['user']}]/exit[/bold {COLORS['user']}] - Exit")
    console.print()


def run_shell(env):
    """Run the shell loop."""
    print_banner(env)

    while True:
        try:
            # Get user input
            user_input = prompt("> ").strip().lower()

            if not user_input:
                continue

            # Handle commands
            if user_input in ['/quit', '/exit', '/q']:
                console.print(f"[{COLORS['text_dim']}]Goodbye![/{COLORS['text_dim']}]")
                break

            elif user_input == '/viewer':
                console.print(f"[{COLORS['success']}]Opening TUI...[/{COLORS['success']}]")
                console.print()
                from .tui import run_chat_viewer
                run_chat_viewer(env)
                console.print()
                console.print(f"[{COLORS['text_dim']}]Back to shell[/{COLORS['text_dim']}]")
                console.print()

            else:
                console.print(f"[{COLORS['error']}]Unknown command: {user_input}[/{COLORS['error']}]")

            console.print()

        except KeyboardInterrupt:
            console.print()
            continue

        except EOFError:
            break

        except Exception as e:
            console.print(f"[{COLORS['error']}]Error: {e}[/{COLORS['error']}]")
            console.print()
            continue
