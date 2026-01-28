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
    assert "Prompt file is empty" in result.output


def test_vibe_main_function_claude_not_found(temp_prompt_file):
    """Test that the main function handles claude command not found."""
    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        mock_invoke.side_effect = ClaudeCommandNotFoundError(
            "'claude' command not found. Please ensure Claude Code is installed."
        )

        result = runner.invoke(main, [str(temp_prompt_file)])

        assert result.exit_code == 1
        assert "'claude' command not found" in result.output


def test_vibe_main_function_claude_failure(temp_prompt_file):
    """Test that the main function handles claude command failures."""
    runner = CliRunner()

    with patch("vibe.cli.vibe.invoke_claude") as mock_invoke:
        mock_invoke.side_effect = ClaudeCommandError(
            returncode=1, stderr="Claude error message"
        )

        result = runner.invoke(main, [str(temp_prompt_file)])

        assert result.exit_code == 1
        assert "Claude command failed" in result.output
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
        assert "Failed to parse Claude output as JSON" in result.output


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


# ============================================================================
# Tests for directory processing functionality
# ============================================================================


def test_single_file_processing_unchanged(tmp_path, monkeypatch):
    """Test that single file processing remains unchanged."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Test prompt content")

    mock_output = {
        "session_id": "test-session-123",
        "result": "This is the test result",
    }

    runner = CliRunner()

    # Change to tmp_path to ensure .vibe directory can be created if needed
    monkeypatch.chdir(tmp_path)

    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.return_value = mock_output
        mock_checks.return_value = True

        result = runner.invoke(main, [str(prompt_file)])

        # Verify invoke was called correctly
        mock_invoke.assert_called_once_with("Test prompt content")
        mock_checks.assert_called_once()

        # Verify output
        assert result.exit_code == 0
        assert "Session ID: test-session-123" in result.output
        assert "This is the test result" in result.output


def test_directory_processing_multiple_files(tmp_path, monkeypatch):
    """Test directory processing with multiple prompt files."""
    # Create directory with multiple prompt files
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    # Create multiple prompt files
    (prompt_dir / "prompt1.txt").write_text("First prompt")
    (prompt_dir / "prompt2.txt").write_text("Second prompt")
    (prompt_dir / "prompt3.md").write_text("Third prompt")

    mock_output = {
        "session_id": "test-session",
        "result": "Test result",
    }

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.return_value = mock_output
        mock_checks.return_value = True

        result = runner.invoke(main, [str(prompt_dir)])

        # Verify all three files were processed
        assert mock_invoke.call_count == 3
        assert mock_checks.call_count == 3

        # Verify files were processed in order
        calls = [call[0][0] for call in mock_invoke.call_args_list]
        assert calls == ["First prompt", "Second prompt", "Third prompt"]

        # Verify output mentions all files
        assert result.exit_code == 0
        assert "prompt1.txt" in result.output
        assert "prompt2.txt" in result.output
        assert "prompt3.md" in result.output
        assert "All prompt files processed successfully" in result.output


def test_directory_processing_file_sorting(tmp_path, monkeypatch):
    """Test that prompt files are sorted ascending by filename."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    # Create files in non-alphabetical order
    (prompt_dir / "z_prompt.txt").write_text("Z prompt")
    (prompt_dir / "a_prompt.txt").write_text("A prompt")
    (prompt_dir / "m_prompt.md").write_text("M prompt")

    mock_output = {"session_id": "test", "result": "result"}

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.return_value = mock_output
        mock_checks.return_value = True

        runner.invoke(main, [str(prompt_dir)])

        # Verify files were processed in alphabetical order
        calls = [call[0][0] for call in mock_invoke.call_args_list]
        assert calls == ["A prompt", "M prompt", "Z prompt"]


