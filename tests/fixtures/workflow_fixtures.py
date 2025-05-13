"""
Pytest fixtures related to Workflow configurations (Simple and Custom).
"""

import pytest
from pathlib import Path

# Use relative imports assuming tests run from aurite-mcp root
from src.config.config_models import WorkflowConfig, CustomWorkflowConfig

# Note: We might need AgentConfig fixtures here if workflows depend on them,
# but for now, let's keep agent configs in agent_fixtures.py


@pytest.fixture
def sample_workflow_config() -> WorkflowConfig:
    """Provides a sample simple workflow configuration for unit tests."""
    # Assumes agents 'Agent1' and 'Agent2' exist where this is used
    return WorkflowConfig(
        name="TestSimpleWorkflow",
        steps=["Agent1", "Agent2"],
        description="A test simple workflow",
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
