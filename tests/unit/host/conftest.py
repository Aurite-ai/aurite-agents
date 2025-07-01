"""
Shared fixtures for host layer unit tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_message_router() -> AsyncMock:
    """
    Provides a reusable AsyncMock for the MessageRouter.
    """
    return AsyncMock()


@pytest.fixture
def mock_root_manager() -> AsyncMock:
    """
    Provides a reusable AsyncMock for the RootManager.
    """
    return AsyncMock()


@pytest.fixture
def mock_filtering_manager() -> Mock:
    """
    Provides a reusable Mock for the FilteringManager.
    """
    return Mock()
