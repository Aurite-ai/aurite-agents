import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app instance from its new location
from src.bin.api.api import app

# Marker for API integration tests
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.anyio,  # Assuming endpoints might be async
]


# --- Test Functions ---

# Use the api_client fixture which handles setup and provides the TestClient instance
def test_api_health_check(api_client: TestClient):
    """
    Tests the /health endpoint for a 200 OK response.
    """
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_status_unauthorized(api_client: TestClient):
    """
    Tests the /status endpoint without providing an API key.
    Expects a 401 Unauthorized response.
    """
    # The fixture sets a default API key, so we need to make a request without it
    headers_without_auth = {k: v for k, v in api_client.headers.items() if k.lower() != 'x-api-key'}
    response = api_client.get("/status", headers=headers_without_auth)
    # The API key middleware should return 401 if key is missing
    assert response.status_code == 401
    # Detail message might vary slightly based on FastAPI/middleware version
    assert (
        "api key required in x-api-key header"
        in response.json().get("detail", "").lower()
    )


def test_api_status_authorized(api_client: TestClient):
    """
    Tests the /status endpoint with a valid API key (provided by fixture).
    Expects a 200 OK response with the correct status message.
    """
    # Fixture handles setup (env vars, cache clear, client creation)
    # Explicitly add auth header for this test
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get("/status", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "initialized", "manager_status": "active"}


# --- Remaining tests (health, status_unauthorized, status_authorized) stay here ---
