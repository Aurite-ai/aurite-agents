"""
Tests for the Aurite class.
"""

import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

from aurite.host_manager import Aurite

class TestPromptValidation:
    @pytest.mark.timeout(300)
    async def test_workflow_prompt_validation(self, request, host_manager: Aurite):
        # edit the path based on command line args
        config_file = request.config.getoption("--config")
        
        # PROJECT_ROOT_DIR deprecated, now fetch from project manager
        PROJECT_ROOT_DIR = host_manager.project_manager.current_project_root

        if config_file:
            testing_config_path = PROJECT_ROOT_DIR / f"config/testing/{config_file}"
        else:
            pytest.skip("No json config specified. Use --config=[filename]")

        result = await host_manager.execution.run_custom_workflow(
            workflow_name="Prompt Validation Workflow",
            initial_input={"config_path": testing_config_path},
        )

        assert "status" in result
        assert result["status"] == "success"
