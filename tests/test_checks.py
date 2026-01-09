"""Unit tests for vibe.checks module."""

import json
from unittest.mock import MagicMock, patch

from vibe.checks import CheckResult, run_check, run_checks_with_retry
from vibe.project_config import ChecksConfig, CheckStep
from vibe.providers.claude import (
    ClaudeCommandError,
    ClaudeCommandNotFoundError,
    ClaudeJSONParseError,
)


def test_check_result_dataclass():
    """Test CheckResult dataclass creation."""
    result = CheckResult(
        success=True, step_name="test", output="Success output", error=None
    )
    assert result.success is True
    assert result.step_name == "test"
    assert result.output == "Success output"
    assert result.error is None

    result_with_error = CheckResult(
        success=False,
        step_name="lint",
        output="",
        error="Lint errors found",
    )
    assert result_with_error.success is False
    assert result_with_error.error == "Lint errors found"


def test_run_check_success():
    """Test run_check with successful command execution."""
    step = CheckStep(name="test", command="echo success")

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_check(step)

        assert result.success is True
        assert result.step_name == "test"
        assert result.output == "success output"
        assert result.error is None
        mock_run.assert_called_once_with(
            "echo success",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )


def test_run_check_failure():
    """Test run_check with failing command execution."""
    step = CheckStep(name="test", command="make test")

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Test failures found"
        mock_run.return_value = mock_result

        result = run_check(step)

        assert result.success is False
        assert result.step_name == "test"
        assert result.output == ""
        assert result.error == "Test failures found"


def test_run_check_failure_with_stdout():
    """Test run_check with failing command that has stdout."""
    step = CheckStep(name="lint", command="make lint")

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = "Some lint output"
        mock_result.stderr = "Lint errors"
        mock_run.return_value = mock_result

        result = run_check(step)

        assert result.success is False
        assert result.error == "Lint errors"


def test_run_check_exception():
    """Test run_check when subprocess raises an exception."""
    step = CheckStep(name="test", command="nonexistent-command")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Command not found")

        result = run_check(step)

        assert result.success is False
        assert result.step_name == "test"
        assert result.output == ""
        assert "Command not found" in result.error


def test_run_checks_with_retry_no_steps():
    """Test run_checks_with_retry with no check steps."""
    config = ChecksConfig(steps=[], max_retries=3)

    results = run_checks_with_retry(config)

    assert results == []


def test_run_checks_with_retry_all_pass_first_try():
    """Test run_checks_with_retry when all checks pass on first attempt."""
    steps = [
        CheckStep(name="test", command="echo test"),
        CheckStep(name="lint", command="echo lint"),
    ]
    config = ChecksConfig(steps=steps, max_retries=3)

    with patch("vibe.checks.run_check") as mock_run_check:
        mock_run_check.side_effect = [
            CheckResult(success=True, step_name="test", output="test passed"),
            CheckResult(success=True, step_name="lint", output="lint passed"),
        ]

        results = run_checks_with_retry(config)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert mock_run_check.call_count == 2


def test_run_checks_with_retry_failure_then_success():
    """Test run_checks_with_retry with failure then success after Claude fix."""
    steps = [CheckStep(name="test", command="make test")]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        # First attempt: failure
        # Second attempt: success
        mock_run_check.side_effect = [
            CheckResult(
                success=False, step_name="test", output="", error="Tests failed"
            ),
            CheckResult(success=True, step_name="test", output="All tests passed"),
        ]

        results = run_checks_with_retry(config)

        assert len(results) == 1
        assert results[0].success is True
        assert mock_run_check.call_count == 2
        assert mock_invoke.call_count == 1


def test_run_checks_with_retry_max_retries_reached():
    """Test run_checks_with_retry when max retries is reached."""
    steps = [CheckStep(name="test", command="make test")]
    config = ChecksConfig(steps=steps, max_retries=2)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        # Always fail
        mock_run_check.return_value = CheckResult(
            success=False, step_name="test", output="", error="Tests failed"
        )

        results = run_checks_with_retry(config)

        assert len(results) == 1
        assert results[0].success is False
        # Should try 3 times: initial + 2 retries
        assert mock_run_check.call_count == 3
        # Should call Claude 2 times (for retries 1 and 2)
        assert mock_invoke.call_count == 2


def test_run_checks_with_retry_multiple_checks_mixed_results():
    """Test run_checks_with_retry with multiple checks having mixed results."""
    steps = [
        CheckStep(name="test", command="make test"),
        CheckStep(name="lint", command="make lint"),
    ]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        # First attempt: test passes, lint fails
        # Second attempt: both pass
        mock_run_check.side_effect = [
            CheckResult(success=True, step_name="test", output="test passed"),
            CheckResult(
                success=False, step_name="lint", output="", error="Lint errors"
            ),
            CheckResult(success=True, step_name="test", output="test passed"),
            CheckResult(success=True, step_name="lint", output="lint passed"),
        ]

        results = run_checks_with_retry(config)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert mock_run_check.call_count == 4
        assert mock_invoke.call_count == 1


