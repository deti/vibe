"""Tests for CLI utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pathlib import Path

from vibe.cli.utils import (
    NotInGitRepositoryError,
    error,
    fatal,
    find_project_root,
    info,
    success,
    warning,
)


class TestPrintFunctions:
    """Tests for print utility functions."""

    def test_success(self, capsys):
        """Test success message printing."""
        success("Test success")
        captured = capsys.readouterr()
        assert "Test success" in captured.out
        assert "✓" in captured.out or "[green]" in captured.out

    def test_info(self, capsys):
        """Test info message printing."""
        info("Test info")
        captured = capsys.readouterr()
        assert "Test info" in captured.out
        assert "i" in captured.out or "[blue]" in captured.out

    def test_warning(self, capsys):
        """Test warning message printing."""
        warning("Test warning")
        captured = capsys.readouterr()
        assert "Test warning" in captured.out
        assert "⚠" in captured.out or "[yellow]" in captured.out

    def test_error(self, capsys):
        """Test error message printing."""
        error("Test error")
        captured = capsys.readouterr()
        assert "Test error" in captured.err
        assert "✗" in captured.err or "[red]" in captured.err

    def test_fatal(self, capsys):
        """Test fatal message printing and exit."""
        with pytest.raises(SystemExit) as exc_info:
            fatal("Test fatal", exit_code=42)

        assert exc_info.value.code == 42
        captured = capsys.readouterr()
        assert "Test fatal" in captured.err


class TestFindProjectRoot:
    """Tests for find_project_root function."""

    def test_find_project_root_in_git_repo(self, tmp_path: Path):
        """Test finding project root in a git repository."""
        # Create a git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Create a subdirectory
        subdir = tmp_path / "subdir" / "nested"
        subdir.mkdir(parents=True)

        # Should find root from subdirectory
        result = find_project_root(start=subdir)
        assert result == tmp_path

    def test_find_project_root_from_cwd(self, tmp_path: Path, monkeypatch):
        """Test finding project root from current working directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        monkeypatch.chdir(tmp_path)
        result = find_project_root()
        assert result == tmp_path

    def test_find_project_root_not_in_repo(self, tmp_path: Path):
        """Test that NotInGitRepositoryError is raised when not in a git repo."""
        # Create directory without .git
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with pytest.raises(NotInGitRepositoryError, match="Not in a git repository"):
            find_project_root(start=subdir)

    def test_find_project_root_with_start_path(self, tmp_path: Path):
        """Test finding project root with explicit start path."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = find_project_root(start=subdir)
        assert result == tmp_path
