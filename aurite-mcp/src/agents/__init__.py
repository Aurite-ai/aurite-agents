"""
Agent framework for Aurite MCP.
Provides base classes for building AI agents across the Agency Spectrum.
"""

from .base_workflow import (
    BaseWorkflow,
    WorkflowStep,
    StepStatus,
    StepResult,
    WorkflowContext,
)
from .base_agent import (
    BaseAgent,
    AgentTool,
    ToolType,
    AgentMemory,
    AgentPlanner,
    ToolRegistry,
    Plan,
    PlanStep,
    AgentResult,
)
