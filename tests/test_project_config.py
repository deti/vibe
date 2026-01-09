"""Unit tests for vibe.project_config module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from vibe.project_config import (
    ChecksConfig,
    CheckStep,
    ProjectConfig,
    load_project_config,
)


def test_check_step_model():
    """Test CheckStep model creation and validation."""
    step = CheckStep(name="test", command="make test")
    assert step.name == "test"
    assert step.command == "make test"


def test_check_step_missing_fields():
    """Test CheckStep validation with missing fields."""
    with pytest.raises(ValidationError):
        CheckStep()


def test_checks_config_defaults():
    """Test ChecksConfig with default values."""
    config = ChecksConfig()
    assert config.steps == []
    assert config.max_retries == 10


def test_checks_config_with_values():
    """Test ChecksConfig with provided values."""
    steps = [
        CheckStep(name="test", command="make test"),
        CheckStep(name="lint", command="make lint"),
    ]
    config = ChecksConfig(steps=steps, max_retries=5)
    assert len(config.steps) == 2
    assert config.max_retries == 5
    assert config.steps[0].name == "test"
    assert config.steps[1].name == "lint"


def test_project_config_defaults():
    """Test ProjectConfig with default values."""
    config = ProjectConfig()
    assert config.checks is None


def test_project_config_with_checks():
    """Test ProjectConfig with checks configuration."""
    checks = ChecksConfig(
        steps=[CheckStep(name="test", command="make test")], max_retries=3
    )
    config = ProjectConfig(checks=checks)
    assert config.checks is not None
    assert len(config.checks.steps) == 1
    assert config.checks.max_retries == 3


def test_load_project_config_missing_file():
    """Test load_project_config when config file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Don't create .vibe directory, so config file won't exist

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = load_project_config()
            assert result is None


def test_load_project_config_empty_file():
    """Test load_project_config with empty YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        config_file = vibe_dir / "vibe.yaml"
        config_file.write_text("", encoding="utf-8")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = load_project_config()
            assert result is not None
            assert isinstance(result, ProjectConfig)
            assert result.checks is None


def test_load_project_config_valid_with_checks():
    """Test load_project_config with valid config containing checks."""
    config_data = {
        "checks": {
            "steps": [
                {"name": "test", "command": "make test"},
                {"name": "lint", "command": "make lint"},
            ],
            "max_retries": 5,
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        config_file = vibe_dir / "vibe.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = load_project_config()
            assert result is not None
            assert isinstance(result, ProjectConfig)
            assert result.checks is not None
            assert len(result.checks.steps) == 2
            assert result.checks.max_retries == 5
            assert result.checks.steps[0].name == "test"
            assert result.checks.steps[1].name == "lint"


def test_load_project_config_valid_without_checks():
    """Test load_project_config with valid config without checks section."""
    config_data = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        config_file = vibe_dir / "vibe.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = load_project_config()
            assert result is not None
            assert isinstance(result, ProjectConfig)
            assert result.checks is None


def test_load_project_config_invalid_yaml():
    """Test load_project_config with invalid YAML."""
    invalid_yaml = (
        "checks:\n  steps:\n    - name: test\n      command: make test\ninvalid: ["
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        config_file = vibe_dir / "vibe.yaml"
        config_file.write_text(invalid_yaml, encoding="utf-8")

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            pytest.raises(yaml.YAMLError),
        ):
            load_project_config()


def test_load_project_config_invalid_structure():
    """Test load_project_config with invalid config structure."""
    config_data = {
        "checks": {
            "steps": [
                {"name": "test"},  # Missing 'command' field
            ],
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        config_file = vibe_dir / "vibe.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            pytest.raises(ValueError, match="Failed to validate"),
        ):
            load_project_config()


def test_load_project_config_invalid_max_retries_type():
    """Test load_project_config with invalid max_retries type."""
    config_data = {
        "checks": {
            "steps": [{"name": "test", "command": "make test"}],
            "max_retries": "not-a-number",  # Should be int
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        config_file = vibe_dir / "vibe.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            pytest.raises(ValueError, match="Failed to validate"),
        ):
            load_project_config()


def test_load_project_config_checks_with_default_max_retries():
    """Test load_project_config with checks but no max_retries (uses default)."""
    config_data = {
        "checks": {
            "steps": [{"name": "test", "command": "make test"}],
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        config_file = vibe_dir / "vibe.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = load_project_config()
            assert result is not None
            assert result.checks is not None
            assert result.checks.max_retries == 10  # Default value


def test_load_project_config_empty_checks_steps():
    """Test load_project_config with empty checks steps."""
    config_data = {"checks": {"steps": [], "max_retries": 3}}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vibe_dir = tmp_path / ".vibe"
        vibe_dir.mkdir()
        config_file = vibe_dir / "vibe.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = load_project_config()
            assert result is not None
            assert result.checks is not None
            assert len(result.checks.steps) == 0
            assert result.checks.max_retries == 3
