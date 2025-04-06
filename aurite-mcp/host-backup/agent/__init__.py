"""
Agent layer of the MCP Host system.

This package contains components for the fourth layer of the host system:
- Workflow management
- Agent orchestration
- LLM integration

This layer builds on the foundation, communication, and resource layers
to provide a complete agent management framework.
"""

from .workflows import WorkflowManager

__all__ = ["WorkflowManager"]
