"""Project-specific configuration loading from .vibe/vibe.yaml."""

import yaml
from pydantic import BaseModel, Field

from vibe.settings import PROJECT_ROOT


class CheckStep(BaseModel):
    """A single check step configuration."""

    name: str = Field(description="Name of the check step")
    command: str = Field(description="Command to execute for this check")


class ChecksConfig(BaseModel):
    """Configuration for checks section."""

    steps: list[CheckStep] = Field(
        default_factory=list, description="List of check steps"
    )
    max_retries: int = Field(default=10, description="Maximum number of retries")


class ProjectConfig(BaseModel):
    """Root project configuration model.

    Designed to be extensible for future custom logic sections.
    """

    checks: ChecksConfig | None = Field(
        default=None, description="Checks configuration"
    )


def load_project_config() -> ProjectConfig | None:
    """Load project configuration from .vibe/vibe.yaml.

    Returns:
        ProjectConfig instance if config file exists and is valid, None otherwise.

    Raises:
        yaml.YAMLError: If YAML parsing fails.
        ValueError: If config validation fails.
    """
    config_path = PROJECT_ROOT / ".vibe" / "vibe.yaml"

    if not config_path.exists():
        return None

    try:
        with config_path.open(encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        msg = f"Failed to parse YAML config file {config_path}: {e}"
        raise yaml.YAMLError(msg) from e

    if config_data is None:
        return ProjectConfig()

    try:
        return ProjectConfig.model_validate(config_data)
    except Exception as e:
        msg = f"Failed to validate config file {config_path}: {e}"
        raise ValueError(msg) from e
