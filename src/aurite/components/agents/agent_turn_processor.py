"""
Helper class for processing a single turn in an Agent's conversation loop.
"""

import json
import logging
import os
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, Tuple

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

if TYPE_CHECKING:
    from langfuse.client import StatefulTraceClient

from ...config.config_models import AgentConfig
from ...host.host import MCPHost
from ..llm.providers.litellm_client import LiteLLMClient

logger = logging.getLogger(__name__)


class AgentTurnProcessor:
    """
    Handles the logic for a single turn of interaction within the Agent's
    execution loop, including LLM calls, response parsing, schema validation,
    and tool execution coordination.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: LiteLLMClient,
        host_instance: MCPHost,
        current_messages: List[Dict[str, Any]],
        tools_data: Optional[List[Dict[str, Any]]],
        effective_system_prompt: Optional[str],
        trace: Optional["StatefulTraceClient"] = None,
    ):
        self.config = config
        self.llm = llm_client
        self.host = host_instance
        self.messages = current_messages
        self.tools = tools_data
        self.system_prompt = effective_system_prompt
        self._last_llm_response: Optional[ChatCompletionMessage] = None
        self._tool_uses_this_turn: List[ChatCompletionMessageToolCall] = []
        self.trace = trace
        self.span = None  # Will hold the span for this turn
        logger.debug("AgentTurnProcessor initialized.")

    def get_last_llm_response(self) -> Optional[ChatCompletionMessage]:
        return self._last_llm_response

    def get_tool_uses_this_turn(self) -> List[ChatCompletionMessageToolCall]:
        return self._tool_uses_this_turn

    def _get_turn_input(self) -> str:
        """Extract the most relevant input for this turn from the conversation history."""
        if not self.messages:
            return "No input"

        # Get the last message that triggered this turn
        last_message = self.messages[-1]
        role = last_message.get("role", "")

        if role == "user":
            return f"User: {last_message.get('content', '')}"
        elif role == "tool":
            # For tool results, show the tool name and a summary
            # Try to get tool name from different possible locations
            tool_name = last_message.get("name")
            if not tool_name:
                # Check if there's a tool_call_id we can match to previous messages
                tool_call_id = last_message.get("tool_call_id")
                if tool_call_id and len(self.messages) > 1:
                    # Look for the assistant message with this tool call
                    for msg in reversed(self.messages[:-1]):
                        if msg.get("role") == "assistant" and msg.get("tool_calls"):
                            for tc in msg.get("tool_calls", []):
                                if tc.get("id") == tool_call_id:
                                    tool_name = tc.get("function", {}).get("name", "unknown")
                                    break
                            if tool_name:
                                break
            if not tool_name:
                tool_name = "unknown"

            # Format tool name for display (handle server-prefixed names)
            display_tool_name = tool_name
            if "-" in tool_name:
                # Split server-tool format (e.g., "weather_server-weather_lookup")
                parts = tool_name.split("-", 1)
                if len(parts) == 2:
                    server_name, actual_tool_name = parts
                    display_tool_name = actual_tool_name  # Just show the tool name without server prefix

            content = last_message.get("content", "")

            # Try to parse and format MCP tool results
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "content" in parsed:
                    # Extract text content from MCP format
                    text_parts = []
                    for item in parsed.get("content", []):
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    if text_parts:
                        formatted_content = " ".join(text_parts)
                        # Truncate if needed
                        if len(formatted_content) > 200:
                            formatted_content = formatted_content[:200] + "..."
                        return f"Tool result ({display_tool_name}): {formatted_content}"
            except (json.JSONDecodeError, TypeError):
                pass

            # Fallback to raw content if parsing fails
            # Truncate long tool outputs
            if len(content) > 200:
                content = content[:200] + "..."
            return f"Tool result ({display_tool_name}): {content}"
        elif role == "assistant":
            # This shouldn't typically be the last message when starting a new turn
            return f"Assistant: {last_message.get('content', '')}"
        else:
            return f"{role}: {last_message.get('content', '')}"

    async def process_turn(
        self,
    ) -> Tuple[Optional[ChatCompletionMessage], Optional[List[Dict[str, Any]]], bool]:
        logger.debug("Processing conversation turn...")

        # Create a span for this turn if we have a trace
        if self.trace and os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
            try:
                turn_number = len([msg for msg in self.messages if msg.get("role") == "assistant"]) + 1
                turn_input = self._get_turn_input()
                self.span = self.trace.span(
                    name=f"Agent Turn {turn_number}",
                    input=turn_input,
                    metadata={
                        "has_tools": bool(self.tools),
                        "has_schema": bool(self.config.config_validation_schema),
                        "message_count": len(self.messages),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create Langfuse span for turn: {e}")
                self.span = None

        try:
            # Pass the span (or trace if no span) to the LLM
            llm_response = await self.llm.create_message(
                messages=self.messages,
                tools=self.tools,
                system_prompt_override=self.system_prompt,
                schema=self.config.config_validation_schema,
                trace=self.span or self.trace,
            )
        except Exception as e:
            if self.span:
                try:
                    self.span.end(level="ERROR", status_message=str(e))
                except:
                    pass
            logger.error(f"LLM call failed within turn processor: {e}")
            raise

        self._last_llm_response = llm_response
        is_final_turn = False

        if llm_response.tool_calls:
            tool_results_for_next_turn = await self._process_tool_calls(llm_response.tool_calls)
            if self.span:
                try:
                    # Format tool calls for output
                    tool_outputs = []
                    for tc in llm_response.tool_calls:
                        tool_name = tc.function.name
                        # Format tool name for display (handle server-prefixed names)
                        if "-" in tool_name:
                            parts = tool_name.split("-", 1)
                            if len(parts) == 2:
                                server_name, actual_tool_name = parts
                                display_name = actual_tool_name  # Just show the tool name without server prefix
                            else:
                                display_name = tool_name
                        else:
                            display_name = tool_name

                        try:
                            args = json.loads(tc.function.arguments)
                            tool_outputs.append(f"{display_name}({json.dumps(args, separators=(',', ':'))})")
                        except:
                            tool_outputs.append(f"{display_name}(...)")

                    self.span.update(
                        output=f"Tool calls: {', '.join(tool_outputs)}",
                        metadata={"tool_count": len(llm_response.tool_calls)},
                    )
                    self.span.end()
                except:
                    pass
            return None, tool_results_for_next_turn, is_final_turn
        else:
            validated_response = self._handle_final_response(llm_response)
            if validated_response:
                is_final_turn = True
            if self.span:
                try:
                    # Format the assistant's response
                    output_text = llm_response.content if llm_response.content else "No content"
                    # Truncate very long responses for readability in Langfuse
                    if len(output_text) > 500:
                        output_text = output_text[:500] + "..."

                    self.span.update(
                        output=f"Assistant: {output_text}",
                        metadata={"is_final": is_final_turn, "validated": validated_response is not None},
                    )
                    self.span.end()
                except:
                    pass
            return validated_response, None, is_final_turn

    async def stream_turn_response(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Processes a single conversation turn by streaming events from the LLM,
        handling tool calls inline, and yielding standardized event dictionaries.

        Yields:
            Dict[str, Any]: Standardized event dictionaries for SSE.
                            Includes text_delta, tool_use_start, tool_use_input_delta,
                            tool_use_end, tool_result, tool_execution_error, stream_end.
        """
        self._tool_uses_this_turn = []
        current_tool_call: Optional[Dict[str, Any]] = None
        current_text_buffer = ""
        current_message_id = None

        # Create a span for this streaming turn if we have a trace
        if self.trace and os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
            try:
                turn_number = len([msg for msg in self.messages if msg.get("role") == "assistant"]) + 1
                turn_input = self._get_turn_input()
                self.span = self.trace.span(
                    name=f"Agent Turn {turn_number} (streaming)",
                    input=turn_input,
                    metadata={
                        "has_tools": bool(self.tools),
                        "has_schema": bool(self.config.config_validation_schema),
                        "message_count": len(self.messages),
                        "streaming": True,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create Langfuse span for streaming turn: {e}")
                self.span = None

        try:
            logger.debug("ATP: About to enter LLM stream message loop")  # ADDED
            async for llm_chunk in self.llm.stream_message(
                messages=self.messages,  # type: ignore[arg-type]
                tools=self.tools,
                system_prompt_override=self.system_prompt,
                schema=self.config.config_validation_schema,  # Though schema less used in streaming
                trace=self.span or self.trace,
            ):
                logger.debug(f"ATP: Received LLM chunk from stream: {llm_chunk}")
                yield llm_chunk.model_dump(exclude_none=True)

                if not llm_chunk.choices:
                    continue

                chunk_choice = llm_chunk.choices[0]
                delta = chunk_choice.delta

                # Handle message start
                if delta.role == "assistant" and not current_text_buffer:
                    current_message_id = llm_chunk.id

                # Handle content deltas
                if delta.content:
                    current_text_buffer += delta.content

                # Handle tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        # New tool call starting
                        if tool_call.id and tool_call.function and tool_call.function.name:
                            current_tool_call = {
                                "id": tool_call.id,
                                "name": tool_call.function.name,
                                "arguments": "",
                            }

                        # Accumulate tool arguments
                        if tool_call.function and tool_call.function.arguments and current_tool_call:
                            current_tool_call["arguments"] += tool_call.function.arguments

                # Handle completion, allow finish_reason to be stop for gemini
                if chunk_choice.finish_reason in ["tool_calls", "stop"] and current_tool_call:
                    # Parse and execute tool
                    try:
                        tool_id = current_tool_call.get("id")
                        tool_name = current_tool_call.get("name")
                        tool_input_str = current_tool_call.get("arguments", "")
                        logger.debug(
                            f"Executing tool '{tool_name}' (ID: {tool_id}) from stream with input: {tool_input_str}"
                        )

                        yield {
                            "internal": True,
                            "type": "tool_complete",
                            "tool_id": tool_id,
                            "name": tool_name,
                            "arguments": tool_input_str,
                            "message_id": current_message_id,
                        }

                        if tool_name and tool_id:
                            current_tool_calls = [
                                ChatCompletionMessageToolCall(
                                    id=tool_id,
                                    function=Function(arguments=tool_input_str, name=tool_name),
                                    type="function",
                                )
                            ]

                            tool_results_for_next_turn = await self._process_tool_calls(current_tool_calls)

                            if tool_results_for_next_turn:
                                serializable_output = tool_results_for_next_turn[0].get("content")

                                yield {
                                    "role": "tool",
                                    "tool_call_id": current_tool_call["id"],
                                    "content": serializable_output,
                                }
                                yield {
                                    "internal": True,
                                    "type": "tool_result",
                                    "tool_id": current_tool_call["id"],
                                    "result": serializable_output,
                                    "status": "success",
                                }
                            else:
                                yield {
                                    "internal": True,
                                    "type": "tool_result",
                                    "tool_id": current_tool_call["id"],
                                    "error": "Error executing tool.",
                                    "status": "error",
                                }
                        else:
                            logger.error(f"Tool name missing for tool use event. Tool ID: {tool_id}")
                            yield {
                                "internal": True,
                                "type": "tool_result",
                                "tool_id": current_tool_call["id"],
                                "error": "LLM did not provide a tool name for a tool_use block.",
                                "status": "error",
                            }

                    except Exception as e:
                        yield {
                            "internal": True,
                            "type": "tool_result",
                            "tool_id": current_tool_call["id"],
                            "error": str(e),
                            "status": "error",
                        }
                    current_tool_call = None

                # Handle final completion
                if chunk_choice.finish_reason in ["stop", "length"]:
                    yield {
                        "internal": True,
                        "type": "message_complete",
                        "content": current_text_buffer,
                        "stop_reason": chunk_choice.finish_reason,
                        "message_id": current_message_id,
                    }
                    break

        except Exception as e:
            if self.span:
                try:
                    self.span.end(level="ERROR", status_message=str(e))
                except:
                    pass
            raise
        finally:
            # End the span if it was created
            if self.span:
                try:
                    # Determine the output based on what happened in this turn
                    if self._tool_uses_this_turn:
                        # Format tool calls for output
                        tool_outputs = []
                        for tc in self._tool_uses_this_turn:
                            tool_name = tc.function.name
                            # Format tool name for display (handle server-prefixed names)
                            if "-" in tool_name:
                                parts = tool_name.split("-", 1)
                                if len(parts) == 2:
                                    server_name, actual_tool_name = parts
                                    display_name = actual_tool_name  # Just show the tool name without server prefix
                                else:
                                    display_name = tool_name
                            else:
                                display_name = tool_name
                            tool_outputs.append(display_name)
                        output = f"Tool calls: {', '.join(tool_outputs)}"
                    elif current_text_buffer:
                        # Format the assistant's response
                        output_text = current_text_buffer
                        if len(output_text) > 500:
                            output_text = output_text[:500] + "..."
                        output = f"Assistant: {output_text}"
                    else:
                        output = "No output generated"

                    self.span.update(
                        output=output,
                        metadata={
                            "final_content_length": len(current_text_buffer),
                            "had_tool_calls": len(self._tool_uses_this_turn) > 0,
                            "tool_count": len(self._tool_uses_this_turn),
                        },
                    )
                    self.span.end()
                except:
                    pass
            logger.debug("Finished streaming conversation turn.")

    async def _process_tool_calls(
        self, tool_calls: Optional[List[ChatCompletionMessageToolCall]]
    ) -> List[Dict[str, Any]]:
        tool_results_for_next_turn: List[Dict[str, Any]] = []
        if not tool_calls:
            return tool_results_for_next_turn

        self._tool_uses_this_turn = tool_calls

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_input = {}
            try:
                tool_input = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON for tool '{tool_name}' arguments: {tool_call.function.arguments}")
                tool_result_content = f"Error: Invalid JSON arguments provided: {tool_call.function.arguments}"
            else:
                try:
                    tool_result_content = await self.host.call_tool(
                        name=tool_name,
                        args=tool_input,
                    )
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    tool_result_content = f"Error executing tool '{tool_name}': {str(e)}"

            # Format the result into an OpenAI-compatible tool message
            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": self._serialize_tool_content(tool_result_content),
            }
            tool_results_for_next_turn.append(tool_message)

        return tool_results_for_next_turn

    def _serialize_tool_content(self, tool_result_content: Any) -> str:
        """Safely serializes tool output content to a string for the LLM."""
        if isinstance(tool_result_content, str):
            return tool_result_content

        # For Pydantic models
        if hasattr(tool_result_content, "model_dump_json"):
            return tool_result_content.model_dump_json()
        if hasattr(tool_result_content, "model_dump"):
            return json.dumps(tool_result_content.model_dump())

        # For other JSON-serializable types
        try:
            return json.dumps(tool_result_content)
        except TypeError:
            # Fallback for any other object type
            return str(tool_result_content)

    def _handle_final_response(self, llm_response: ChatCompletionMessage) -> Optional[ChatCompletionMessage]:
        if not self.config.config_validation_schema:
            return llm_response

        text_content = llm_response.content or ""
        try:
            json_content = json.loads(text_content)
            validate(instance=json_content, schema=self.config.config_validation_schema)
            return llm_response
        except (json.JSONDecodeError, JsonSchemaValidationError) as e:
            logger.warning(f"Schema validation failed for final response: {e}")
            return None
