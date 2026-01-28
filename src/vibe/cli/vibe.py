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


def _get_state_file_path() -> Path:
    """Get the path to the state file."""
    return Path.cwd() / ".vibe" / "state.json"


def _load_state() -> dict[str, list[str]]:
    """Load state from .vibe/state.json.

    Returns:
        Dictionary mapping directory paths (as strings) to lists of completed filenames.
        Returns empty dict if state file doesn't exist or is invalid.
    """
    state_path = _get_state_file_path()
    if not state_path.exists():
        return {}

    try:
        with state_path.open(encoding="utf-8") as f:
            state = json.load(f)
            # Validate structure
            if isinstance(state, dict):
                return state
            return {}
    except (json.JSONDecodeError, Exception) as e:
        warning(f"Failed to load state file: {e}. Starting fresh.")
        return {}


def _save_state(state: dict[str, list[str]]) -> None:
    """Save state to .vibe/state.json.

    Args:
        state: Dictionary mapping directory paths to lists of completed filenames.
    """
    state_path = _get_state_file_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with state_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        error(f"Failed to save state file: {e}")


def _mark_complete(directory_path: Path, filename: str) -> None:
    """Mark a prompt file as complete in the state.

    Args:
        directory_path: The directory containing the prompt file.
        filename: The name of the completed prompt file.
    """
    state = _load_state()
    dir_key = str(directory_path.resolve())
    if dir_key not in state:
        state[dir_key] = []
    if filename not in state[dir_key]:
        state[dir_key].append(filename)
    _save_state(state)


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
    prompt_content: str, raise_on_error: bool = False
) -> dict:
    """Invoke Claude and handle reporting/errors.

    Args:
        prompt_content: The prompt to send to Claude.
        raise_on_error: If True, raise exceptions instead of calling fatal().
            Used for directory processing where errors should be caught.

    Returns:
        Dictionary containing Claude output.

    Raises:
        ClaudeCommandNotFoundError: If raise_on_error is True and Claude command not found.
        ClaudeCommandError: If raise_on_error is True and Claude command fails.
        ClaudeJSONParseError: If raise_on_error is True and JSON parsing fails.
    """
    info(f"Running Claude with prompt:\n-------\n{prompt_content}\n-------")

    try:
        output_data = invoke_claude(prompt_content)
    except ClaudeCommandNotFoundError as e:
        if raise_on_error:
            raise
        fatal(str(e))
    except ClaudeCommandError as e:
        if e.stderr:
            error(f"Error output: {e.stderr}")
        if raise_on_error:
            raise
        fatal(str(e))
    except ClaudeJSONParseError as e:
        error(f"Raw output: {e.raw_output}")
        if raise_on_error:
            raise
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


def _run_project_checks(project_config: ProjectConfig | None) -> bool:
    """Run configured project checks.

    Returns:
        True if all checks passed, False otherwise.
    """
    if not (project_config and project_config.checks):
        return True

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
        return len(failed) == 0
    except Exception as e:
        error(f"Error running checks: {e}")
        warning("Continuing despite check errors")
        return False


def _process_single_file(prompt_file: Path) -> bool:
    """Process a single prompt file.

    Args:
        prompt_file: Path to the prompt file.

    Returns:
        True if processing was successful (including checks), False otherwise.
    """
    project_config = _load_config()
    info(f"project_config: {project_config}")
    prompt_content = _read_prompt(prompt_file)
    _invoke_claude_with_reporting(prompt_content)
    return _run_project_checks(project_config)


def _process_directory(directory_path: Path) -> None:
    """Process all prompt files in a directory sequentially.

    Args:
        directory_path: Path to the directory containing prompt files.
    """
    # Find all .txt and .md files
    prompt_files = []
    for ext in [".txt", ".md"]:
        prompt_files.extend(directory_path.glob(f"*{ext}"))

    if not prompt_files:
        warning(f"No .txt or .md files found in directory: {directory_path}")
        return

    # Sort files ascending by filename
    prompt_files.sort(key=lambda p: p.name)

    info(f"Found {len(prompt_files)} prompt file(s) in directory")

    # Load state for this directory
    state = _load_state()
    dir_key = str(directory_path.resolve())
    completed_files = set(state.get(dir_key, []))

    # Filter out already completed files
    remaining_files = [f for f in prompt_files if f.name not in completed_files]

    if completed_files:
        info(f"Skipping {len(completed_files)} already completed file(s)")
    if not remaining_files:
        info("All prompt files in this directory have been completed.")
        return

    info(f"Processing {len(remaining_files)} remaining file(s)")

    project_config = _load_config()

    # Process each file sequentially
    for prompt_file in remaining_files:
        info(f"\n{'=' * 60}")
        info(f"Processing: {prompt_file.name}")
        info(f"{'=' * 60}")

        try:
            prompt_content = _read_prompt(prompt_file)
            _invoke_claude_with_reporting(prompt_content, raise_on_error=True)
            checks_passed = _run_project_checks(project_config)

            if checks_passed:
                # Mark as complete only if checks passed
                _mark_complete(directory_path, prompt_file.name)
                info(f"✓ Completed: {prompt_file.name}")
            else:
                error(f"✗ Failed: {prompt_file.name} (checks did not pass)")
                warning(
                    "Stopping directory processing. Fix issues and restart to continue."
                )
                return
        except (
            ClaudeCommandNotFoundError,
            ClaudeCommandError,
            ClaudeJSONParseError,
        ) as e:
            error(f"✗ Failed: {prompt_file.name}")
            error(f"Error: {e}")
            warning(
                "Stopping directory processing. Fix issues and restart to continue."
            )
            return
        except Exception as e:
            error(f"✗ Failed: {prompt_file.name}")
            error(f"Unexpected error: {e}")
            warning(
                "Stopping directory processing. Fix issues and restart to continue."
            )
            return

    info(f"\n{'=' * 60}")
    info("All prompt files processed successfully!")
    info(f"{'=' * 60}")


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def main(path: Path) -> None:
    """Invoke Claude Code headless with a prompt from a file or directory.

    If PATH is a file, reads the prompt from it, invokes claude with the prompt,
    and prints the session ID and result.

    If PATH is a directory, processes all .txt and .md files in the directory
    sequentially, running checks after each prompt. State is tracked to allow
    resuming from incomplete prompts.
    """
    if path.is_file():
        success = _process_single_file(path)
        if not success:
            fatal("Processing failed", exit_code=1)
    elif path.is_dir():
        _process_directory(path)
    else:
        fatal(f"Path must be a file or directory: {path}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
