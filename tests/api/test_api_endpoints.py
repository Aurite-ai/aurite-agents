"""
Integration tests for the main FastAPI application endpoints.

These tests interact with the API endpoints using TestClient and rely on the
application's lifespan to manage the HostManager state.
"""

import pytest
import os
from fastapi.testclient import TestClient

# Use relative imports assuming tests run from aurite-mcp root
from src.main import app  # Import the FastAPI app instance

# Read API Key from environment for test headers
TEST_API_KEY = os.environ.get("API_KEY", "fallback-test-key-if-not-set")
# Determine if API key is properly set for skipping tests
API_KEY_IS_SET = TEST_API_KEY != "fallback-test-key-if-not-set"
ANTHROPIC_API_KEY_IS_SET = bool(os.environ.get("ANTHROPIC_API_KEY"))


# --- Fixtures ---


@pytest.fixture(scope="function")
def api_client() -> TestClient:
    """
    Provides a function-scoped TestClient instance for making API requests.
    Ensures clean state and lifespan interaction for each test.
    """
    # TestClient uses the app instance, which includes the lifespan manager
    return TestClient(app)


# --- Test Classes ---


@pytest.mark.integration
class TestBasicEndpoints:
    """Tests for basic server endpoints like /health and /status."""

    def test_health_check(self, api_client: TestClient):
        """Test the /health endpoint."""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.skipif(not API_KEY_IS_SET, reason="Requires API_KEY in environment")
    def test_get_status_success(self, api_client: TestClient):
        """Test the /status endpoint with a valid API key."""
        headers = {"X-API-Key": TEST_API_KEY}
        response = api_client.get("/status", headers=headers)
        assert response.status_code == 200
        # Check the structure based on the refactored main.py
        assert response.json() == {"status": "initialized", "manager_status": "active"}

    def test_get_status_missing_key(self, api_client: TestClient):
        """Test the /status endpoint without an API key."""
        response = api_client.get("/status")
        assert response.status_code == 401  # Unauthorized

    def test_get_status_invalid_key(self, api_client: TestClient):
        """Test the /status endpoint with an invalid API key."""
        headers = {"X-API-Key": "invalid-key"}
        response = api_client.get("/status", headers=headers)
        assert response.status_code == 403  # Forbidden


# --- Placeholder for Agent Endpoint Tests ---
# @pytest.mark.integration
# class TestAgentEndpoints:
#     pass # Add tests later


# --- Placeholder for Workflow Endpoint Tests ---
# @pytest.mark.integration
# class TestWorkflowEndpoints:
#     pass # Add tests later


# --- Placeholder for Custom Workflow Endpoint Tests ---
# @pytest.mark.integration
# class TestCustomWorkflowEndpoints:
#     pass # Add tests later
