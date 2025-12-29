"""Unit tests for vibe.main module."""

import pytest
from httpx import ASGITransport, AsyncClient

from vibe.main import app


def test_app_instance():
    """Test that the app instance exists and is a FastAPI application."""
    assert app is not None
    assert hasattr(app, "routes")


def test_app_title():
    """Test that the app has a default title."""
    # FastAPI creates default app metadata
    assert app.title is not None


def get_client() -> AsyncClient:
    """Create a test client"""
    return AsyncClient(base_url="http://test", transport=(ASGITransport(app=app)))


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test that the root endpoint returns the expected response."""
    async with get_client() as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert "message" in data
    assert data["message"] == "Hello World"


@pytest.mark.asyncio
async def test_root_endpoint_response_structure():
    """Test that the root endpoint returns a proper JSON structure."""
    async with get_client() as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()

    # Verify response is a dictionary
    assert isinstance(data, dict)

    # Verify it contains the message field
    assert "message" in data


@pytest.mark.asyncio
async def test_nonexistent_endpoint():
    """Test that a non-existent endpoint returns 404."""
    async with get_client() as client:
        response = await client.get("/nonexistent")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_root_endpoint_methods():
    """Test that only GET is allowed on the root endpoint."""
    async with get_client() as client:
        # POST should not be allowed
        response = await client.post("/")
        assert response.status_code == 405  # Method Not Allowed

        # PUT should not be allowed
        response = await client.put("/")
        assert response.status_code == 405  # Method Not Allowed

        # DELETE should not be allowed
        response = await client.delete("/")
        assert response.status_code == 405  # Method Not Allowed
