import pytest
import anyio  # Import anyio for sleep
import os
import tempfile
from unittest.mock import patch, AsyncMock
from pathlib import Path

from src.host.host import MCPHost
from src.config import load_host_config_from_json
from src.host.foundation.security import SecurityManager

# Define the path to the test configuration file
# Corrected path based on project structure (assuming tests run from root)
TEST_CONFIG_PATH = Path("config/testing_config.json")

# Mark all tests in this file as integration tests and use anyio backend
pytestmark = [pytest.mark.integration, pytest.mark.anyio]


# Removed module-scoped event_loop fixture - let pytest-anyio handle it


@pytest.fixture(scope="function")  # Changed scope to function for better isolation
async def configured_host_instance_with_outfile():
    """
    Fixture to initialize and shutdown an MCPHost instance using the test config,
    mocking SecurityManager's GCP secret resolution, and setting up an output file
    for the env_check_server.
    Yields the host instance and the path to the output file.
    """
    output_file = None
    original_env_value = os.environ.get("ENV_CHECK_OUTPUT_FILE")
    # Load host config, agent configs, etc. from the test JSON
    (
        host_config,
        agent_configs,
        workflow_configs,
        custom_workflow_configs,
    ) = load_host_config_from_json(TEST_CONFIG_PATH)

    # --- Mock SecurityManager.resolve_gcp_secrets ---
    # Define the mock return value
    mock_resolved_secrets = {
        "TEST_SECRET_1": "mock_value_1",
        "TEST_SECRET_DB_PASSWORD": "mock_db_password_123",
    }

    try:
        # Create a temporary file for the env_check_server output
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tmp_file:
            output_file_path = tmp_file.name
            output_file = output_file_path  # Store path for cleanup
            print(f"\n[Fixture] Using temp output file: {output_file_path}")

        # Set the environment variable *before* host initialization
        os.environ["ENV_CHECK_OUTPUT_FILE"] = output_file_path

        # Patch the method within the SecurityManager class *before* MCPHost is instantiated
        with patch.object(
            SecurityManager,
            "resolve_gcp_secrets",
            new_callable=AsyncMock,  # Use AsyncMock for async methods
            return_value=mock_resolved_secrets,
        ) as mock_resolve:
            host = MCPHost(
                config=host_config,
                agent_configs=agent_configs,
                workflow_configs=workflow_configs,
                # custom_workflow_configs=custom_workflow_configs, # Assuming custom workflows aren't needed for this test
            )

            # Initialize the host (this will start the clients, including env_check_server)
            # The patched resolve_gcp_secrets will be called during _initialize_client
            await host.initialize()

            # Give the env_check_server a moment to start and write output
            await anyio.sleep(1.0)  # Use anyio.sleep

            yield host, output_file_path  # Provide the host and output file path

            # Teardown: Shutdown the host
            await host.shutdown()

    finally:
        # Cleanup: Unset environment variable and delete temp file
        if original_env_value is None:
            if "ENV_CHECK_OUTPUT_FILE" in os.environ:
                del os.environ["ENV_CHECK_OUTPUT_FILE"]
        else:
            os.environ["ENV_CHECK_OUTPUT_FILE"] = original_env_value

        if output_file and os.path.exists(output_file):
            try:
                os.remove(output_file)
                print(f"\n[Fixture] Cleaned up temp file: {output_file}")
            except OSError as e:
                print(f"\n[Fixture] Error removing temp file {output_file}: {e}")


async def test_gcp_secrets_injected_into_client_env(
    configured_host_instance_with_outfile,
):
    """
    Tests that secrets resolved (mocked) by SecurityManager are correctly
    injected into the environment of the client process by checking the output file.
    """
    host_instance, output_file_path = configured_host_instance_with_outfile

    # Read the output file written by env_check_server.py
    output_content = ""
    try:
        # Wait a tiny bit more just in case file writing was delayed
        await anyio.sleep(0.2)  # Use anyio.sleep
        with open(output_file_path, "r", encoding="utf-8") as f:
            output_content = f.read()
        print(f"\nRead output from {output_file_path}:\n---\n{output_content}\n---")
    except FileNotFoundError:
        pytest.fail(f"Output file not found: {output_file_path}")
    except Exception as e:
        pytest.fail(f"Error reading output file {output_file_path}: {e}")

    # Assert that the expected output lines are present
    expected_line_1 = "ENV_CHECK_OUTPUT: TEST_SECRET_1=mock_value_1"
    expected_line_2 = "ENV_CHECK_OUTPUT: TEST_SECRET_DB_PASSWORD=mock_db_password_123"

    assert expected_line_1 in output_content, (
        f"Expected line '{expected_line_1}' not found in output."
    )
    assert expected_line_2 in output_content, (
        f"Expected line '{expected_line_2}' not found in output."
    )

    # Optional: Check if the mock was called
    security_manager_instance = host_instance._security_manager
    security_manager_instance.resolve_gcp_secrets.assert_called()
