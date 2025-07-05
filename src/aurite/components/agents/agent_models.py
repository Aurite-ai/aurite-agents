"""
Pydantic models for Agent execution results.
"""

from typing import Any, Dict, List, Literal, Optional

from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel, Field


class AgentRunResult(BaseModel):
    """
    Standardized Pydantic model for the output of an Agent's conversation run.
    """

    status: Literal["success", "error", "max_iterations_reached"] = Field(
        description="The final status of the agent run."
    )
    final_response: Optional[ChatCompletionMessage] = Field(
        None,
        description="The final message from the assistant, if the run was successful.",
    )
    conversation_history: List[Dict[str, Any]] = Field(
        description="The complete conversation history as a list of dictionaries, compliant with OpenAI's message format."
    )
    error_message: Optional[str] = Field(None, description="An error message if the agent execution failed.")

    @property
    def primary_text(self) -> Optional[str]:
        """
        Returns the primary text content from the final response, if available.
        """
        if self.final_response and self.final_response.content:
            return self.final_response.content
        return None

    @property
    def has_error(self) -> bool:
        """Checks if the run resulted in an error."""
        return self.status == "error"
