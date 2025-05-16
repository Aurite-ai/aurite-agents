"""
Aurite Agents Framework
=======================

This is the main package for the Aurite Agents framework.
It exposes the core classes and functions for users to build and run AI agents.
"""

# Core classes for users
from src.host_manager import HostManager

# Configuration models
from src.config.config_models import (
    AgentConfig,
    ClientConfig,
    CustomWorkflowConfig,
    HostConfig,
    LLMConfig,
    ProjectConfig,
    WorkflowConfig,
    # Add other config models if they are part of the public API
)

# Potentially other key components or utilities
# from .execution.facade import ExecutionFacade # If users need to type hint it directly
# from .some_utility_module import useful_function

__all__ = [
    "HostManager",
    "AgentConfig",
    "ClientConfig",
    "CustomWorkflowConfig",
    "HostConfig",
    "LLMConfig",
    "ProjectConfig",
    "WorkflowConfig",
    # Add other exposed names to __all__
]

__version__ = "0.2.0" # Keep in sync with pyproject.toml