def test_run_checks_with_retry_claude_command_not_found():
    """Test run_checks_with_retry when Claude command is not found during fix."""
    steps = [CheckStep(name="test", command="make test")]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        mock_run_check.return_value = CheckResult(
            success=False, step_name="test", output="", error="Tests failed"
        )
        mock_invoke.side_effect = ClaudeCommandNotFoundError()

        results = run_checks_with_retry(config)

        assert len(results) == 1
        assert results[0].success is False
        assert mock_invoke.call_count == 1


def test_run_checks_with_retry_claude_command_error():
    """Test run_checks_with_retry when Claude command fails during fix."""
    steps = [CheckStep(name="test", command="make test")]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        mock_run_check.return_value = CheckResult(
            success=False, step_name="test", output="", error="Tests failed"
        )
        mock_invoke.side_effect = ClaudeCommandError(
            returncode=1, stderr="Claude error"
        )

        results = run_checks_with_retry(config)

        assert len(results) == 1
        assert results[0].success is False
        assert mock_invoke.call_count == 1


def test_run_checks_with_retry_claude_json_parse_error():
    """Test run_checks_with_retry when Claude JSON parsing fails during fix."""
    steps = [CheckStep(name="test", command="make test")]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        mock_run_check.return_value = CheckResult(
            success=False, step_name="test", output="", error="Tests failed"
        )

        json_error = json.JSONDecodeError("Invalid JSON", "test", 0)
        mock_invoke.side_effect = ClaudeJSONParseError(
            error=json_error, raw_output="invalid json"
        )

        results = run_checks_with_retry(config)

        assert len(results) == 1
        assert results[0].success is False
        assert mock_invoke.call_count == 1


def test_run_checks_with_retry_fix_prompt_content():
    """Test that fix prompt contains correct information from failed checks."""
    steps = [
        CheckStep(name="test", command="make test"),
        CheckStep(name="lint", command="make lint"),
    ]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        # First attempt: both fail
        # Second attempt: both pass
        mock_run_check.side_effect = [
            CheckResult(success=False, step_name="test", output="", error="Test error"),
            CheckResult(success=False, step_name="lint", output="", error="Lint error"),
            CheckResult(success=True, step_name="test", output="test passed"),
            CheckResult(success=True, step_name="lint", output="lint passed"),
        ]

        run_checks_with_retry(config)

        # Verify fix prompt was called with correct content
        assert mock_invoke.call_count == 1
        fix_prompt = mock_invoke.call_args[0][0]
        assert "make test" in fix_prompt
        assert "make lint" in fix_prompt
        assert "Test error" in fix_prompt
        assert "Lint error" in fix_prompt
        assert "Please run these commands and fix all found issues" in fix_prompt


def test_run_checks_with_retry_uses_error_output_when_available():
    """Test that fix prompt uses error output when available."""
    steps = [CheckStep(name="test", command="make test")]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        mock_run_check.side_effect = [
            CheckResult(
                success=False,
                step_name="test",
                output="stdout content",
                error="stderr error content",
            ),
            CheckResult(success=True, step_name="test", output="test passed"),
        ]

        run_checks_with_retry(config)

        fix_prompt = mock_invoke.call_args[0][0]
        # Should use error (stderr) over output (stdout)
        assert "stderr error content" in fix_prompt
        assert "stdout content" not in fix_prompt


def test_run_checks_with_retry_uses_output_when_no_error():
    """Test that fix prompt uses output when error is not available."""
    steps = [CheckStep(name="test", command="make test")]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        mock_run_check.side_effect = [
            CheckResult(
                success=False, step_name="test", output="stdout content", error=None
            ),
            CheckResult(success=True, step_name="test", output="test passed"),
        ]

        run_checks_with_retry(config)

        fix_prompt = mock_invoke.call_args[0][0]
        assert "stdout content" in fix_prompt


def test_run_checks_with_retry_handles_no_output():
    """Test that fix prompt handles case when both output and error are empty."""
    steps = [CheckStep(name="test", command="make test")]
    config = ChecksConfig(steps=steps, max_retries=3)

    with (
        patch("vibe.checks.run_check") as mock_run_check,
        patch("vibe.checks.invoke_claude") as mock_invoke,
    ):
        mock_run_check.side_effect = [
            CheckResult(success=False, step_name="test", output="", error=None),
            CheckResult(success=True, step_name="test", output="test passed"),
        ]

        run_checks_with_retry(config)

        fix_prompt = mock_invoke.call_args[0][0]
        assert "No output" in fix_prompt
