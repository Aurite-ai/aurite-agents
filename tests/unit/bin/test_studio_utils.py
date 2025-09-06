"""
Unit tests for the Aurite Studio utility functions.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from aurite.bin.studio.utils import (
    check_build_artifacts,
    check_frontend_dependencies,
    check_port_availability,
    check_system_dependencies,
    is_api_server_running,
    validate_frontend_structure,
)


class TestSystemDependencies:
    """Test system dependency checking functions."""

    def test_check_system_dependencies_success(self):
        """Test successful system dependency check."""
        with patch("subprocess.run") as mock_run:
            # Mock successful node and npm version checks
            mock_run.side_effect = [
                Mock(returncode=0, stdout="v18.0.0\n"),  # node --version
                Mock(returncode=0, stdout="8.0.0\n"),  # npm --version
            ]

            success, error = check_system_dependencies()

            assert success is True
            assert error == ""
            assert mock_run.call_count == 2

    def test_check_system_dependencies_node_missing(self):
        """Test system dependency check when Node.js is missing."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            success, error = check_system_dependencies()

            assert success is False
            assert "Node.js or npm not found in PATH" in error

    def test_check_system_dependencies_node_fails(self):
        """Test system dependency check when Node.js command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")

            success, error = check_system_dependencies()

            assert success is False
            assert "Node.js is not installed or not accessible" in error

    def test_check_system_dependencies_timeout(self):
        """Test system dependency check with timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("node", 10)

            success, error = check_system_dependencies()

            assert success is False
            assert "Timeout while checking" in error


class TestFrontendDependencies:
    """Test frontend dependency checking functions."""

    def test_check_frontend_dependencies_exists(self):
        """Test frontend dependency check when dependencies exist."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch("pathlib.Path.exists") as mock_exists:
            mock_cwd.return_value = Path("/test")
            mock_exists.return_value = True

            result = check_frontend_dependencies()

            assert result is True

    def test_check_frontend_dependencies_missing(self):
        """Test frontend dependency check when dependencies are missing."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch("pathlib.Path.exists") as mock_exists:
            mock_cwd.return_value = Path("/test")
            mock_exists.return_value = False

            result = check_frontend_dependencies()

            assert result is False


class TestBuildArtifacts:
    """Test build artifact checking functions."""

    def test_check_build_artifacts_exist(self):
        """Test build artifact check when artifacts exist."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch("pathlib.Path.exists") as mock_exists:
            mock_cwd.return_value = Path("/test")
            mock_exists.return_value = True

            result = check_build_artifacts()

            assert result is True

    def test_check_build_artifacts_missing(self):
        """Test build artifact check when artifacts are missing."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch("pathlib.Path.exists") as mock_exists:
            mock_cwd.return_value = Path("/test")
            mock_exists.return_value = False

            result = check_build_artifacts()

            assert result is False


class TestFrontendStructure:
    """Test frontend structure validation functions."""

    def test_validate_frontend_structure_valid(self):
        """Test frontend structure validation with valid structure."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch("pathlib.Path.exists") as mock_exists:
            mock_cwd.return_value = Path("/test")
            mock_exists.return_value = True

            is_valid, error = validate_frontend_structure()

            assert is_valid is True
            assert error == ""

    def test_validate_frontend_structure_missing_frontend(self):
        """Test frontend structure validation when frontend directory is missing."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch("pathlib.Path.exists") as mock_exists:
            mock_cwd.return_value = Path("/test")
            # First call (frontend dir) returns False, others don't matter
            mock_exists.side_effect = [False]

            is_valid, error = validate_frontend_structure()

            assert is_valid is False
            assert "Frontend directory not found" in error


class TestPortAvailability:
    """Test port availability checking functions."""

    def test_check_port_availability_available(self):
        """Test port availability check when port is available."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 1  # Connection failed = port available
            mock_socket.return_value.__enter__.return_value = mock_sock

            result = check_port_availability(3000)

            assert result is True

    def test_check_port_availability_in_use(self):
        """Test port availability check when port is in use."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0  # Connection succeeded = port in use
            mock_socket.return_value.__enter__.return_value = mock_sock

            result = check_port_availability(3000)

            assert result is False

    def test_check_port_availability_exception(self):
        """Test port availability check with exception."""
        with patch("socket.socket") as mock_socket:
            mock_socket.side_effect = Exception("Socket error")

            result = check_port_availability(3000)

            assert result is False


class TestAPIServerStatus:
    """Test API server status checking functions."""

    def test_is_api_server_running_success(self):
        """Test API server status check when server is running."""
        with patch("httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = is_api_server_running(8000)

            assert result is True

    def test_is_api_server_running_not_running(self):
        """Test API server status check when server is not running."""
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection failed")

            result = is_api_server_running(8000)

            assert result is False

    def test_is_api_server_running_wrong_status(self):
        """Test API server status check when server returns wrong status."""
        with patch("httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = is_api_server_running(8000)

            assert result is False

    def test_is_api_server_running_with_config(self):
        """Test API server status check using server config."""
        with patch("httpx.Client") as mock_client, patch("aurite.bin.studio.utils.get_server_config") as mock_config:
            mock_config.return_value.PORT = 8080
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = is_api_server_running()  # No port specified

            assert result is True
            # Verify it used the config port
            mock_client.return_value.__enter__.return_value.get.assert_called_with("http://localhost:8080/health")
