"""Tests for the show_settings CLI command."""

import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from vibe.cli.show_settings import main
from vibe.settings import Settings, get_settings


# Ensure the package can be imported from the src/ layout during tests
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear settings cache before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_show_settings_main_function():
    """Test that the main function returns settings as JSON."""
    # Capture stdout by temporarily redirecting it
    f = io.StringIO()
    with redirect_stdout(f):
        main()

    output = f.getvalue().strip()

    # Verify it's valid JSON
    settings_data = json.loads(output)

    # Check that it contains expected settings keys
    assert "app_name" in settings_data
    assert "debug" in settings_data
    assert "log_level" in settings_data

    # Verify values (accounting for .env file)
    assert settings_data["app_name"] == "vibe"
    assert settings_data["debug"] is False
    assert settings_data["log_level"] == "INFO"  # From .env file


def test_show_settings_cli_module_execution():
    """Test running the CLI module directly."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_PATH)

    proc = subprocess.run(
        [sys.executable, "-m", "vibe.cli.show_settings"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert proc.returncode == 0
    # Note: stderr might contain warnings, so we don't assert it's empty

    # Verify output is valid JSON
    output = proc.stdout.strip()
    settings_data = json.loads(output)

    # Check expected structure
    assert "app_name" in settings_data
    assert "debug" in settings_data
    assert "log_level" in settings_data


def test_show_settings_with_environment_overrides(monkeypatch):
    """Test that environment variables can override defaults."""
    # This test verifies that environment variables can override defaults
    # Note: The .env file takes precedence in the actual application,
    # so we test the settings mechanism directly

    # First, clear any existing environment variables that might interfere
    for key in ["APP_NAME", "DEBUG", "LOG_LEVEL", "ENVIRONMENT"]:
        monkeypatch.delenv(key, raising=False)

    # Set environment variables
    monkeypatch.setenv("APP_NAME", "test-app")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")

    # Clear cache to pick up new env vars
    get_settings.cache_clear()

    # Test the settings directly to verify environment overrides work
    test_settings = Settings()

    # Verify environment overrides are applied
    assert test_settings.app_name == "test-app"
    assert test_settings.debug is True
    assert test_settings.log_level == "ERROR"

    # Note: The CLI will still show the .env file values because the Settings class
    # is configured to load .env from the project root. This is the expected behavior.
    # We've verified that environment variables work by testing the Settings class directly.


def test_show_settings_json_format():
    """Test that output is properly formatted JSON with indentation."""
    f = io.StringIO()
    with redirect_stdout(f):
        main()

    output = f.getvalue()

    # Should have multiple lines due to indentation
    lines = output.strip().split("\n")
    assert len(lines) > 1

    # First line should start with {
    assert lines[0].strip() == "{"

    # Should be valid JSON
    settings_data = json.loads(output)
    assert isinstance(settings_data, dict)


def test_show_settings_script_entry_point():
    """Test that the script entry point works correctly."""
    # This test verifies the pyproject.toml script configuration
    # by testing the actual module execution
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_PATH)

    # Test the module path that would be used by the script
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, r'{SRC_PATH}'); "
            "from vibe.cli.show_settings import main; main()",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert proc.returncode == 0
    # Note: stderr might contain warnings, so we don't assert it's empty

    # Verify output is valid JSON
    output = proc.stdout.strip()
    json.loads(output)  # Should not raise
