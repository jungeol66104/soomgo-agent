"""Daemon management for Soomgo agent."""

import os
import signal
import sys
import time
from pathlib import Path

import psutil
from rich.console import Console

console = Console()


def start_daemon(env, shadow=False):
    """Start the agent daemon in background."""
    # Check if daemon is already running
    if is_running(env):
        console.print("[yellow]Daemon is already running![/yellow]")
        console.print(f"[dim]PID file: {env.pid_file}[/dim]")
        return

    # TODO: Implement actual daemon logic
    console.print("[yellow]Daemon not yet implemented[/yellow]")
    console.print("[dim]Coming soon: Background monitoring and auto-response[/dim]")


def stop_daemon(env):
    """Stop the running daemon."""
    if not env.pid_file.exists():
        console.print("[yellow]No daemon is running[/yellow]")
        return

    try:
        with open(env.pid_file) as f:
            pid = int(f.read().strip())

        # Check if process exists
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=5)
            console.print(f"[green]✓ Daemon stopped (PID: {pid})[/green]")
        except psutil.NoSuchProcess:
            console.print("[yellow]Daemon was not running (stale PID file)[/yellow]")
        except psutil.TimeoutExpired:
            # Force kill if it doesn't stop
            process.kill()
            console.print(f"[yellow]Daemon force-killed (PID: {pid})[/yellow]")

        # Remove PID file
        env.pid_file.unlink()

    except Exception as e:
        console.print(f"[red]Error stopping daemon: {e}[/red]")


def is_running(env) -> bool:
    """Check if daemon is running."""
    if not env.pid_file.exists():
        return False

    try:
        with open(env.pid_file) as f:
            pid = int(f.read().strip())
        # Check if process exists
        return psutil.pid_exists(pid)
    except:
        return False


def show_status(env):
    """Show daemon status and statistics."""
    running = is_running(env)

    console.print(f"\n[bold]Soomgo Agent Status[/bold] [dim]({env.env_type} mode)[/dim]\n")

    if running:
        with open(env.pid_file) as f:
            pid = int(f.read().strip())
        try:
            process = psutil.Process(pid)
            uptime = time.time() - process.create_time()
            uptime_str = format_uptime(uptime)

            console.print(f"  Status: [bold green]● Running[/bold green]")
            console.print(f"  PID: {pid}")
            console.print(f"  Uptime: {uptime_str}")
            console.print(f"  Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
        except:
            console.print(f"  Status: [bold yellow]● Unknown[/bold yellow]")
    else:
        console.print(f"  Status: [bold red]● Stopped[/bold red]")

    console.print(f"\n  [bold]Paths:[/bold]")
    console.print(f"  Base:     {env.base_dir}")
    console.print(f"  Data:     {env.data_dir}")
    console.print(f"  Messages: {env.messages_dir}")
    console.print(f"  Shadow:   {env.shadow_dir}")
    console.print(f"  DB:       {env.db_dir}")
    console.print(f"  Logs:     {env.logs_dir}")
    console.print(f"  Config:   {env.config_file}")
    console.print()


def show_logs(env, follow=False, lines=50):
    """View daemon logs."""
    log_file = env.logs_dir / "daemon.log"

    if not log_file.exists():
        console.print("[yellow]No logs found[/yellow]")
        return

    if follow:
        # Follow logs (tail -f equivalent)
        console.print(f"[dim]Following logs from {log_file}...[/dim]\n")
        try:
            with open(log_file) as f:
                # Go to end of file
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        print(line, end='')
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped following logs[/dim]")
    else:
        # Show last N lines
        with open(log_file) as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
            for line in last_lines:
                print(line, end='')


def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
