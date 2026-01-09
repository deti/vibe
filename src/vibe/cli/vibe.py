"""CLI command to invoke Claude Code headless with a prompt file."""

import json
import sys
from pathlib import Path

import click

from vibe.cli.utils import error, info
from vibe.providers.claude import (
    ClaudeCommandError,
    ClaudeCommandNotFoundError,
    ClaudeJSONParseError,
)
from vibe.providers.claude import (
    invoke as invoke_claude,
)


@click.command()
@click.argument("prompt_file", type=click.Path(exists=True, path_type=Path))
def main(prompt_file: Path) -> None:
    """Invoke Claude Code headless with a prompt from a file.

    Reads the prompt from PROMPT_FILE, invokes claude with the prompt,
    and prints the session ID and result.
    """
    # Read prompt from file
    try:
        prompt_content = prompt_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        error(f"Error: Prompt file not found: {prompt_file}")
        sys.exit(1)
    except Exception as e:
        error(f"Error reading prompt file: {e}")
        sys.exit(1)

    if not prompt_content:
        error("Error: Prompt file is empty")
        sys.exit(1)

    info(f"Running Claude with prompt:\n-------\n{prompt_content}\n-------")

    # Invoke claude command
    try:
        output_data = invoke_claude(prompt_content)
    except ClaudeCommandNotFoundError as e:
        error(f"Error: {e}")
        sys.exit(1)
    except ClaudeCommandError as e:
        error(f"Error: {e}")
        if e.stderr:
            error(f"Error output: {e.stderr}")
        sys.exit(1)
    except ClaudeJSONParseError as e:
        error(f"Error: {e}")
        error(f"Raw output: {e.raw_output}")
        sys.exit(1)

    # Display parsed output
    info("---- unparsed Claude output ----")
    info(json.dumps(output_data, indent=2))
    info("--------------------------------")
    info(
        f"Claude output parsed successfully. "
        f"{len(output_data)} keys found in JSON output."
    )

    # Extract session_id and result
    session_id = output_data.get("session_id")
    result_text = output_data.get("result", "")

    if session_id:
        info(f"Session ID: {session_id}")

    if result_text:
        info(result_text)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
