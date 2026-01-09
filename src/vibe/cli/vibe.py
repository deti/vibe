"""CLI command to invoke Claude Code headless with a prompt file."""

import json
import sys
from pathlib import Path

import click
import yaml

from vibe.checks import run_checks_with_retry
from vibe.cli.utils import error, info, warning
from vibe.project_config import load_project_config
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
    # 1. Load project config
    try:
        project_config = load_project_config()
        if project_config is None:
            info("No project configuration found (.vibe/vibe.yaml), skipping checks")
        elif project_config.checks:
            info(
                f"Loaded project configuration with {len(project_config.checks.steps)} check(s)"
            )
    except yaml.YAMLError as e:
        error(f"Invalid YAML in configuration file: {e}")
        sys.exit(1)
    except ValueError as e:
        error(f"Invalid configuration: {e}")
        sys.exit(1)
    except Exception as e:
        error(f"Error loading project configuration: {e}")
        sys.exit(1)

    # 2. Load prompt from file
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

    # 3. Run prompt
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

    # 4. Loop checks until they all pass
    if project_config and project_config.checks:
        try:
            info("Running configured checks...")
            check_results = run_checks_with_retry(project_config.checks, prompt_content)

            # Report final check status
            passed = [r for r in check_results if r.success]
            failed = [r for r in check_results if not r.success]

            if passed:
                info(f"Passed checks: {len(passed)}/{len(check_results)}")
            if failed:
                warning(f"Failed checks: {len(failed)}/{len(check_results)}")
                for result in failed:
                    error(f"  - {result.step_name}")
                    if result.error:
                        error(f"    Error: {result.error}")
        except Exception as e:
            error(f"Error running checks: {e}")
            warning("Continuing despite check errors")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
