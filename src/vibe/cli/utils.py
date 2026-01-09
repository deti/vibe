"""CLI utility functions."""

import sys
from pathlib import Path
from typing import NoReturn

from rich.console import Console


class NotInGitRepositoryError(FileNotFoundError):
    """Raised when not in a git repository."""

    def __init__(self) -> None:
        super().__init__("Not in a git repository")


# Global console instance
console = Console()
error_console = Console(stderr=True)


def success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]SUCCESS:[/green] {message}")


def info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]INFO:[/blue] {message}")


def warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]WARNING:[/yellow] {message}")


def error(message: str) -> None:
    """Print an error message."""
    error_console.print(f"[red]ERROR:[/red] {message}")


def fatal(message: str, exit_code: int = 1) -> NoReturn:
    """Print an error and exit."""
    error(message)
    sys.exit(exit_code)


def find_project_root(start: Path | None = None) -> Path:
    """Find the project root (directory containing .git).

    Args:
        start: Starting directory (defaults to cwd).

    Returns:
        Project root path.

    Raises:
        NotInGitRepositoryError: If not in a git repository.
    """
    current = start or Path.cwd()

    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    raise NotInGitRepositoryError
