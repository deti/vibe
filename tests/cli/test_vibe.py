"""Tests for the vibe CLI command."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from vibe.cli.vibe import main
from vibe.providers.claude import (
    ClaudeCommandError,
    ClaudeCommandNotFoundError,
    ClaudeJSONParseError,
)


# Ensure the package can be imported from the src/ layout during tests
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture
def temp_prompt_file(tmp_path):
    """Create a temporary prompt file for testing."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Test prompt content")
    return prompt_file


@pytest.fixture
def empty_prompt_file(tmp_path):
    """Create an empty prompt file for testing."""
    prompt_file = tmp_path / "empty_prompt.txt"
    prompt_file.write_text("")
    return prompt_file


def test_vibe_main_function_success(temp_prompt_file):
    """Test that the main function successfully invokes claude and parses output."""
    mock_output = {
        "session_id": "test-session-123",
        "result": "This is the test result",
    }

    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        mock_invoke.return_value = mock_output

        # Call main with the temp file path
        result = runner.invoke(main, [str(temp_prompt_file)])

        # Verify invoke was called correctly
        mock_invoke.assert_called_once_with("Test prompt content")

        # Verify output
        assert result.exit_code == 0
        assert "Session ID: test-session-123" in result.output
        assert "This is the test result" in result.output
        # The output now includes debug information
        assert "---- unparsed Claude output ----" in result.output


def test_vibe_main_function_file_not_found():
    """Test that the main function handles file not found errors."""
    non_existent_file = Path("/non/existent/prompt.txt")
    runner = CliRunner()

    result = runner.invoke(main, [str(non_existent_file)])

    # Click returns exit code 2 for parameter validation errors
    assert result.exit_code == 2
    assert "Error" in result.output or "does not exist" in result.output


def test_vibe_main_function_empty_file(empty_prompt_file):
    """Test that the main function handles empty prompt files."""
    runner = CliRunner()

    result = runner.invoke(main, [str(empty_prompt_file)])

    assert result.exit_code == 1
    assert "Error: Prompt file is empty" in result.output


def test_vibe_main_function_claude_not_found(temp_prompt_file):
    """Test that the main function handles claude command not found."""
    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        mock_invoke.side_effect = ClaudeCommandNotFoundError(
            "'claude' command not found. Please ensure Claude Code is installed."
        )

        result = runner.invoke(main, [str(temp_prompt_file)])

        assert result.exit_code == 1
        assert "Error: 'claude' command not found" in result.output


def test_vibe_main_function_claude_failure(temp_prompt_file):
    """Test that the main function handles claude command failures."""
    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        mock_invoke.side_effect = ClaudeCommandError(
            returncode=1, stderr="Claude error message"
        )

        result = runner.invoke(main, [str(temp_prompt_file)])

        assert result.exit_code == 1
        assert "Error: Claude command failed" in result.output
        assert "Claude error message" in result.output


def test_vibe_main_function_invalid_json(temp_prompt_file):
    """Test that the main function handles invalid JSON output."""
    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        json_error = json.JSONDecodeError("Expecting value", "Invalid JSON output", 0)
        mock_invoke.side_effect = ClaudeJSONParseError(
            error=json_error, raw_output="Invalid JSON output"
        )

        result = runner.invoke(main, [str(temp_prompt_file)])

        assert result.exit_code == 1
        assert "Error: Failed to parse Claude output as JSON" in result.output


def test_vibe_main_function_missing_session_id(temp_prompt_file):
    """Test that the main function handles missing session_id in output."""
    mock_output = {
        "result": "This is the test result",
    }

    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        mock_invoke.return_value = mock_output

        result = runner.invoke(main, [str(temp_prompt_file)])

        # Verify output - should not have Session ID line
        assert result.exit_code == 0
        assert "Session ID:" not in result.output
        assert "This is the test result" in result.output


def test_vibe_main_function_missing_result(temp_prompt_file):
    """Test that the main function handles missing result in output."""
    mock_output = {
        "session_id": "test-session-123",
    }

    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        mock_invoke.return_value = mock_output

        result = runner.invoke(main, [str(temp_prompt_file)])

        # Verify output - should have Session ID but no result text
        assert result.exit_code == 0
        assert "Session ID: test-session-123" in result.output
        # Debug output should be present
        assert "---- unparsed Claude output ----" in result.output
        # But no actual result text should be printed (since result field is missing)
        # The output will contain debug/info messages, but not the result content itself
        # We can verify this by checking that the JSON output is shown but no result text follows
        assert (
            '"session_id": "test-session-123"' in result.output
            or '"session_id":"test-session-123"' in result.output
        )


def test_vibe_cli_module_execution():
    """Test that the CLI module can be imported and executed as a script."""
    # This test verifies the pyproject.toml script configuration
    # by testing that the module can be imported and the main function exists
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_PATH)

    # Test that the module can be imported and main function is callable
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, r'{SRC_PATH}'); "
            "from vibe.cli.vibe import main; "
            "assert callable(main); "
            "print('Module imported successfully')",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert proc.returncode == 0
    assert "Module imported successfully" in proc.stdout


def test_vibe_prompt_file_reading_with_unicode(tmp_path):
    """Test that the main function correctly reads prompt files with unicode content."""
    prompt_file = tmp_path / "unicode_prompt.txt"
    unicode_content = "Test prompt with unicode: 你好世界 🌍"
    prompt_file.write_text(unicode_content, encoding="utf-8")

    mock_output = {
        "session_id": "test-session-unicode",
        "result": "Unicode test result",
    }

    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        mock_invoke.return_value = mock_output

        result = runner.invoke(main, [str(prompt_file)])

        # Verify the prompt content was passed correctly
        mock_invoke.assert_called_once_with(unicode_content)
        assert result.exit_code == 0
