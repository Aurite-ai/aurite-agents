"""
Aurite Framework
================

This is the main package for the Aurite framework.
It exposes the core classes and functions for users to build and run AI agents.
"""

# Core classes for users
from .aurite import Aurite
from .execution.aurite_engine import AuriteEngine

# Import the models module as 'types' for convenient access
from .lib import models as types

# Individual imports for backward compatibility
from .lib.models import (
    AgentConfig,
    AgentRunRequest,
    AgentRunResult,
    ClientConfig,
    ComponentCreate,
    ComponentUpdate,
    CustomWorkflowConfig,
    ExecutionHistoryResponse,
    HostConfig,
    LLMConfig,
    LLMConfigOverrides,
    ProjectCreate,
    ProjectInfo,
    ProjectUpdate,
    RootConfig,
    SessionListResponse,
    SessionMetadata,
    WorkflowComponent,
    WorkflowConfig,
    WorkflowRunRequest,
    WorkspaceInfo,
)

__all__ = [
    "Aurite",
    "AuriteEngine",
    "types",
    # Individual model exports for backward compatibility
    "AgentConfig",
    "AgentRunRequest",
    "AgentRunResult",
    "ClientConfig",
    "ComponentCreate",
    "ComponentUpdate",
    "CustomWorkflowConfig",
    "ExecutionHistoryResponse",
    "HostConfig",
    "LLMConfig",
    "LLMConfigOverrides",
    "ProjectCreate",
    "ProjectInfo",
    "ProjectUpdate",
    "RootConfig",
    "SessionListResponse",
    "ServerConfig",
    "SessionMetadata",
    "WorkflowComponent",
    "WorkflowConfig",
    "WorkflowRunRequest",
    "WorkspaceInfo",
]

__version__ = "0.2.0"  # Keep in sync with pyproject.toml
