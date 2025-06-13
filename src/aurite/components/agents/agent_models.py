"""
Pydantic models for Agent execution inputs and outputs.
"""

from pydantic import BaseModel, Field
from anthropic.types import MessageParam
from typing import List, Optional, Dict, Any

# --- Agent Output Models ---


class AgentOutputContentBlock(BaseModel):
    """Represents a single block of content within an agent's message."""

    type: str = Field(
        description="The type of content block (e.g., 'text', 'tool_use')."
    )

    # Fields for 'text' type
    text: Optional[str] = Field(
        default=None, description="The text content, if the block is of type 'text'."
    )

    # Fields for 'tool_use' type (mirroring Anthropic's ToolUseBlock for consistency if needed)
    id: Optional[str] = Field(
        default=None,
        description="The ID of the tool use, if the block is of type 'tool_use'.",
    )
    input: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The input provided to the tool, if the block is of type 'tool_use'.",
    )
    name: Optional[str] = Field(
        default=None,
        description="The name of the tool used, if the block is of type 'tool_use'.",
    )

    # Fields for 'tool_result' type
    tool_use_id: Optional[str] = Field(
        default=None,
        description="The ID of the tool use this result corresponds to, if block is 'tool_result'.",
    )
    content: Optional[List["AgentOutputContentBlock"]] = (
        Field(  # For tool_result, content can be list of blocks
            default=None,
            description="Nested content, e.g., for tool_result blocks or other container types.",
        )
    )
    # Added for tool_result, though ToolResultView handles it via props
    is_error: Optional[bool] = Field(
        default=None, description="Indicates if a tool result is an error."
    )

    # Internal field, not for API
    index: Optional[int] = Field(
        default=None,
        description="Internal index of the block in a sequence.",
        exclude=True,
    )

    class Config:
        extra = "allow"


class AgentOutputMessage(BaseModel):
    """Represents a single message in the agent's conversation or its final response."""

    role: str = Field(
        description="The role of the message sender (e.g., 'user', 'assistant')."
    )
    content: List[AgentOutputContentBlock] = Field(
        description="A list of content blocks comprising the message."
    )

    id: Optional[str] = Field(
        None,
        description="The unique ID of the message, if applicable (e.g., from LLM provider).",
    )
    model: Optional[str] = Field(
        None, description="The model that generated this message, if applicable."
    )
    stop_reason: Optional[str] = Field(
        None, description="The reason the LLM stopped generating tokens, if applicable."
    )
    stop_sequence: Optional[str] = Field(
        None,
        description="The specific sequence that caused the LLM to stop, if applicable.",
    )
    usage: Optional[Dict[str, int]] = Field(
        None,
        description="Token usage information for this message generation, if applicable.",
    )

    def to_api_message_param(self) -> Dict[str, Any]:
        """Converts this AgentOutputMessage to an Anthropic MessageParam compliant dictionary."""
        api_compliant_content_blocks = []
        if self.content:
            for block in self.content:  # block is AgentOutputContentBlock
                if block.type == "text":
                    if block.text is not None:
                        api_compliant_content_blocks.append(
                            {"type": "text", "text": block.text}
                        )
                elif block.type == "tool_use":
                    # Ensure input is a dict, even if empty, for Anthropic schema
                    tool_input = block.input if isinstance(block.input, dict) else {}
                    if block.id and block.name:  # input can be empty {}
                        api_compliant_content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": tool_input,
                            }
                        )
                # Add other block type conversions if necessary (e.g. image)
                # For tool_result content blocks within an assistant message (rare, usually user role):
                elif block.type == "tool_result":
                    # This case is primarily for when an assistant might be reflecting on a tool result
                    # or if a tool_result block is part of its direct output content.
                    # The content of a tool_result block itself can be complex.
                    if (
                        block.tool_use_id and block.content is not None
                    ):  # block.content is List[AgentOutputContentBlock]
                        inner_api_content = []
                        for inner_block in block.content:
                            if (
                                inner_block.type == "text"
                                and inner_block.text is not None
                            ):
                                inner_api_content.append(
                                    {"type": "text", "text": inner_block.text}
                                )
                            # Potentially handle other inner block types if tools can return complex structures

                        api_compliant_content_blocks.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.tool_use_id,
                                "content": inner_api_content,  # This should be List of simple blocks like {"type": "text", "text": ...}
                                "is_error": block.is_error
                                if block.is_error is not None
                                else False,
                            }
                        )
                    elif (
                        block.tool_use_id and block.text is not None
                    ):  # Simple string content for tool_result
                        api_compliant_content_blocks.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.tool_use_id,
                                "content": block.text,  # Anthropic allows string content for tool_result
                                "is_error": block.is_error
                                if block.is_error is not None
                                else False,
                            }
                        )

        message_param: Dict[str, Any] = {
            "role": self.role,
            "content": api_compliant_content_blocks,
        }
        # Anthropic doesn't take id, model, stop_reason etc. as part of the MessageParam input list.
        return message_param


class AgentExecutionResult(BaseModel):
    """
    Standardized Pydantic model for the output of Agent.execute_agent().
    """

    conversation: List[AgentOutputMessage] = Field(
        description="The complete conversation history, with all messages and their content."
    )
    final_response: Optional[AgentOutputMessage] = Field(
        None, description="The final message from the assistant, if one was generated."
    )
    tool_uses_in_final_turn: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Details of tools used in the turn that led to the final_response. Structure: [{'id': str, 'name': str, 'input': dict}].",
    )
    error: Optional[str] = Field(
        None,
        description="An error message if the agent execution failed at some point.",
    )

    @property
    def _raw_primary_text_content(self) -> Optional[str]:
        """Internal helper to get only the actual text from final_response, or None."""
        if self.final_response and self.final_response.content:
            for block in self.final_response.content:
                if block.type == "text" and block.text is not None:
                    return block.text
        return None

    @property
    def primary_text(self) -> str:
        """
        Gets the primary text from the final_response for display,
        or an error/status message if applicable.
        """
        if self.error:  # Equivalent to self.has_error
            return f"Agent execution error: {self.error}"

        actual_text = self._raw_primary_text_content
        if actual_text is not None:
            return actual_text

        # If no error and no actual text found
        return "Agent's final response did not contain primary text."

    @property
    def has_error(self) -> bool:
        """Checks if an error message is present."""
        return self.error is not None


# --- Agent Input Models ---

class ConversationHistoryMessage(BaseModel):
    role: str = Field(
        description="The role of the message sender (e.g., 'user', 'assistant')."
    )
    content: str = Field(
        description="The content of the message"
    )
    
    
class ToolDefinition(BaseModel):
    name: str = Field(
        description="The tool name."
    )
    description: str = Field(
        description="The tool description."
    )
    input_schema: dict[str, Any] = Field(
        description="A json schema describing the input parameters for the tool."
    )
    