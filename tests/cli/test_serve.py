"""Tests for the serve CLI command."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from vibe.cli.serve import main
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


@patch("vibe.cli.serve.uvicorn.run")
def test_serve_main_function(mock_uvicorn_run):
    """Test that main function calls uvicorn with correct parameters."""
    # Mock the settings to return specific values
    with patch(
        "vibe.cli.serve.get_settings",
    ) as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.host = "127.0.0.1"
        mock_settings.port = 8001
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        # Call the underlying function
        main.callback(host=None, port=None)

    # Verify uvicorn.run was called
    assert mock_uvicorn_run.called
    call_args = mock_uvicorn_run.call_args

    # Check that app was passed as first argument
    assert "app" in call_args.kwargs or call_args.args[0]

    # Check that host and port are correct
    assert call_args.kwargs["host"] == "127.0.0.1"
    assert call_args.kwargs["port"] == 8001
    assert call_args.kwargs["log_level"] == "info"


@patch("vibe.cli.serve.uvicorn.run")
def test_serve_with_custom_host_and_port(mock_uvicorn_run, monkeypatch):
    """Test that custom host and port are read from settings."""
    # Set environment variables
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")

    # Clear cache to pick up new env vars
    get_settings.cache_clear()

    # Call the underlying function
    main.callback(host=None, port=None)

    # Verify uvicorn.run was called
    assert mock_uvicorn_run.called
    call_args = mock_uvicorn_run.call_args

    # Check that host and port are correct
    assert call_args.kwargs["host"] == "0.0.0.0"
    assert call_args.kwargs["port"] == 9000


@patch("vibe.cli.serve.uvicorn.run")
def test_serve_with_debug_log_level(mock_uvicorn_run, monkeypatch):
    """Test that log level is passed correctly to uvicorn."""
    # Set environment variable
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # Clear cache to pick up new env vars
    get_settings.cache_clear()

    # Call the underlying function
    main.callback(host=None, port=None)

    # Verify uvicorn.run was called
    assert mock_uvicorn_run.called
    call_args = mock_uvicorn_run.call_args

    # Check that log_level is correct
    assert call_args.kwargs["log_level"] == "debug"


def test_serve_module_can_be_imported():
    """Test that the serve module can be imported and has the expected structure."""
    # Import at module level to avoid PLC0415 warning
    import vibe.cli.serve  # noqa: PLC0415

    # Verify the module has the expected attributes
    assert hasattr(vibe.cli.serve, "main")
    assert callable(vibe.cli.serve.main)
    assert hasattr(vibe.cli.serve, "app")


def test_serve_settings_defaults():
    """Test that default settings are correct for proxy host and port."""
    # Get settings without environment overrides
    settings = Settings()

    # Check defaults
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_serve_settings_validation():
    """Test that invalid proxy port raises validation error."""
    with pytest.raises(ValidationError):
        # Port should be an integer, not a string
        Settings(port="invalid")  # type: ignore[arg-type]


@patch("vibe.cli.serve.uvicorn.run")
def test_serve_with_port_as_string_converted(mock_uvicorn_run, monkeypatch):
    """Test that port number from env var string is converted to int."""
    # Set environment variable as string (env vars are always strings)
    monkeypatch.setenv("PORT", "5000")

    # Clear cache to pick up new env vars
    get_settings.cache_clear()

    # Call the underlying function
    main.callback(host=None, port=None)

    # Verify uvicorn.run was called
    assert mock_uvicorn_run.called
    call_args = mock_uvicorn_run.call_args

    # Check that port is an integer
    assert isinstance(call_args.kwargs["port"], int)
    assert call_args.kwargs["port"] == 5000


@patch("vibe.cli.serve.uvicorn.run")
def test_serve_with_cli_host_parameter(mock_uvicorn_run):
    """Test that CLI --host parameter overrides settings."""
    with patch("vibe.cli.serve.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.host = "127.0.0.1"
        mock_settings.port = 8001
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        # Call the underlying function with host parameter
        main.callback(host="0.0.0.0", port=None)

    # Verify uvicorn.run was called
    assert mock_uvicorn_run.called
    call_args = mock_uvicorn_run.call_args

    # Check that host was overridden
    assert call_args.kwargs["host"] == "0.0.0.0"
    assert call_args.kwargs["port"] == 8001


@patch("vibe.cli.serve.uvicorn.run")
def test_serve_with_cli_port_parameter(mock_uvicorn_run):
    """Test that CLI --port parameter overrides settings."""
    with patch("vibe.cli.serve.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.host = "127.0.0.1"
        mock_settings.port = 8001
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        # Call the underlying function with port parameter
        main.callback(host=None, port=9000)

    # Verify uvicorn.run was called
    assert mock_uvicorn_run.called
    call_args = mock_uvicorn_run.call_args

    # Check that port was overridden
    assert call_args.kwargs["host"] == "127.0.0.1"
    assert call_args.kwargs["port"] == 9000


@patch("vibe.cli.serve.uvicorn.run")
def test_serve_with_cli_host_and_port_parameters(mock_uvicorn_run):
    """Test that both CLI --host and --port parameters override settings."""
    with patch("vibe.cli.serve.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.host = "127.0.0.1"
        mock_settings.port = 8001
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        # Call the underlying function with both parameters
        main.callback(host="192.168.1.1", port=9999)

    # Verify uvicorn.run was called
    assert mock_uvicorn_run.called
    call_args = mock_uvicorn_run.call_args

    # Check that both were overridden
    assert call_args.kwargs["host"] == "192.168.1.1"
    assert call_args.kwargs["port"] == 9999


@patch("vibe.cli.serve.uvicorn.run")
def test_serve_with_cli_no_parameters_uses_settings(mock_uvicorn_run):
    """Test that when no CLI parameters are provided, settings are used."""
    with patch("vibe.cli.serve.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.host = "192.168.0.1"
        mock_settings.port = 3000
        mock_settings.log_level = "DEBUG"
        mock_get_settings.return_value = mock_settings

        # Call the underlying function without parameters
        main.callback(host=None, port=None)

    # Verify uvicorn.run was called
    assert mock_uvicorn_run.called
    call_args = mock_uvicorn_run.call_args

    # Check that settings values were used
    assert call_args.kwargs["host"] == "192.168.0.1"
    assert call_args.kwargs["port"] == 3000
