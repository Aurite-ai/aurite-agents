"""
Unit tests for basic MCPHost functionality.

These tests focus on the MCPHost initialization (synchronous part),
configuration handling, and basic state management, using mocked clients or configs.
"""

import pytest

from src.host.host import MCPHost
from src.config.config_models import HostConfig, ClientConfig


@pytest.mark.host_unit  # Using the same mark as test_host_lifecycle
class TestHostBasicUnit:
    """Unit tests for basic MCPHost features (pre-initialization state)."""

    def test_host_initialization_empty_config(self):
        """Verify MCPHost initializes correctly with an empty client list."""
        empty_config = HostConfig(name="TestEmptyHost", clients=[])
        host = MCPHost(config=empty_config)

        assert host._config == empty_config
        assert host._config.name == "TestEmptyHost"
        assert host.client_manager.active_clients == {}

    def test_host_initialization_with_clients(self):
        """Verify MCPHost initializes with client configurations."""
        client_config_1 = ClientConfig(
            client_id="client1",
            server_path="/path/to/server1.py",
            capabilities=["tools"],
            roots=[],
        )
        client_config_2 = ClientConfig(
            client_id="client2",
            server_path="/path/to/server2.py",
            capabilities=["prompts"],
            roots=[],
            exclude=["prompt_a"],
        )
        host_config = HostConfig(
            name="TestHostWithClients", clients=[client_config_1, client_config_2]
        )

        host = MCPHost(config=host_config)

        assert host._config == host_config
        assert host._config.name == "TestHostWithClients"
        # ClientManager's clients dict is only populated during async initialize(),
        # so it should be empty after MCPHost.__init__
        assert host.client_manager.active_clients == {}
