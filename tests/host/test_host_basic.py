"""
Integration tests for basic MCPHost functionality.

These tests focus on the MCPHost initialization, configuration handling,
and basic state management, potentially using mocked clients or configs.
"""

import pytest

# Use relative imports assuming tests run from aurite-mcp root
from src.host.host import MCPHost
from src.config.config_models import HostConfig, ClientConfig  # Updated import path


@pytest.mark.integration
class TestHostBasicIntegration:
    """Integration tests for basic MCPHost features."""

    def test_host_initialization_empty_config(self):
        """Verify MCPHost initializes correctly with an empty client list."""
        empty_config = HostConfig(name="TestEmptyHost", clients=[])
        host = MCPHost(config=empty_config)

        assert host._config == empty_config  # Use private attribute
        assert host._config.name == "TestEmptyHost"  # Access name via config
        assert (
            host._clients == {}
        )  # Should be an empty dict internally # Use private attribute
        # assert not host.is_running  # State not explicitly tracked before initialize()

    def test_host_initialization_with_clients(self):
        """Verify MCPHost initializes with client configurations."""
        client_config_1 = ClientConfig(
            client_id="client1",
            server_path="/path/to/server1.py",  # Path doesn't need to exist for this test
            capabilities=["tools"],
            roots=[],  # Add required roots field
        )
        client_config_2 = ClientConfig(
            client_id="client2",
            server_path="/path/to/server2.py",
            capabilities=["prompts"],
            roots=[],  # Add required roots field
            exclude=["prompt_a"],  # Example exclusion
        )
        host_config = HostConfig(
            name="TestHostWithClients", clients=[client_config_1, client_config_2]
        )

        host = MCPHost(config=host_config)

        assert host._config == host_config  # Use private attribute
        assert host._config.name == "TestHostWithClients"  # Access name via config
        # _clients dict is only populated during async initialize(), should be empty after __init__
        assert host._clients == {}  # Use private attribute, check for empty dict
        # assert "client1" in host._clients  # Removed check - _clients is empty here
        # assert "client2" in host._clients  # Removed check - _clients is empty here
        # assert (
        #     host._clients["client1"]["config"] == client_config_1
        # )  # Removed check - _clients is empty here
        # assert (
        #     host._clients["client2"]["config"] == client_config_2
        # )  # Removed check - _clients is empty here
        # assert (
        #     host._clients["client1"]["process"] is None
        # )  # Removed check - _clients is empty here
        # assert host._clients["client2"]["process"] is None  # Removed check - _clients is empty here
        # assert not host.is_running # State not explicitly tracked before initialize()

    # Note: Testing the actual initialize() and shutdown() methods which start
    # processes requires async tests and potentially mocking subprocesses or using
    # the real_mcp_host fixture, which is better suited for E2E tests.
    # These integration tests focus purely on the initial state based on config.

    # TODO: Consider adding tests for exclusion logic if not covered elsewhere,
    # although verifying the *effect* of exclusion often requires running initialize()
    # and checking the managers (ToolManager, PromptManager), leaning towards E2E.
