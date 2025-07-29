from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SessionMetadata(BaseModel):
    session_id: str
    name: str  # Name of the agent or workflow
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    message_count: Optional[int] = None
    is_workflow: bool = False  # Indicates if this is a workflow session
    agents_involved: Optional[List[str]] = None


class SessionListResponse(BaseModel):
    sessions: List[SessionMetadata]
    total: int
    offset: int
    limit: int


class ExecutionHistoryResponse(BaseModel):
    """Unified response model for both agent and workflow execution history"""

    result_type: str  # "agent" or "workflow"
    execution_result: Dict[str, Any]  # The complete AgentRunResult or SimpleWorkflowExecutionResult
    metadata: SessionMetadata
