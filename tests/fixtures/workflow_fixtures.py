"""
Pytest fixtures related to Workflow configurations (Linear and Custom).
"""

from pathlib import Path

import pytest

# Use relative imports assuming tests run from aurite-mcp root
from aurite.config.config_models import CustomWorkflowConfig, WorkflowConfig

# Note: We might need AgentConfig fixtures here if workflows depend on them,
# but for now, let's keep agent configs in agent_fixtures.py


@pytest.fixture
def sample_workflow_config() -> WorkflowConfig:
    """Provides a sample linear workflow configuration for unit tests."""
    # Assumes agents 'Agent1' and 'Agent2' exist where this is used
    return WorkflowConfig(
        name="TestLinearWorkflow",
        steps=["Agent1", "Agent2"],
        description="A test linear workflow",
    )


@pytest.fixture
def sample_custom_workflow_config() -> CustomWorkflowConfig:
    """Provides a sample custom workflow configuration for unit tests."""
    # Use dummy paths/names as the actual loading is mocked in unit tests
    return CustomWorkflowConfig(
        name="TestCustomWorkflow",
        module_path=Path("dummy/path/to/workflow.py"),
        class_name="MyCustomWorkflow",
        description="A test custom workflow",
    )


# Add more workflow config fixtures as needed