def test_directory_processing_file_filtering(tmp_path, monkeypatch):
    """Test that only .txt and .md files are processed."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    # Create various file types
    (prompt_dir / "prompt1.txt").write_text("Text prompt")
    (prompt_dir / "prompt2.md").write_text("Markdown prompt")
    (prompt_dir / "prompt3.py").write_text("Python file - should be ignored")
    (prompt_dir / "prompt4.json").write_text("JSON file - should be ignored")
    (prompt_dir / "prompt5.txt").write_text("Another text prompt")

    mock_output = {"session_id": "test", "result": "result"}

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.return_value = mock_output
        mock_checks.return_value = True

        runner.invoke(main, [str(prompt_dir)])

        # Verify only .txt and .md files were processed (3 files)
        assert mock_invoke.call_count == 3
        assert mock_checks.call_count == 3

        # Verify the correct files were processed
        calls = [call[0][0] for call in mock_invoke.call_args_list]
        assert "Text prompt" in calls
        assert "Markdown prompt" in calls
        assert "Another text prompt" in calls
        assert "Python file - should be ignored" not in calls
        assert "JSON file - should be ignored" not in calls


def test_directory_processing_empty_directory(tmp_path, monkeypatch):
    """Test handling of empty directory."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(main, [str(prompt_dir)])

    assert result.exit_code == 0
    assert "No .txt or .md files found" in result.output


def test_state_persistence_and_resume(tmp_path, monkeypatch):
    """Test state persistence and resume functionality."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    (prompt_dir / "prompt1.txt").write_text("First prompt")
    (prompt_dir / "prompt2.txt").write_text("Second prompt")
    (prompt_dir / "prompt3.txt").write_text("Third prompt")

    mock_output = {"session_id": "test", "result": "result"}

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    # First run: process all files
    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.return_value = mock_output
        mock_checks.return_value = True

        result = runner.invoke(main, [str(prompt_dir)])

        assert mock_invoke.call_count == 3
        assert result.exit_code == 0

    # Verify state file was created
    state_file = tmp_path / ".vibe" / "state.json"
    assert state_file.exists()

    # Read state file
    with state_file.open() as f:
        state = json.load(f)

    dir_key = str(prompt_dir.resolve())
    assert dir_key in state
    assert set(state[dir_key]) == {"prompt1.txt", "prompt2.txt", "prompt3.txt"}

    # Second run: should skip all files
    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.return_value = mock_output
        mock_checks.return_value = True

        result = runner.invoke(main, [str(prompt_dir)])

        # Should not process any files
        assert mock_invoke.call_count == 0
        assert mock_checks.call_count == 0
        assert "already completed" in result.output
        assert "All prompt files in this directory have been completed" in result.output


def test_state_persistence_partial_resume(tmp_path, monkeypatch):
    """Test resuming from a partially completed directory."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    (prompt_dir / "prompt1.txt").write_text("First prompt")
    (prompt_dir / "prompt2.txt").write_text("Second prompt")
    (prompt_dir / "prompt3.txt").write_text("Third prompt")

    mock_output = {"session_id": "test", "result": "result"}

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    # Manually create state file with one completed file
    state_dir = tmp_path / ".vibe"
    state_dir.mkdir()
    state_file = state_dir / "state.json"

    dir_key = str(prompt_dir.resolve())
    state = {dir_key: ["prompt1.txt"]}

    with state_file.open("w") as f:
        json.dump(state, f)

    # Run processing - should skip prompt1.txt and process prompt2.txt and prompt3.txt
    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.return_value = mock_output
        mock_checks.return_value = True

        runner.invoke(main, [str(prompt_dir)])

        # Should process only 2 files (prompt2 and prompt3)
        assert mock_invoke.call_count == 2
        assert mock_checks.call_count == 2

        # Verify the correct files were processed
        calls = [call[0][0] for call in mock_invoke.call_args_list]
        assert "First prompt" not in calls
        assert "Second prompt" in calls
        assert "Third prompt" in calls

        # Verify state was updated
        with state_file.open() as f:
            updated_state = json.load(f)

        assert set(updated_state[dir_key]) == {
            "prompt1.txt",
            "prompt2.txt",
            "prompt3.txt",
        }


