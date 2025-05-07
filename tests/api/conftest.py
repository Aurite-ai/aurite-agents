import pytest
import os  # Added for os.getenv
from fastapi.testclient import TestClient

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
    test_api_key = "test_api_fixture_key"  # Consistent key for tests
    test_config_path = "config/testing_config.json"  # Default test config

    # Use monkeypatch (provided by pytest) to set environment variables for the test function
    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")  # Default to DB disabled
    # monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key_fixture")  # Dummy key

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

        # Store the key for tests to use if needed (optional, but can be handy)
        client.test_api_key = test_api_key

        yield client  # Provide the configured client to the test function

    # --- Teardown (handled by TestClient context manager and monkeypatch) ---
    # TestClient ensures app shutdown.
    # monkeypatch automatically reverts environment variables after the test function finishes.
