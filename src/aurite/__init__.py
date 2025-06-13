"""
Aurite Framework
================

This is the main package for the Aurite framework.
It exposes the core classes and functions for users to build and run AI agents.
"""

# Core classes for users
from .host_manager import Aurite

# Configuration models
from .config.config_models import (
    AgentConfig,
    ClientConfig,
    CustomWorkflowConfig,
    HostConfig,
    LLMConfig,
    ProjectConfig,
    WorkflowConfig,
    # Add other config models if they are part of the public API
)
from .components.agents.agent_models import (
    AgentOutputContentBlock,
    AgentOutputMessage,
    AgentExecutionResult,
)
from .execution.facade import ExecutionFacade

__all__ = [
    "Aurite",
    "AgentConfig",
    "ClientConfig",
    "CustomWorkflowConfig",
    "HostConfig",
    "LLMConfig",
    "ProjectConfig",
    "WorkflowConfig",
    "ExecutionFacade",
    "AgentOutputContentBlock",
    "AgentOutputMessage",
    "AgentExecutionResult",
    # Add other exposed names to __all__
]

__version__ = "0.2.0"  # Keep in sync with pyproject.toml
