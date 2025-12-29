"""CLI command to show application settings."""

from vibe.settings import get_settings


def main() -> None:
    """Print the app settings to stdout."""
    settings = get_settings()
    print(settings.model_dump_json(indent=2))  # noqa: T201


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
