#!/usr/bin/env python3
"""Main CLI entry point for Soomgo agent."""

import os
import sys
from pathlib import Path
from typing import Literal

import click
from rich.console import Console

console = Console()

# Environment type
ENV_TYPE = Literal["dev", "prod"]


class Environment:
    """Environment configuration for dev vs prod."""

    def __init__(self, env_type: ENV_TYPE):
        self.env_type = env_type
        self.home = Path.home()

        # Set base directory based on environment
        if env_type == "dev":
            # Dev: Use project directory
            # Get project root (vf-data directory)
            project_root = Path(__file__).parent.parent.parent
            self.base_dir = project_root
            self.data_dir = project_root / "data"
            self.logs_dir = project_root / "logs"
            self.db_dir = project_root / "db"
            self.config_dir = project_root / "config"
        else:
            # Prod: Use home directory
            self.base_dir = self.home / ".soomgo"
            self.data_dir = self.base_dir / "data"
            self.logs_dir = self.base_dir / "logs"
            self.db_dir = self.base_dir / "db"
            self.config_dir = self.base_dir / "config"

        # Data subdirectories
        self.sessions_dir = self.data_dir / "sessions"
        self.messages_dir = self.data_dir / "messages"
        self.shadow_dir = self.data_dir / "shadow"
        self.prompts_dir = self.data_dir / "prompts"
        self.knowledge_dir = self.data_dir / "knowledge"

        # Config files
        self.config_file = self.config_dir / "config.yaml"
        self.pid_file = self.base_dir / "daemon.pid"

        # DB files
        self.chat_db = self.db_dir / "chats.db"
        self.response_db = self.db_dir / "responses.db"

        # Ensure all directories exist
        self._init_directories()

    def _init_directories(self):
        """Create all necessary directories."""
        # In dev mode, most directories should already exist in project
        # In prod mode, create everything
        for directory in [
            self.config_dir,
            self.logs_dir,
            self.db_dir,
            self.sessions_dir,
            self.messages_dir,
            self.shadow_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def __repr__(self):
        return f"Environment(type={self.env_type}, base={self.base_dir})"


# Global environment instance (will be set by CLI)
env: Environment = None


def set_environment(env_type: ENV_TYPE):
    """Set global environment."""
    global env
    env = Environment(env_type)
    # Set environment variable for other modules to access
    os.environ["SOOMGO_ENV"] = env_type
    os.environ["SOOMGO_BASE_DIR"] = str(env.base_dir)


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0")
def dev_cli(ctx):
    """Soomgo Agent - Development Mode"""
    set_environment("dev")

    # If no subcommand provided, launch TUI
    if ctx.invoked_subcommand is None:
        from .tui import run_chat_viewer
        run_chat_viewer(env)


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0")
def prod_cli(ctx):
    """Soomgo Agent - Production Mode"""
    set_environment("prod")

    # If no subcommand provided, launch TUI
    if ctx.invoked_subcommand is None:
        from .tui import run_chat_viewer
        run_chat_viewer(env)


# Run command (start daemon)
@dev_cli.command()
@click.option("--shadow", is_flag=True, help="Run in shadow mode (no real messages sent)")
def run(shadow):
    """Start the agent daemon."""
    from .daemon import start_daemon

    console.print(f"[bold green]Starting daemon ({env.env_type} mode)...[/bold green]")
    if shadow:
        console.print("[yellow]Shadow mode: Messages will NOT be sent[/yellow]")

    start_daemon(env, shadow=shadow)


@prod_cli.command()
@click.option("--shadow", is_flag=True, help="Run in shadow mode (no real messages sent)")
def run(shadow):
    """Start the agent daemon."""
    from .daemon import start_daemon

    console.print(f"[bold green]Starting daemon ({env.env_type} mode)...[/bold green]")
    if shadow:
        console.print("[yellow]Shadow mode: Messages will NOT be sent[/yellow]")

    start_daemon(env, shadow=shadow)


# Stop command
@dev_cli.command()
def stop():
    """Stop the agent daemon."""
    from .daemon import stop_daemon

    console.print(f"[bold yellow]Stopping daemon ({env.env_type} mode)...[/bold yellow]")
    stop_daemon(env)


@prod_cli.command()
def stop():
    """Stop the agent daemon."""
    from .daemon import stop_daemon

    console.print(f"[bold yellow]Stopping daemon ({env.env_type} mode)...[/bold yellow]")
    stop_daemon(env)


# Status command
@dev_cli.command()
def status():
    """Show daemon status and statistics."""
    from .daemon import show_status

    show_status(env)


@prod_cli.command()
def status():
    """Show daemon status and statistics."""
    from .daemon import show_status

    show_status(env)


# Logs command
@dev_cli.command()
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
def logs(follow, lines):
    """View daemon logs."""
    from .daemon import show_logs

    show_logs(env, follow=follow, lines=lines)


@prod_cli.command()
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
def logs(follow, lines):
    """View daemon logs."""
    from .daemon import show_logs

    show_logs(env, follow=follow, lines=lines)


# Interactive chat command (for manual testing)
@dev_cli.command()
def chat():
    """Start interactive chat session (for testing)."""
    console.print(f"[bold cyan]Starting interactive chat ({env.env_type} mode)[/bold cyan]\n")

    # Import and run agent REPL
    from . import agent_repl
    sys.exit(agent_repl.main())


@prod_cli.command()
def chat():
    """Start interactive chat session."""
    console.print(f"[bold cyan]Starting interactive chat ({env.env_type} mode)[/bold cyan]\n")

    # Import and run agent REPL
    from . import agent_repl
    sys.exit(agent_repl.main())


if __name__ == "__main__":
    # This should not be called directly
    console.print("[red]Error: Use 'soomgo-dev' or 'soomgo' commands instead[/red]")
    sys.exit(1)
