"""
Tests for the HostManager class.
"""

import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

from src.host_manager import HostManager
from src.config import PROJECT_ROOT_DIR  # Import project root


class TestABTesting:
    @pytest.mark.timeout(300)
    @pytest.mark.xfail(
        reason="Known 'Event loop is closed' error during host_manager fixture teardown"
    )
    async def test_workflow_ab_testing(self, request, host_manager: HostManager):
        # edit the path based on command line args
        config_file = request.config.getoption("--config")

        if config_file:
            testing_config_path = PROJECT_ROOT_DIR / f"config/testing/{config_file}"
        else:
            pytest.skip("No json config specified. Use --config=[filename]")

        result = await host_manager.execution.run_custom_workflow(
            workflow_name="A/B Testing Workflow",
            initial_input={"config_path": testing_config_path},
        )

        assert "status" in result
        assert result["status"] == "success"