def test_error_handling_state_preservation_on_failure(tmp_path, monkeypatch):
    """Test that state is preserved when processing fails."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    (prompt_dir / "prompt1.txt").write_text("First prompt")
    (prompt_dir / "prompt2.txt").write_text("Second prompt")
    (prompt_dir / "prompt3.txt").write_text("Third prompt")

    mock_output = {"session_id": "test", "result": "result"}

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    # First run: process prompt1 successfully, fail on prompt2
    call_count = 0

    def mock_invoke_side_effect(_prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_output
        if call_count == 2:
            raise ClaudeCommandError(returncode=1, stderr="Claude error")
        return None

    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.side_effect = mock_invoke_side_effect
        mock_checks.return_value = True

        result = runner.invoke(main, [str(prompt_dir)])

        # Should fail on second file
        assert result.exit_code == 0  # Directory processing doesn't exit with error
        assert "Failed: prompt2.txt" in result.output
        assert "Stopping directory processing" in result.output

    # Verify state file exists and only contains prompt1.txt
    state_file = tmp_path / ".vibe" / "state.json"
    assert state_file.exists()

    with state_file.open() as f:
        state = json.load(f)

    dir_key = str(prompt_dir.resolve())
    assert dir_key in state
    assert state[dir_key] == [
        "prompt1.txt"
    ]  # Only first file should be marked complete

    # Second run: should resume from prompt2.txt
    call_count = 0

    def mock_invoke_side_effect2(_prompt):
        nonlocal call_count
        call_count += 1
        return mock_output

    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.side_effect = mock_invoke_side_effect2
        mock_checks.return_value = True

        result = runner.invoke(main, [str(prompt_dir)])

        # Should skip prompt1.txt and process prompt2.txt and prompt3.txt
        assert mock_invoke.call_count == 2
        calls = [call[0][0] for call in mock_invoke.call_args_list]
        assert "First prompt" not in calls
        assert "Second prompt" in calls
        assert "Third prompt" in calls


def test_error_handling_check_failure_preserves_state(tmp_path, monkeypatch):
    """Test that state is preserved when checks fail."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    (prompt_dir / "prompt1.txt").write_text("First prompt")
    (prompt_dir / "prompt2.txt").write_text("Second prompt")

    mock_output = {"session_id": "test", "result": "result"}

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    # Process prompt1 successfully, fail checks on prompt2
    call_count = 0

    def mock_checks_side_effect(*_args):
        nonlocal call_count
        call_count += 1
        return call_count == 1  # First check passes, second fails

    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.return_value = mock_output
        mock_checks.side_effect = mock_checks_side_effect

        result = runner.invoke(main, [str(prompt_dir)])

        # Should process both files but fail on second check
        assert mock_invoke.call_count == 2
        assert "Failed: prompt2.txt (checks did not pass)" in result.output
        assert "Stopping directory processing" in result.output

    # Verify state file exists and only contains prompt1.txt
    state_file = tmp_path / ".vibe" / "state.json"
    assert state_file.exists()

    with state_file.open() as f:
        state = json.load(f)

    dir_key = str(prompt_dir.resolve())
    assert dir_key in state
    assert state[dir_key] == [
        "prompt1.txt"
    ]  # Only first file should be marked complete


def test_error_handling_claude_error_preserves_state(tmp_path, monkeypatch):
    """Test that state is preserved when Claude execution fails."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()

    (prompt_dir / "prompt1.txt").write_text("First prompt")
    (prompt_dir / "prompt2.txt").write_text("Second prompt")

    mock_output = {"session_id": "test", "result": "result"}

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    # Process prompt1 successfully, fail Claude on prompt2
    call_count = 0

    def mock_invoke_side_effect(_prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_output
        if call_count == 2:
            raise ClaudeCommandNotFoundError
        return None

    with (
        patch("vibe.cli.vibe.invoke_claude") as mock_invoke,
        patch("vibe.cli.vibe._run_project_checks") as mock_checks,
    ):
        mock_invoke.side_effect = mock_invoke_side_effect
        mock_checks.return_value = True

        result = runner.invoke(main, [str(prompt_dir)])

        # Should fail on second file
        assert "Failed: prompt2.txt" in result.output
        assert "Stopping directory processing" in result.output

    # Verify state file exists and only contains prompt1.txt
    state_file = tmp_path / ".vibe" / "state.json"
    assert state_file.exists()

    with state_file.open() as f:
        state = json.load(f)

    dir_key = str(prompt_dir.resolve())
    assert dir_key in state
    assert state[dir_key] == [
        "prompt1.txt"
    ]  # Only first file should be marked complete
