"""Check execution and retry logic."""

import subprocess
from dataclasses import dataclass

from vibe.cli.utils import error, info, warning
from vibe.project_config import ChecksConfig, CheckStep
from vibe.providers.claude import (
    ClaudeCommandError,
    ClaudeCommandNotFoundError,
    ClaudeJSONParseError,
)
from vibe.providers.claude import (
    invoke as invoke_claude,
)


@dataclass
class CheckResult:
    """Result of a check execution."""

    success: bool
    step_name: str
    output: str
    error: str | None = None


def run_check(step: CheckStep) -> CheckResult:
    """Execute a check step command.

    Args:
        step: The check step to execute.

    Returns:
        CheckResult with success status, output, and error if any.
    """
    info(f"Running check '{step.name}': {step.command}")

    try:
        result = subprocess.run(
            step.command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )

        success = result.returncode == 0
        output = result.stdout
        error_output = result.stderr if not success else None

        if success:
            info(f"Check '{step.name}' passed")
        else:
            error(f"Check '{step.name}' failed with exit code {result.returncode}")

        return CheckResult(
            success=success,
            step_name=step.name,
            output=output,
            error=error_output,
        )
    except Exception as e:
        error(f"Error executing check '{step.name}': {e}")
        return CheckResult(
            success=False,
            step_name=step.name,
            output="",
            error=str(e),
        )


def run_checks_with_retry(config: ChecksConfig) -> list[CheckResult]:
    """Run checks with automatic retry logic.

    If any check fails, automatically calls Claude with a fix prompt and retries
    all checks. Continues until all checks pass or max_retries is reached.

    Args:
        config: The checks configuration.

    Returns:
        List of final check results, even if some checks failed.
    """
    if not config.steps:
        info("No checks configured")
        return []

    retry_count = 0

    while retry_count <= config.max_retries:
        if retry_count > 0:
            info(f"Retry attempt {retry_count}/{config.max_retries}")

        # Run all checks sequentially
        results = []
        failed_checks = []

        for step in config.steps:
            result = run_check(step)
            results.append(result)

            if not result.success:
                failed_checks.append(result)

        # If all checks passed, return results
        if not failed_checks:
            info("All checks passed!")
            return results

        # If we've reached max retries, return current results
        if retry_count >= config.max_retries:
            warning(
                f"Reached maximum retries ({config.max_retries}). "
                f"Some checks still failing."
            )
            return results

        # Build fix prompt from failed checks
        failed_commands = []
        error_outputs = []

        for failed in failed_checks:
            step = next(s for s in config.steps if s.name == failed.step_name)
            failed_commands.append(f"`{step.command}`")
            error_output = failed.error or failed.output or "No output"
            error_outputs.append(f"{step.name}:\n{error_output}")

        fix_prompt = (
            f"The following checks failed:\n"
            f"{chr(10).join(f'- {cmd}' for cmd in failed_commands)}\n\n"
            f"Error outputs:\n{chr(10).join(error_outputs)}\n\n"
            f"Please run these commands and fix all found issues."
        )

        info("Calling Claude to fix failing checks...")
        info(f"Fix prompt:\n-------\n{fix_prompt}\n-------")

        # Call Claude with fix prompt
        try:
            invoke_claude(fix_prompt)
            info("Claude fix execution completed, re-running checks...")
        except ClaudeCommandNotFoundError as e:
            error(f"Error: {e}")
            warning("Cannot retry checks - Claude command not found")
            return results
        except ClaudeCommandError as e:
            error(f"Error: {e}")
            if e.stderr:
                error(f"Error output: {e.stderr}")
            warning("Claude fix execution failed, continuing with current results")
            return results
        except ClaudeJSONParseError as e:
            error(f"Error: {e}")
            error(f"Raw output: {e.raw_output}")
            warning(
                "Claude fix execution had parsing issues, continuing with current results"
            )
            return results

        retry_count += 1

    # Should not reach here, but return results if we do
    return results
