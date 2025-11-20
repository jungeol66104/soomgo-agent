"""Main TUI application - menu, daemon controls, and chat browsing."""

import json
import textwrap
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll, Center
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static, Input, Button
from textual.screen import Screen, ModalScreen
from rich.text import Text

from src.scraper.central_db import CentralChatDatabase
from src.scraper.message_central_db import MessageCentralDB
from src.simulation.runner import SimulationRunner
from src.cli.config_manager import is_configured, set_api_key, load_config


def wrap_message_text(text: str, width: int = 75) -> str:
    """Wrap long lines in message text to fit terminal width.

    Args:
        text: Message text (may contain newlines)
        width: Maximum width for each line

    Returns:
        Text with long lines wrapped
    """
    lines = text.split('\n')
    wrapped_lines = []

    for line in lines:
        if len(line) <= width:
            wrapped_lines.append(line)
        else:
            # Wrap long line
            wrapped = textwrap.fill(
                line,
                width=width,
                break_long_words=False,
                break_on_hyphens=False
            )
            wrapped_lines.append(wrapped)

    return '\n'.join(wrapped_lines)


class SetupScreen(ModalScreen):
    """First-run setup screen for API key configuration."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    SetupScreen {
        align: center middle;
    }

    #setup-dialog {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 2;
    }

    #setup-title {
        text-align: center;
        text-style: bold;
        color: $accent;
    }

    #api-key-input {
        width: 100%;
    }

    #save-button {
        width: 100%;
    }
    """

    def __init__(self, env):
        super().__init__()
        self.env = env

    def compose(self) -> ComposeResult:
        yield Container(
            Static("First-time Setup", id="setup-title"),
            Static(""),
            Static("OpenAI API Key:"),
            Input(placeholder="sk-...", password=True, id="api-key-input"),
            Static(""),
            Button("Save & Continue", variant="primary", id="save-button"),
            id="setup-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle save button press."""
        if event.button.id == "save-button":
            api_key_input = self.query_one("#api-key-input", Input)
            api_key = api_key_input.value.strip()

            if not api_key:
                self.app.notify("API key cannot be empty", severity="error")
                return

            if not api_key.startswith("sk-"):
                self.app.notify("Invalid API key format", severity="error")
                return

            # Save API key
            if set_api_key(self.env, api_key):
                self.app.notify("Configuration saved!", severity="information")
                self.dismiss(True)
            else:
                self.app.notify("Failed to save configuration", severity="error")

    def action_cancel(self) -> None:
        """Cancel setup and quit."""
        self.app.exit()


class SettingsScreen(Screen):
    """Settings screen to view/edit configuration."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("b", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, env):
        super().__init__()
        self.env = env

    def compose(self) -> ComposeResult:
        yield Static("Settings", id="header")
        yield Container(
            Static("OpenAI API Key:"),
            Static(""),
            Input(placeholder="sk-...", password=True, id="api-key-input"),
            Static(""),
            Button("Save Changes", variant="primary", id="save-button"),
            id="settings-container",
        )
        yield Static("Esc/b: back  |  q: quit", id="footer")

    def on_mount(self) -> None:
        """Load current config on mount."""
        from src.cli.config_manager import get_api_key

        api_key = get_api_key(self.env)
        if api_key:
            # Show masked API key
            api_key_input = self.query_one("#api-key-input", Input)
            api_key_input.value = api_key

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle save button press."""
        if event.button.id == "save-button":
            from src.cli.config_manager import set_api_key

            api_key_input = self.query_one("#api-key-input", Input)
            api_key = api_key_input.value.strip()

            if not api_key:
                self.app.notify("API key cannot be empty", severity="error")
                return

            if not api_key.startswith("sk-"):
                self.app.notify("Invalid API key format", severity="error")
                return

            # Save API key
            if set_api_key(self.env, api_key):
                self.app.notify("Settings saved!", severity="information")
                self.app.pop_screen()
            else:
                self.app.notify("Failed to save settings", severity="error")

    def action_back(self) -> None:
        """Go back to dashboard."""
        self.app.pop_screen()


class MenuListItem(ListItem):
    """Single menu item in the dashboard."""

    def __init__(self, menu_id: str, label: str):
        super().__init__()
        self.menu_id = menu_id
        self.menu_label = label

    def compose(self) -> ComposeResult:
        yield Label(self.menu_label)


class DashboardScreen(Screen):
    """Main dashboard screen with menu options."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "select", "Select"),
    ]

    def __init__(self, env):
        super().__init__()
        self.env = env
        self.latest_version = None

    def compose(self) -> ComposeResult:
        yield Static("Soomgo Agent", id="header")
        yield ListView(id="menu-list")
        yield Static("Enter: select  |  q: quit", id="footer")

    def on_mount(self) -> None:
        """Load menu items on mount."""
        self.check_for_updates()
        self.load_menu()

    def check_for_updates(self) -> None:
        """Check for available updates from GitHub."""
        try:
            import requests
            from packaging import version as pkg_version

            current_version = "0.1.0"  # TODO: Get from package metadata

            # Check GitHub API for latest release
            response = requests.get(
                "https://api.github.com/repos/jungeol66104/soomgo-agent/releases/latest",
                timeout=3
            )

            if response.status_code == 200:
                latest = response.json()["tag_name"].lstrip("v")
                if pkg_version.parse(latest) > pkg_version.parse(current_version):
                    self.latest_version = latest
        except Exception:
            # Silently fail - don't block if update check fails
            pass

    def load_menu(self) -> None:
        """Load menu items."""
        list_view = self.query_one("#menu-list", ListView)

        # Show update option if available (in yellow)
        if self.latest_version:
            list_view.append(MenuListItem("update", f"[yellow]Update available: v{self.latest_version} - Update Now[/yellow]"))
            list_view.append(MenuListItem("separator", ""))

        # Add menu items
        list_view.append(MenuListItem("run", "Run (coming soon)"))
        list_view.append(MenuListItem("stop", "Stop (coming soon)"))
        list_view.append(MenuListItem("status", "Status (coming soon)"))
        list_view.append(MenuListItem("separator2", ""))
        list_view.append(MenuListItem("settings", "Settings"))
        list_view.append(MenuListItem("chats", "Chats"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle menu selection."""
        menu_item = event.item
        if isinstance(menu_item, MenuListItem):
            if menu_item.menu_id == "update":
                self.perform_update()
            elif menu_item.menu_id == "settings":
                self.app.push_screen(SettingsScreen(self.env))
            elif menu_item.menu_id == "chats":
                self.app.push_screen(ChatListScreen(self.env))
            elif menu_item.menu_id == "run":
                self.app.notify("Coming soon: Start daemon", severity="information")
            elif menu_item.menu_id == "stop":
                self.app.notify("Coming soon: Stop daemon", severity="information")
            elif menu_item.menu_id == "status":
                self.app.notify("Coming soon: Show status", severity="information")
            elif menu_item.menu_id in ["separator", "separator2"]:
                # Separator - do nothing
                pass

    def perform_update(self) -> None:
        """Perform update using uv."""
        import subprocess

        self.app.notify("Updating Soomgo Agent...", severity="information")

        try:
            # Run uv tool upgrade
            result = subprocess.run(
                ["uv", "tool", "upgrade", "soomgo-agent"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.app.notify(f"Updated to v{self.latest_version}! Please restart.", severity="information")
            else:
                self.app.notify("Update failed. Please try manually: uv tool upgrade soomgo-agent", severity="error")
        except Exception as e:
            self.app.notify(f"Update error: {str(e)}", severity="error")


class ChatListItem(ListItem):
    """Single chat item in the list."""

    def __init__(self, chat_id: int, service: str, status: str):
        super().__init__()
        self.chat_id = chat_id
        self.service = service
        self.status = status

    def compose(self) -> ComposeResult:
        yield Label(f"Chat #{self.chat_id} - {self.service}")


class MessageView(Static):
    """Display a single message."""

    def __init__(self, sender_name: str, content: str):
        super().__init__()
        # Wrap long lines in the content
        wrapped_content = wrap_message_text(content, width=75)

        # Build the full message as a single string
        lines = wrapped_content.split('\n')
        message_lines = [f"║  {line}" for line in lines]

        full_message = f"╔═ {sender_name}\n" + "\n".join(message_lines) + f"\n╚{'═' * 79}\n"
        self.message_text = full_message

    def compose(self) -> ComposeResult:
        yield Label(self.message_text)


class SimulationListItem(ListItem):
    """Single simulation run item."""

    def __init__(self, run_id: str, status: str, progress: float = 0.0, turns: str = "", timestamp: str = ""):
        super().__init__()
        self.run_id = run_id
        self.status = status
        self.progress = progress
        self.turns = turns
        self.timestamp = timestamp

    def compose(self) -> ComposeResult:
        if self.status == "running":
            # Show progress bar
            bar_width = 20
            filled = int(bar_width * self.progress)
            bar = "▓" * filled + "░" * (bar_width - filled)
            yield Label(f"{self.run_id}  {bar} {self.turns}")
        else:
            # Completed run
            yield Label(f"{self.run_id}  {self.turns}  |  {self.timestamp}")


class SimulationListScreen(Screen):
    """Screen showing simulation runs for a chat."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("b", "back", "Back"),
        Binding("q", "quit", "Quit"),
        Binding("enter", "select", "Select"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, chat_id: int, env):
        super().__init__()
        self.chat_id = chat_id
        self.env = env
        self.auto_refresh_interval = 2.0  # seconds

    def compose(self) -> ComposeResult:
        yield Static(f"Simulations - Chat #{self.chat_id}", id="header")
        yield ListView(id="simulation-list")
        yield Static("Enter: select  |  r: refresh  |  Esc/b: back  |  q: quit", id="footer")

    def on_mount(self) -> None:
        """Load simulations and set up auto-refresh."""
        self.load_simulations()
        self.set_interval(self.auto_refresh_interval, self.refresh_simulations)

    def refresh_simulations(self) -> None:
        """Refresh simulation list (for auto-update)."""
        self.load_simulations()

    def action_refresh(self) -> None:
        """Manually refresh simulation list."""
        self.load_simulations()

    def load_simulations(self) -> None:
        """Load simulation runs from storage."""
        list_view = self.query_one("#simulation-list", ListView)

        # Clear existing items
        list_view.clear()

        # Add "Run New Simulation" option
        list_view.append(MenuListItem("new_simulation", "► Run New Simulation"))

        # Load actual simulation runs
        simulations_dir = self.env.data_dir / "simulations"
        runner = SimulationRunner(self.env.messages_dir, simulations_dir)

        run_ids = runner.list_chat_runs(self.chat_id)

        for run_id in run_ids:
            summary = runner.get_run_summary(self.chat_id, run_id)
            if not summary:
                continue

            status = summary["status"]

            if status == "running":
                # Running simulation with progress bar
                list_view.append(SimulationListItem(
                    run_id=run_id,
                    status="running",
                    progress=summary["progress"],
                    turns=summary["progress_text"]
                ))
            else:
                # Completed simulation
                duration = summary.get("duration_seconds", 0)
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

                turns_str = f"{summary['total_simulated_responses']} turns, {duration_str}"

                # Calculate relative timestamp
                completed_at = summary.get("completed_at")
                if completed_at:
                    time_diff = datetime.now() - completed_at
                    hours = int(time_diff.total_seconds() // 3600)
                    if hours > 24:
                        days = hours // 24
                        timestamp_str = f"{days}d ago"
                    elif hours > 0:
                        timestamp_str = f"{hours}h ago"
                    else:
                        minutes = int(time_diff.total_seconds() // 60)
                        timestamp_str = f"{minutes}m ago" if minutes > 0 else "just now"
                else:
                    timestamp_str = ""

                list_view.append(SimulationListItem(
                    run_id=run_id,
                    status=status,
                    turns=turns_str,
                    timestamp=timestamp_str
                ))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle simulation selection."""
        item = event.item

        if isinstance(item, MenuListItem) and item.menu_id == "new_simulation":
            # Start new simulation
            self.start_new_simulation()
        elif isinstance(item, SimulationListItem):
            if item.status == "completed":
                # Open results view
                self.app.push_screen(SimulationResultScreen(self.chat_id, item.run_id, self.env))

    def start_new_simulation(self) -> None:
        """Start a new simulation run in background."""
        import threading
        import sys
        import io

        simulations_dir = self.env.data_dir / "simulations"
        runner = SimulationRunner(self.env.messages_dir, simulations_dir)

        def run_in_thread():
            # Suppress all logging output during simulation
            import logging
            logging.getLogger().setLevel(logging.CRITICAL)

            # Suppress loguru logs completely
            from loguru import logger
            logger.remove()  # Remove all handlers
            logger.add(sys.stderr, level="WARNING")  # Only show warnings/errors

            # Redirect stdout/stderr to suppress prints
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()

            try:
                # Initialize agent (logs suppressed)
                from src.agent.core import SoomgoAgent
                agent = SoomgoAgent()

                # Run simulation with agent
                runner.run_simulation(self.chat_id, agent=agent)

            except Exception as e:
                # Restore output for error reporting
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                print(f"Simulation error: {e}")
            finally:
                # Restore output
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        # Start simulation in background
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

        # Stay on this screen (don't pop back)
        # User can manually go back when ready

    def action_back(self) -> None:
        """Go back to chat detail."""
        self.app.pop_screen()


class SimulationResultScreen(Screen):
    """Screen showing simulation results (comparison view)."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("b", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, chat_id: int, run_id: str, env):
        super().__init__()
        self.chat_id = chat_id
        self.run_id = run_id
        self.env = env

    def compose(self) -> ComposeResult:
        yield Static(f"Simulation Results - {self.run_id}", id="header")
        yield VerticalScroll(id="results-container")
        yield Static("Esc/b: back  |  q: quit", id="footer")

    def on_mount(self) -> None:
        """Load and display simulation results."""
        self.load_results()
        # Scroll to top to show simulated messages
        container = self.query_one("#results-container")
        container.scroll_home()

    def load_results(self) -> None:
        """Load simulation results and display as unified chat timeline."""
        container = self.query_one("#results-container")

        # Load simulation run
        simulations_dir = self.env.data_dir / "simulations"
        runner = SimulationRunner(self.env.messages_dir, simulations_dir)

        simulation_run = runner.get_run(self.chat_id, self.run_id)
        if not simulation_run:
            container.mount(Label("Error: Simulation not found"))
            return

        # Add info header with markup colors
        header_markup = (
            f"[bold cyan]Simulation Results:[/bold cyan] "
            f"{simulation_run.metadata.total_simulated_responses} simulated responses shown in [cyan]CYAN[/cyan]"
        )
        # Static widget supports markup directly
        container.mount(Static(header_markup))
        container.mount(Label("=" * 80))
        container.mount(Label(""))

        # Load original messages
        message_db = MessageCentralDB(str(self.env.messages_dir))
        messages_dict = message_db.load_chat_messages(self.chat_id)
        original_messages = sorted(messages_dict.values(), key=lambda m: m.id)

        # Reconstruct message groups to find insertion points
        from src.simulation.grouper import (
            find_start_trigger,
            find_end_trigger,
            group_customer_messages
        )

        start_idx = find_start_trigger(original_messages)
        if start_idx is None:
            container.mount(Label("Error: Start trigger not found"))
            return

        end_idx, _ = find_end_trigger(original_messages, start_idx)

        groups = group_customer_messages(
            original_messages,
            start_idx,
            end_idx,
            simulation_run.metadata.time_window_seconds
        )

        # Build insertion map: after which message index to insert simulated response
        insertion_map = {}
        for group, simulated_msg in zip(groups, simulation_run.simulated_messages):
            insertion_map[group.last_message_index] = simulated_msg

        # Display messages with simulated responses inserted
        for idx, msg in enumerate(original_messages):
            # Determine sender name
            if msg.user.id == 0:
                sender_name = "시스템"
            elif msg.user.provider and msg.user.provider.id is not None:
                sender_name = "정코치"
            else:
                sender_name = msg.user.name

            # Display original message (with wrapping)
            wrapped_content = wrap_message_text(msg.message, width=75)
            lines = wrapped_content.split('\n')
            message_lines = [f"║  {line}" for line in lines]
            full_message = f"╔═ {sender_name}\n" + "\n".join(message_lines) + f"\n╚{'═' * 79}\n"
            container.mount(Label(full_message))

            # Insert simulated response after this message if applicable
            if idx in insertion_map:
                simulated_msg = insertion_map[idx]
                # Wrap simulated message content
                wrapped_sim_content = wrap_message_text(simulated_msg.message, width=75)
                sim_lines = wrapped_sim_content.split('\n')
                sim_message_lines = [f"║  {line}" for line in sim_lines]

                # Use cyan color for simulated messages
                # Each line needs to be wrapped in [cyan] tags
                sim_message_lines_colored = [f"[cyan]{line}[/cyan]" for line in sim_message_lines]

                sim_full_message = (
                    "[cyan]╔═ 정코치 [SIMULATED][/cyan]\n" +
                    "\n".join(sim_message_lines_colored) +
                    f"\n[cyan]╚{'═' * 79}[/cyan]"
                )

                # Static widget supports markup directly (markup=True by default)
                container.mount(Static(sim_full_message))

    def action_back(self) -> None:
        """Go back to simulation list."""
        self.app.pop_screen()


class ChatDetailScreen(Screen):
    """Screen showing chat messages."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("b", "back", "Back"),
        Binding("q", "quit", "Quit"),
        Binding("s", "simulations", "Simulations"),
    ]

    def __init__(self, chat_id: int, messages_dir: str, env):
        super().__init__()
        self.chat_id = chat_id
        self.messages_dir = Path(messages_dir)
        self.env = env

    def compose(self) -> ComposeResult:
        yield Static(f"Chat #{self.chat_id}", id="header")
        yield VerticalScroll(id="messages-container")
        yield Static("s: simulations  |  Esc/b: back  |  q: quit", id="footer")

    def on_mount(self) -> None:
        """Load and display messages."""
        self.load_messages()

    def load_messages(self) -> None:
        """Load messages from file."""
        message_db = MessageCentralDB(str(self.messages_dir))
        messages = message_db.load_chat_messages(self.chat_id)

        container = self.query_one("#messages-container")

        if not messages:
            container.mount(Label("No messages found"))
            return

        # Sort by ID and display
        sorted_messages = sorted(messages.values(), key=lambda m: m.id)

        for msg in sorted_messages:
            # Determine sender name:
            # - user.id == 0: system message -> "시스템"
            # - user.provider.id != None: provider -> "정코치"
            # - else: customer -> use user.name
            if msg.user.id == 0:
                sender_name = "시스템"
            elif msg.user.provider and msg.user.provider.id is not None:
                # Provider message - use simple name
                sender_name = "정코치"
            else:
                # Customer message - use actual customer name
                sender_name = msg.user.name

            container.mount(MessageView(sender_name, msg.message))

    def action_back(self) -> None:
        """Go back to chat list."""
        self.app.pop_screen()

    def action_simulations(self) -> None:
        """Open simulations screen."""
        self.app.push_screen(SimulationListScreen(self.chat_id, self.env))


class ChatListScreen(Screen):
    """Screen showing list of all chats."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("b", "back", "Back"),
        Binding("q", "quit", "Quit"),
        Binding("enter", "select", "View Chat"),
    ]

    def __init__(self, env):
        super().__init__()
        self.env = env

    def compose(self) -> ComposeResult:
        yield Static("Chats", id="header")
        yield ListView(id="chat-list")
        yield Static("Enter: view  |  Esc/b: back  |  q: quit", id="footer")

    def on_mount(self) -> None:
        """Load chats on mount."""
        self.load_chats()

    def load_chats(self) -> None:
        """Load all chats from database."""
        db_path = self.env.data_dir / "chat_list_master.jsonl"
        db = CentralChatDatabase(str(db_path))
        chats = db.load()

        list_view = self.query_one("#chat-list", ListView)

        # Filter for hired chats only (using quote.is_hired)
        all_chats = list(chats.values())
        hired_chats = [c for c in all_chats if c.quote and c.quote.is_hired]

        # Sort by updated_at descending (most recent first)
        hired_chats.sort(key=lambda c: c.updated_at, reverse=True)

        for chat in hired_chats:
            # Format: name | address | service title
            address = f"{chat.request.address.address1} {chat.request.address.address2}"
            display_text = f"{chat.user.name} | {address} | {chat.service.title}"

            list_view.append(ChatListItem(
                chat.id,
                display_text,
                "hired"
            ))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle chat selection."""
        chat_item = event.item
        if isinstance(chat_item, ChatListItem):
            # Push chat detail screen
            self.app.push_screen(ChatDetailScreen(
                chat_item.chat_id,
                str(self.env.messages_dir),
                self.env
            ))

    def action_back(self) -> None:
        """Go back to dashboard."""
        self.app.pop_screen()


class ChatViewerApp(App):
    """Chat viewer TUI application."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, env):
        super().__init__()
        self.env = env

    def on_mount(self) -> None:
        """Show setup or dashboard on startup."""
        # Check if configured
        if not is_configured(self.env):
            # First run - show setup
            self.push_screen(SetupScreen(self.env), callback=self.on_setup_complete)
        else:
            # Already configured - show dashboard
            self.push_screen(DashboardScreen(self.env))

    def on_setup_complete(self, success: bool) -> None:
        """Called after setup is complete."""
        if success:
            # Setup successful - show dashboard
            self.push_screen(DashboardScreen(self.env))


def run_chat_viewer(env):
    """Run the chat viewer TUI."""
    app = ChatViewerApp(env)
    app.run()
