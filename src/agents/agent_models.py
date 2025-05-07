"""
Pydantic models for Agent execution inputs and outputs.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- Agent Output Models ---

class AgentOutputContentBlock(BaseModel):
    """Represents a single block of content within an agent's message."""
    type: str = Field(description="The type of content block (e.g., 'text', 'tool_use').")

    # Fields for 'text' type
    text: Optional[str] = Field(None, description="The text content, if the block is of type 'text'.")

    # Fields for 'tool_use' type (mirroring Anthropic's ToolUseBlock for consistency if needed)
    id: Optional[str] = Field(None, description="The ID of the tool use, if the block is of type 'tool_use'.")
    input: Optional[Dict[str, Any]] = Field(None, description="The input provided to the tool, if the block is of type 'tool_use'.")
    name: Optional[str] = Field(None, description="The name of the tool used, if the block is of type 'tool_use'.")

    # Fields for 'tool_result' type
    # Note: Anthropic's ToolResultBlock has 'tool_use_id' and 'content' (which can be string or list of blocks)
    # and optionally 'is_error'. We'll simplify here for now, assuming _serialize_content_blocks
    # will turn the tool result's content into a string or a list of dicts that can map to AgentOutputContentBlock.
    tool_use_id: Optional[str] = Field(None, description="The ID of the tool use this result corresponds to, if block is 'tool_result'.")
    # If content of a tool_result can be complex, we might need:
    # content_tool_result: Union[str, List['AgentOutputContentBlock'], None] = Field(None, alias="content")
    # For now, assuming 'text' field can capture simple string results of tools,
    # or _serialize_content_blocks will handle complex tool results appropriately before validation.

    class Config:
        extra = 'allow' # Allow other fields for future extensibility or other block types

class AgentOutputMessage(BaseModel):
    """Represents a single message in the agent's conversation or its final response."""
    role: str = Field(description="The role of the message sender (e.g., 'user', 'assistant').")
    content: List[AgentOutputContentBlock] = Field(description="A list of content blocks comprising the message.")

    # Optional fields that might be present in a final response message from an LLM
    id: Optional[str] = Field(None, description="The unique ID of the message, if applicable (e.g., from LLM provider).")
    model: Optional[str] = Field(None, description="The model that generated this message, if applicable.")
    stop_reason: Optional[str] = Field(None, description="The reason the LLM stopped generating tokens, if applicable.")
    stop_sequence: Optional[str] = Field(None, description="The specific sequence that caused the LLM to stop, if applicable.")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information for this message generation, if applicable.")

class AgentExecutionResult(BaseModel):
    """
    Standardized Pydantic model for the output of Agent.execute_agent().
    """
    conversation: List[AgentOutputMessage] = Field(description="The complete conversation history, with all messages and their content.")
    final_response: Optional[AgentOutputMessage] = Field(None, description="The final message from the assistant, if one was generated.")
    tool_uses_in_final_turn: List[Dict[str, Any]] = Field(default_factory=list, description="Details of tools used in the turn that led to the final_response. Structure: [{'id': str, 'name': str, 'input': dict}].")
    error: Optional[str] = Field(None, description="An error message if the agent execution failed at some point.")

    @property
    def primary_text(self) -> Optional[str]:
        """Helper property to get the primary text from the final_response."""
        if self.final_response and self.final_response.content:
            for block in self.final_response.content:
                if block.type == "text" and block.text is not None:
                    return block.text
        return None

    @property
    def has_error(self) -> bool:
        """Checks if an error message is present."""
        return self.error is not None

    # Consider renaming tool_uses_in_final_turn to something like 'executed_tool_calls_in_final_turn'
    # to be very clear about what it represents. For now, keeping as per design doc.
