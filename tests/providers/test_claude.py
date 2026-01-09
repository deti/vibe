"""Tests for the Claude provider implementation."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vibe.providers.claude import (
    ClaudeCommandError,
    ClaudeCommandNotFoundError,
    ClaudeError,
    ClaudeJSONParseError,
    invoke,
)


# Ensure the package can be imported from the src/ layout during tests
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def test_invoke_success():
    """Test successful invocation with valid JSON output."""
    mock_output = {
        "session_id": "test-session-123",
        "result": "This is the test result",
    }

    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = invoke("Test prompt")

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == [
            "claude",
            "-p",
            "Test prompt",
            "--output-format",
            "json",
            "--allowedTools",
            "'Bash,Read,Edit'",
            "--dangerously-skip-permissions",
        ]
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["check"] is True

        # Verify output
        assert result == mock_output
        assert result["session_id"] == "test-session-123"
        assert result["result"] == "This is the test result"


def test_invoke_with_unicode_prompt():
    """Test invocation with unicode content in prompt."""
    mock_output = {
        "session_id": "test-session-unicode",
        "result": "Unicode test result",
    }

    unicode_prompt = "Test prompt with unicode: 你好世界 🌍"

    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = invoke(unicode_prompt)

        # Verify the prompt was passed correctly
        call_args = mock_subprocess.call_args
        assert call_args[0][0][2] == unicode_prompt
        assert result == mock_output


def test_invoke_output_without_session_id():
    """Test invocation with output missing session_id."""
    mock_output = {
        "result": "This is the test result",
    }

    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = invoke("Test prompt")

        assert result == mock_output
        assert "session_id" not in result
        assert result["result"] == "This is the test result"


def test_invoke_output_without_result():
    """Test invocation with output missing result."""
    mock_output = {
        "session_id": "test-session-123",
    }

    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = invoke("Test prompt")

        assert result == mock_output
        assert result["session_id"] == "test-session-123"
        assert "result" not in result


def test_invoke_empty_output():
    """Test invocation with empty JSON object."""
    mock_output = {}

    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = invoke("Test prompt")

        assert result == mock_output
        assert len(result) == 0


def test_invoke_command_not_found():
    """Test that ClaudeCommandNotFoundError is raised when command is not found."""
    with patch("subprocess.run") as mock_subprocess:
        mock_subprocess.side_effect = FileNotFoundError()

        with pytest.raises(ClaudeCommandNotFoundError) as exc_info:
            invoke("Test prompt")

        assert "'claude' command not found" in str(exc_info.value)
        assert isinstance(exc_info.value, ClaudeError)


def test_invoke_command_failure():
    """Test that ClaudeCommandError is raised when command fails."""
    with patch("subprocess.run") as mock_subprocess:
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["claude"],
            stderr="Claude error message",
        )

        with pytest.raises(ClaudeCommandError) as exc_info:
            invoke("Test prompt")

        assert exc_info.value.returncode == 1
        assert exc_info.value.stderr == "Claude error message"
        assert "Claude command failed with exit code 1" in str(exc_info.value)
        assert isinstance(exc_info.value, ClaudeError)


def test_invoke_command_failure_no_stderr():
    """Test ClaudeCommandError when command fails without stderr."""
    with patch("subprocess.run") as mock_subprocess:
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=2,
            cmd=["claude"],
            stderr=None,
        )

        with pytest.raises(ClaudeCommandError) as exc_info:
            invoke("Test prompt")

        assert exc_info.value.returncode == 2
        assert exc_info.value.stderr is None
        assert "Claude command failed with exit code 2" in str(exc_info.value)


def test_invoke_invalid_json():
    """Test that ClaudeJSONParseError is raised when output is invalid JSON."""
    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = "Invalid JSON output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        with pytest.raises(ClaudeJSONParseError) as exc_info:
            invoke("Test prompt")

        assert "Failed to parse Claude output as JSON" in str(exc_info.value)
        assert exc_info.value.raw_output == "Invalid JSON output"
        assert isinstance(exc_info.value.error, json.JSONDecodeError)
        assert isinstance(exc_info.value, ClaudeError)


def test_invoke_malformed_json():
    """Test ClaudeJSONParseError with malformed JSON."""
    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = '{"session_id": "test", "result": }'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        with pytest.raises(ClaudeJSONParseError) as exc_info:
            invoke("Test prompt")

        assert "Failed to parse Claude output as JSON" in str(exc_info.value)
        assert exc_info.value.raw_output == '{"session_id": "test", "result": }'
        assert isinstance(exc_info.value.error, json.JSONDecodeError)


def test_invoke_empty_stdout():
    """Test ClaudeJSONParseError when stdout is empty."""
    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        with pytest.raises(ClaudeJSONParseError) as exc_info:
            invoke("Test prompt")

        assert "Failed to parse Claude output as JSON" in str(exc_info.value)
        assert exc_info.value.raw_output == ""


def test_claude_command_error_attributes():
    """Test ClaudeCommandError exception attributes."""
    error = ClaudeCommandError(returncode=42, stderr="Test error")
    assert error.returncode == 42
    assert error.stderr == "Test error"
    assert "Claude command failed with exit code 42" in str(error)


def test_claude_json_parse_error_attributes():
    """Test ClaudeJSONParseError exception attributes."""
    json_error = json.JSONDecodeError("Expecting value", "test", 0)
    error = ClaudeJSONParseError(error=json_error, raw_output="test output")
    assert error.error == json_error
    assert error.raw_output == "test output"
    assert "Failed to parse Claude output as JSON" in str(error)


def test_exception_inheritance():
    """Test that all Claude exceptions inherit from ClaudeError."""
    assert issubclass(ClaudeCommandNotFoundError, ClaudeError)
    assert issubclass(ClaudeCommandError, ClaudeError)
    assert issubclass(ClaudeJSONParseError, ClaudeError)


def test_invoke_complex_json_output():
    """Test invocation with complex nested JSON output."""
    mock_output = {
        "session_id": "test-session-complex",
        "result": "Complex result",
        "metadata": {
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0",
        },
        "items": [1, 2, 3],
    }

    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = invoke("Test prompt")

        assert result == mock_output
        assert result["metadata"]["timestamp"] == "2024-01-01T00:00:00Z"
        assert result["items"] == [1, 2, 3]


def test_invoke_with_system_prompt_file():
    """Test invocation with system prompt file."""
    mock_output = {
        "session_id": "test-session-123",
        "result": "This is the test result",
    }

    system_prompt_file = Path("/path/to/system-prompt.md")

    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = invoke("Test prompt", system_prompt_file=system_prompt_file)

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == [
            "claude",
            "-p",
            "Test prompt",
            "--system-prompt-file",
            str(system_prompt_file),
            "--output-format",
            "json",
            "--allowedTools",
            "'Bash,Read,Edit'",
            "--dangerously-skip-permissions",
        ]

        # Verify output
        assert result == mock_output
        assert result["session_id"] == "test-session-123"
        assert result["result"] == "This is the test result"


def test_invoke_without_system_prompt_file():
    """Test invocation without system prompt file (default behavior)."""
    mock_output = {
        "session_id": "test-session-123",
        "result": "This is the test result",
    }

    with patch("subprocess.run") as mock_subprocess:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_output)
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = invoke("Test prompt")

        # Verify subprocess was called correctly without system prompt file flag
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == [
            "claude",
            "-p",
            "Test prompt",
            "--output-format",
            "json",
            "--allowedTools",
            "'Bash,Read,Edit'",
            "--dangerously-skip-permissions",
        ]
        # Verify --system-prompt-file is not in the command
        assert "--system-prompt-file" not in call_args[0][0]

        # Verify output
        assert result == mock_output
