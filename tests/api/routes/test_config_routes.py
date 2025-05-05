import pytest
from fastapi.testclient import TestClient

# Marker for API integration tests (can be defined here or imported from conftest)
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.anyio,
]

# Tests for GET /configs/{component_type} and GET /configs/{component_type}/{filename}
# will be added here later.

# TODO: Add test for listing agent configs
# TODO: Add test for listing client configs
# TODO: Add test for listing workflow configs
# TODO: Add test for listing non-existent type (expect 400 or similar)

# TODO: Add test for getting existing agent config
# TODO: Add test for getting existing client config
# TODO: Add test for getting existing workflow config
# TODO: Add test for getting non-existent config file (expect 404)
# TODO: Add test for getting config file with invalid name (expect 400/404)

# Tests for POST, PUT, DELETE will also go here.
