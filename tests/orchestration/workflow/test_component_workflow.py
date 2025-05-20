import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

from src.host_manager import HostManager

class TestComponentWorkflow:
    @pytest.mark.timeout(300)
    async def test_component_workflow(self, request, host_manager: HostManager):
        
        """
        result = await host_manager.execution.run_custom_workflow(
            workflow_name="ComponentWorkflow",
            initial_input={"workflow": [{"name": "Assistant Agent", "type": "agent"}, {"name": "Formatting Agent", "type": "agent"}, {"name": "ExampleCustomWorkflow", "type": "custom_workflow"}], "input": "Decide on one city in the west coast of America to research the weather in."},
        )
        """
        result = await host_manager.execution.run_simple_workflow(
            workflow_name="TestWorkflow",
            initial_input="Decide on one city in the west coast of America to research the weather in.",
        )

        assert "status" in result
        assert result["status"] == "completed"
