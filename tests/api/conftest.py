import pytest
from fastapi.testclient import TestClient
import os

# Import the FastAPI app instance from its new location
from src.bin.api.api import app

# Import dependencies from their location
from src.bin.dependencies import get_server_config

# Marker for API integration tests (can be defined here or in main conftest)
# pytestmark = pytest.mark.api_integration


@pytest.fixture(scope="function")  # Function scope ensures isolation between tests
def api_client(monkeypatch):
    """
    Provides a TestClient instance for API integration tests with necessary setup.
    - Sets required environment variables.
    - Clears configuration cache.
    - Handles app lifespan (startup/shutdown) via TestClient context manager.
    """
    # --- Environment Setup ---

    # Use monkeypatch (provided by pytest) to set environment variables for the test function
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")  # Default to DB disabled
    monkeypatch.setenv("AURITE_PROJECT_CONFIG_PATH", "config/projects/testing_config.json") # Ensure testing_config is loaded
    # monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key_fixture")  # Dummy key
    test_api_key = os.getenv("API_KEY", "dummy_api_key_fixture")

    # Add any other environment variables required by your application during testing
    # monkeypatch.setenv("SOME_OTHER_VAR", "some_value")

    # --- Cache Clearing ---
    # Clear lru_cache for get_server_config to ensure it re-reads env vars for each test
    get_server_config.cache_clear()
    # If HostManager or other components use caching that depends on env vars, clear them too
    # e.g., from src.config import load_host_config_from_json; load_host_config_from_json.cache_clear()

    # --- Create Test Client ---
    # TestClient handles the application lifespan (startup/shutdown)
    with TestClient(app) as client:
        # Set common headers, but DO NOT set the API key by default.
        # Tests requiring auth must add the 'X-API-Key' header explicitly.
        client.headers["Content-Type"] = "application/json"  # Common header
        client.test_api_key = test_api_key

        yield client  # Provide the configured client to the test function

    # --- Teardown (handled by TestClient context manager and monkeypatch) ---
    # TestClient ensures app shutdown.
    # monkeypatch automatically reverts environment variables after the test function finishes.


@pytest.fixture(scope="function")
async def async_api_client(monkeypatch):
    """
    Provides an httpx.AsyncClient instance for API integration tests
    requiring async operations (like SSE).
    - Sets required environment variables.
    - Clears configuration cache.
    - Handles app lifespan (startup/shutdown) via AsyncClient context manager.
    """
    # --- Environment Setup (same as api_client) ---
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("AURITE_PROJECT_CONFIG_PATH", "config/projects/testing_config.json") # Ensure testing_config is loaded for async client too
    test_api_key = os.getenv("API_KEY", "dummy_api_key_fixture_async")

    # --- Cache Clearing (same as api_client) ---
    get_server_config.cache_clear()
    # Potentially clear other caches if they exist and are relevant

    # --- Create Async Test Client ---
    # httpx.AsyncClient is used for async requests.
    # It needs to be used in an async context (e.g., async with).
    # The app context (startup/shutdown) is handled by asgi-lifespan with httpx.
    # We need to ensure the app instance is the same one used by TestClient.
    # For FastAPI, AsyncClient can take the app directly.

    # The base_url should match how the TestClient constructs its URLs,
    # typically "http://testserver" or "http://127.0.0.1:some_port" if running a live server.
    # For FastAPI's TestClient, it uses "http://testserver" by default.
    # We'll use the app directly, which is simpler for in-process testing.
    from httpx import AsyncClient, ASGITransport
    from asgi_lifespan import LifespanManager # Import LifespanManager

    # The app's lifespan (startup/shutdown) needs to be managed explicitly for AsyncClient
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Set common headers. API key will be added per request in tests.
            client.headers["Content-Type"] = "application/json"
            # Store the API key on the client instance for convenience in tests, similar to TestClient.
        client.test_api_key = test_api_key
        yield client
