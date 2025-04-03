from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import logging
from pydantic import Field

from ...host.resources.tools import ToolManager
from ..base_workflow import BaseWorkflow, WorkflowStep, CompositeStep
from ..base_models import AgentContext, AgentData, StepStatus, StepResult

logger = logging.getLogger(__name__)


class AudioMemoryContext(AgentData):
    """Data model for audio memory context"""

    filepath: str = Field(..., description="The path to the audio file")
    user_id: str = Field(..., description="The user's id for memory storage")

    # Fields that will be populated during workflow execution
    transcript_str: Optional[str] = None
    
@dataclass
class AudioTranscribeStep(WorkflowStep):
    """Step to load and transcribe audio file"""

    def __init__(self):
        super().__init__(
            name="audio_transcribe",
            description="Load and transcribe the audio file",
            required_inputs={"filepath"},
            provided_outputs={"transcript_str"},
            required_tools={"speech_to_text"},
            tags={"data", "preprocessing"},
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        # Extract inputs from context
        filepath = context.get("filepath")

        # Use tool_manager from context to execute tool
        result = await context.tool_manager.execute_tool(
            "speech_to_text",
            {"filepath": filepath},
        )

        # Process the result
        if result and isinstance(result, str):
            return {"transcript_str": result}

        # Return error information if tool call failed
        return {"transcript_str": {"error": "Failed to load file", "filepath": filepath}}
    
@dataclass
class MemoryStorageStep(WorkflowStep):
    """Step to store facts from the transcript in memory"""

    def __init__(self):
        super().__init__(
            name="memory_storage",
            description="Store facts from the transcript in memory",
            required_inputs={"transcript_str", "user_id"},
            provided_outputs={"status"},
            required_tools={"add_memories"},
            tags={"mem0"},
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        # Extract inputs from context
        transcript_str = context.get("transcript_str")
        user_id = context.get("user_id")

        # Use tool_manager from context to execute tool
        result = await context.tool_manager.execute_tool(
            "add_memories",
            {"memory_str": transcript_str, "user_id": user_id},
        )

        # Process the result
        if result and isinstance(result, str):
            return {"status": result}

        # Return error information if tool call failed
        return {"status": {"error": "Error occured in storing transcript", "transcript": transcript_str}}