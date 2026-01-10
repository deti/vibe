"""Claude provider implementation for invoking Claude CLI."""

import json
import subprocess
from typing import Any


class ClaudeError(Exception):
    """Base exception for Claude provider errors."""


class ClaudeCommandNotFoundError(ClaudeError):
    """Raised when the claude command is not found."""

    def __init__(self, message: str | None = None):
        if message is None:
            message = (
                "'claude' command not found. Please ensure Claude Code is installed."
            )
        super().__init__(message)


class ClaudeCommandError(ClaudeError):
    """Raised when the claude command fails."""

    def __init__(self, returncode: int, stderr: str | None = None):
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Claude command failed with exit code {returncode}")


class ClaudeJSONParseError(ClaudeError):
    """Raised when Claude output cannot be parsed as JSON."""

    def __init__(self, error: json.JSONDecodeError, raw_output: str):
        self.error = error
        self.raw_output = raw_output
        super().__init__(f"Failed to parse Claude output as JSON: {error}")


def invoke(prompt: str) -> dict[str, Any]:
    """Invoke Claude CLI with the given prompt and return parsed JSON output.

    Args:
        prompt: The prompt text to send to Claude.

    Returns:
        A dictionary containing the parsed JSON output from Claude, typically
        with keys like 'session_id' and 'result'.

    Raises:
        ClaudeCommandNotFoundError: If the 'claude' command is not found.
        ClaudeCommandError: If the claude command fails.
        ClaudeJSONParseError: If the output cannot be parsed as JSON.
    """
    command = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--allowedTools",
        "'Bash,Read,Edit'",
        "--dangerously-skip-permissions",
    ]

    # Invoke claude command
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as e:
        raise ClaudeCommandNotFoundError from e
    except subprocess.CalledProcessError as e:
        raise ClaudeCommandError(returncode=e.returncode, stderr=e.stderr) from e

    # Parse JSON output
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ClaudeJSONParseError(error=e, raw_output=result.stdout) from e
