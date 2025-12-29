"""CLI command to serve the API proxy."""

import logging

import click
import uvicorn

from vibe.main import app
from vibe.settings import get_settings


logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--host",
    "-h",
    default=None,
    help="Host address to bind the API server.",
)
@click.option(
    "--port",
    "-p",
    default=None,
    type=int,
    help="Port number to bind the API server.",
)
def main(host: str | None, port: int | None) -> None:
    """Start the API server with configured host and port."""
    settings = get_settings()

    # Use CLI parameters if provided, otherwise fall back to settings
    server_host = host if host is not None else settings.host
    server_port = port if port is not None else settings.port

    # Configure logging
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(
        f"Starting API server on {server_host}:{server_port}",
    )

    uvicorn.run(
        app,
        host=server_host,
        port=server_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
