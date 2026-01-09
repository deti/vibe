"""CLI command to invoke Claude Code headless with a prompt file."""

import json
from pathlib import Path

import click
import yaml

from vibe.checks import run_checks_with_retry
from vibe.cli.utils import error, fatal, info, warning
from vibe.project_config import ProjectConfig, load_project_config
from vibe.providers.claude import (
    ClaudeCommandError,
    ClaudeCommandNotFoundError,
    ClaudeJSONParseError,
)
from vibe.providers.claude import (
    invoke as invoke_claude,
)


def _load_config() -> ProjectConfig | None:
    """Load project configuration and handle errors."""
    try:
        project_config = load_project_config()
    except yaml.YAMLError as e:
        fatal(f"Invalid YAML in configuration file: {e}")
    except ValueError as e:
        fatal(f"Invalid configuration: {e}")
    except Exception as e:
        fatal(f"Error loading project configuration: {e}")
    else:
        if project_config is None:
            info("No project configuration found (.vibe/vibe.yaml), skipping checks")
        elif project_config.checks:
            info(
                f"Loaded project configuration with {len(project_config.checks.steps)} check(s)"
            )
        return project_config


def _find_system_prompt_file() -> Path | None:
    """Find system prompt file in .vibe folder (case-insensitive).

    Looks for vibe.md or VIBE.md in the .vibe folder relative to current working directory.

    Returns:
        Path to system prompt file if found, None otherwise.
    """
    vibe_dir = Path.cwd() / ".vibe"
    if not vibe_dir.exists():
        return None

    # Case-insensitive search for vibe.md
    for file in vibe_dir.iterdir():
        if file.is_file() and file.name.lower() == "vibe.md":
            return file

    return None


def _read_prompt(prompt_file: Path) -> str:
    """Read and validate prompt from file."""
    try:
        content = prompt_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        fatal(f"Prompt file not found: {prompt_file}")
    except Exception as e:
        fatal(f"Reading prompt file failed: {e}")
    else:
        if not content:
            fatal("Prompt file is empty")
        return content


def _invoke_claude_with_reporting(
    prompt_content: str, system_prompt_file: Path | None = None
) -> dict:
    """Invoke Claude and handle reporting/errors."""
    info(f"Running Claude with prompt:\n-------\n{prompt_content}\n-------")

    if system_prompt_file:
        info(f"Using system prompt file: {system_prompt_file}")

    try:
        output_data = invoke_claude(
            prompt_content, system_prompt_file=system_prompt_file
        )
    except ClaudeCommandNotFoundError as e:
        fatal(str(e))
    except ClaudeCommandError as e:
        if e.stderr:
            error(f"Error output: {e.stderr}")
        fatal(str(e))
    except ClaudeJSONParseError as e:
        error(f"Raw output: {e.raw_output}")
        fatal(str(e))
    else:
        # Display parsed output
        info("---- unparsed Claude output ----")
        info(json.dumps(output_data, indent=2))
        info("--------------------------------")
        info(
            f"Claude output parsed successfully. "
            f"{len(output_data)} keys found in JSON output."
        )

        session_id = output_data.get("session_id")
        result_text = output_data.get("result", "")

        if session_id:
            info(f"Session ID: {session_id}")

        if result_text:
            info(result_text)

        return output_data


def _run_project_checks(project_config: ProjectConfig | None) -> None:
    """Run configured project checks."""
    if not (project_config and project_config.checks):
        return

    try:
        info("Running configured checks...")
        check_results = run_checks_with_retry(project_config.checks)

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


@click.command()
@click.argument("prompt_file", type=click.Path(exists=True, path_type=Path))
def main(prompt_file: Path) -> None:
    """Invoke Claude Code headless with a prompt from a file.

    Reads the prompt from PROMPT_FILE, invokes claude with the prompt,
    and prints the session ID and result.
    """
    project_config = _load_config()
    info(f"project_config: {project_config}")
    prompt_content = _read_prompt(prompt_file)
    system_prompt_file = _find_system_prompt_file()
    _invoke_claude_with_reporting(prompt_content, system_prompt_file=system_prompt_file)
    _run_project_checks(project_config)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
