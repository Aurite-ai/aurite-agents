"""
Conftest.py for tests in the tests/host directory.

Provides shared fixtures for host-level testing, particularly mocks
for foundation and filtering managers used by resource managers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

# Import foundation classes being mocked
from src.host.foundation import MessageRouter, RootManager
from src.host.filtering import FilteringManager

# --- Shared Mock Manager Fixtures ---

@pytest.fixture
def mock_message_router() -> MagicMock:
    """Provides a shared AsyncMock for MessageRouter."""
    return AsyncMock(spec=MessageRouter)

@pytest.fixture
def mock_filtering_manager() -> MagicMock:
    """Provides a shared MagicMock for FilteringManager."""
    mock = MagicMock(spec=FilteringManager)
    # Default behaviors often needed in manager tests
    mock.is_registration_allowed.return_value = True
    mock.filter_component_list.side_effect = lambda components, config: components # Pass through
    mock.filter_clients_for_request.side_effect = lambda clients, config: clients # Pass through
    mock.is_component_allowed_for_agent.return_value = True
    return mock

@pytest.fixture
def mock_root_manager() -> MagicMock:
    """Provides a shared MagicMock for RootManager."""
    mock = MagicMock(spec=RootManager)
    # Default validate_access to pass (no exception)
    mock.validate_access.return_value = True
    return mock
