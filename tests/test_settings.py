"""Unit tests for vibe.settings module."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from vibe.settings import (
    PROJECT_ROOT as SETTINGS_PROJECT_ROOT,
)
from vibe.settings import (
    Settings,
    get_settings,
)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the get_settings LRU cache before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_when_no_env_vars(monkeypatch):
    """Settings should use defaults when environment variables are not set."""
    # Ensure related environment variables are unset
    for key in ["APP_NAME", "DEBUG", "LOG_LEVEL", "ENVIRONMENT"]:
        monkeypatch.delenv(key, raising=False)

    s = Settings()
    assert s.app_name == "vibe"
    assert s.debug is False
    assert s.log_level == "INFO"
    assert s.environment == "development"


def test_environment_overrides(monkeypatch):
    """Environment variables should override default values."""
    monkeypatch.setenv("APP_NAME", "custom-app")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    monkeypatch.setenv("ENVIRONMENT", "test")

    s = Settings()
    assert s.app_name == "custom-app"
    assert s.debug is True
    assert s.log_level == "ERROR"
    assert s.environment == "test"


def test_get_settings_is_cached():
    """get_settings should return the same instance until cache is cleared."""
    # Prime the cache and get the first instance
    a = get_settings()
    b = get_settings()
    assert a is b  # same object from cache

    # Clearing the cache should yield a new instance
    get_settings.cache_clear()
    c = get_settings()
    assert c is not a


def test_project_root_and_env_file_config():
    """PROJECT_ROOT should point to repo root; env_file should reference .env there."""
    # From the tests/ directory, repo root is the parent
    expected_repo_root = Path(__file__).resolve().parents[1]

    assert SETTINGS_PROJECT_ROOT.resolve() == expected_repo_root

    # Validate env_file configured to PROJECT_ROOT/.env
    # In pydantic v2, model_config is a dict-like object set on the class
    env_file = Settings.model_config.get("env_file")
    assert isinstance(env_file, tuple)
    assert env_file[0] == SETTINGS_PROJECT_ROOT / ".env"


def test_unknown_env_vars_are_ignored(monkeypatch):
    """Unknown environment vars should be ignored due to extra='ignore'."""
    monkeypatch.setenv("UNKNOWN_SETTING", "something")
    s = Settings()

    # Accessing an unknown attribute should raise AttributeError (not set)
    with pytest.raises(AttributeError):
        _ = s.unknown_setting


def test_invalid_log_level_raises(monkeypatch):
    """Invalid LOG_LEVEL should trigger validation error due to Literal type."""
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")  # Not in allowed list

    with pytest.raises(ValidationError):
        Settings()
