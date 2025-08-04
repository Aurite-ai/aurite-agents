"""
LLM Client for interacting with models via the LiteLLM library.
"""

import json
import logging
import os
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, Union

import litellm
from openai import OpenAIError
from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletionMessage,
)

from ...models.config.components import LLMConfig

if TYPE_CHECKING:
    from langfuse.client import StatefulSpanClient, StatefulTraceClient

logger = logging.getLogger(__name__)


class LiteLLMClient:
    """
    A client for interacting with LLMs via the LiteLLM library.
    This client is initialized with a resolved LLMConfig and is responsible
    for making the final API calls.
    """

    def __init__(self, config: LLMConfig):
        if not config.provider or not config.model:
            raise ValueError("LLM provider and model must be specified in the config.")

        self.config = config
        litellm.drop_params = True  # Automatically drops unsupported params rather than throwing an error

        litellm_logger = logging.getLogger("LiteLLM")
        litellm_logger.setLevel(logging.ERROR)

        # Handle provider-specific setup if necessary
        if self.config.provider == "gemini":
            if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" in os.environ:
                os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

        logger.info(f"LiteLLMClient initialized for {self.config.provider}/{self.config.model}.")

    def _convert_messages_to_openai_format(
        self, messages: List[Dict[str, Any]], system_prompt: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Converts our internal dictionary message format to the OpenAI API format.
        This is now simpler as we will store history in the OpenAI format directly.
        """
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        # The messages are now expected to be in OpenAI's format already.
        # This function primarily just prepends the system prompt.
        openai_messages.extend(messages)
        return openai_messages

    def _convert_tools_to_openai_format(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        openai_tools = []
        for tool_def in tools:
            if "name" in tool_def and "inputSchema" in tool_def:
                # Ensure the input_schema has a 'type', defaulting to 'object'.
                # This is required by some providers like Anthropic.
                input_schema = tool_def["inputSchema"].copy()
                if "type" not in input_schema:
                    input_schema["type"] = "object"

                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool_def["name"],
                            "description": tool_def.get("description", ""),
                            "parameters": input_schema,
                        },
                    }
                )
        return openai_tools if openai_tools else None

    def _build_request_params(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Use the resolved system prompt from the config, but allow a final override.
        resolved_system_prompt = system_prompt_override or self.config.default_system_prompt

        if schema:
            json_instruction = f"Your response MUST be a single valid JSON object that conforms to the provided schema. Do NOT add any text or characters before or after, including code block formatting (NO ```) {json.dumps(schema, indent=2)}"
            if resolved_system_prompt:
                resolved_system_prompt = f"{resolved_system_prompt}\n{json_instruction}"
            else:
                resolved_system_prompt = json_instruction

        api_messages = self._convert_messages_to_openai_format(messages, resolved_system_prompt)
        api_tools = self._convert_tools_to_openai_format(tools)

        api_key = None
        if self.config.api_key_env_var:
            api_key = os.getenv(self.config.api_key_env_var)

        request_params: Dict[str, Any] = {
            "model": f"{self.config.provider}/{self.config.model}",
            "messages": api_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "api_base": self.config.api_base,
            "api_key": api_key,
            "api_version": self.config.api_version,
        }

        if api_tools:
            request_params["tools"] = api_tools
            request_params["tool_choice"] = "auto"

        return request_params

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        trace: Optional[Union["StatefulTraceClient", "StatefulSpanClient"]] = None,
    ) -> ChatCompletionMessage:
        request_params = self._build_request_params(messages, tools, system_prompt_override, schema)

        logger.debug(f"Making LiteLLM call with params: {request_params}")

        # Create a generation span if we have a trace/span context
        generation = None
        if trace and os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
            try:
                # Extract model info for Langfuse
                model_name = f"{self.config.provider}/{self.config.model}"

                # Create generation observation
                generation = trace.generation(
                    name=f"LLM Call - {model_name}",
                    model=model_name,
                    input=messages,
                    model_parameters={
                        "temperature": str(self.config.temperature),
                        "max_tokens": str(self.config.max_tokens),
                        "tools": str(len(tools) if tools else 0),
                        "has_schema": str(schema is not None),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create Langfuse generation: {e}")

        try:
            completion: Any = await litellm.acompletion(**request_params)
            response_message = completion.choices[0].message

            # Update generation with output and usage if available
            if generation:
                try:
                    # Extract usage information if available
                    usage_dict = None
                    if hasattr(completion, "usage") and completion.usage:
                        usage_dict = {
                            "input": completion.usage.prompt_tokens,
                            "output": completion.usage.completion_tokens,
                            "total": completion.usage.total_tokens,
                        }

                    # For Langfuse v2, update generation with output
                    output_data = (
                        response_message.model_dump()
                        if hasattr(response_message, "model_dump")
                        else str(response_message)
                    )

                    # Add metadata about the completion
                    metadata = {
                        "finish_reason": completion.choices[0].finish_reason if completion.choices else None,
                        "model": completion.model if hasattr(completion, "model") else None,
                    }

                    if usage_dict:
                        # Pass usage as separate parameters
                        generation.update(output=output_data, usage_details=usage_dict, metadata=metadata)
                    else:
                        generation.update(output=output_data, metadata=metadata)

                    generation.end()
                except Exception as e:
                    logger.warning(f"Failed to update Langfuse generation: {e}")

            return response_message
        except OpenAIError as e:
            if generation:
                try:
                    generation.end(level="ERROR", status_message=str(e))
                except:
                    pass
            logger.error(f"LiteLLM API call failed with specific error: {type(e).__name__}: {e}")
            raise  # Re-raise the specific, informative exception
        except Exception as e:
            if generation:
                try:
                    generation.end(level="ERROR", status_message=str(e))
                except:
                    pass
            logger.error(f"An unexpected error occurred during LiteLLM API call: {type(e).__name__}: {e}")
            raise  # Re-raise as a generic exception

    async def stream_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        trace: Optional[Union["StatefulTraceClient", "StatefulSpanClient"]] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        request_params = self._build_request_params(messages, tools, system_prompt_override, schema)
        request_params["stream"] = True

        logger.debug(f"Making LiteLLM streaming call with params: {request_params}")

        # Create a generation span if we have a trace/span context
        generation = None
        if trace and os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
            try:
                # Extract model info for Langfuse
                model_name = f"{self.config.provider}/{self.config.model}"

                # Create generation observation
                generation = trace.generation(
                    name=f"LLM Call - {model_name} (streaming)",
                    model=model_name,
                    input=messages,
                    model_parameters={
                        "temperature": str(self.config.temperature),
                        "max_tokens": str(self.config.max_tokens),
                        "tools": str(len(tools) if tools else 0),
                        "has_schema": str(schema is not None),
                        "stream": "true",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create Langfuse generation for streaming: {e}")

        try:
            response_stream: Any = await litellm.acompletion(**request_params)

            # Collect chunks for the final output
            collected_chunks = []
            total_tokens = 0
            full_content = ""
            tool_calls = []
            current_tool_call = None
            finish_reason = None
            model_name_from_response = None
            has_tool_calls_in_stream = False  # Track if this stream actually contains tool calls

            async for chunk in response_stream:
                collected_chunks.append(chunk)
                # Count tokens if available
                if hasattr(chunk, "usage") and chunk.usage:
                    total_tokens = chunk.usage.total_tokens

                # Capture model name from response
                if hasattr(chunk, "model") and chunk.model:
                    model_name_from_response = chunk.model

                # Collect content and tool calls
                if chunk.choices and chunk.choices[0]:
                    choice = chunk.choices[0]
                    delta = choice.delta

                    # Capture finish reason
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason

                    if delta and delta.content:
                        full_content += delta.content

                    # Handle tool calls
                    if delta and delta.tool_calls:
                        has_tool_calls_in_stream = True  # Mark that we have tool calls
                        for tool_call_delta in delta.tool_calls:
                            if tool_call_delta.id:
                                # New tool call
                                if current_tool_call:
                                    tool_calls.append(current_tool_call)
                                current_tool_call = {
                                    "id": tool_call_delta.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_call_delta.function.name if tool_call_delta.function else "",
                                        "arguments": "",
                                    },
                                }
                            elif current_tool_call and tool_call_delta.function:
                                # Accumulate arguments
                                if tool_call_delta.function.arguments:
                                    current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments

                yield chunk

            # Add the last tool call if any
            if current_tool_call:
                tool_calls.append(current_tool_call)

        except OpenAIError as e:
            logger.error(f"LiteLLM streaming call failed with specific error: {type(e).__name__}: {e}")
            raise  # Re-raise the specific, informative exception
        except Exception as e:
            logger.error(f"An unexpected error occurred during LiteLLM streaming call: {type(e).__name__}: {e}")
            raise
        finally:
            # Always update and end the generation if it was created
            if generation:
                try:
                    # Determine the output based on what was generated
                    output_data = {}
                    # Only include tool_calls if we actually had tool calls in this stream
                    if has_tool_calls_in_stream and tool_calls:
                        output_data = {"tool_calls": tool_calls}
                    elif full_content:
                        output_data = {"content": full_content}
                    else:
                        output_data = {"content": "No content generated"}

                    # Build metadata
                    metadata = {}
                    if finish_reason:
                        metadata["finish_reason"] = finish_reason
                    if model_name_from_response:
                        metadata["model"] = model_name_from_response

                    # Update with usage if we have token counts
                    if total_tokens > 0:
                        # Estimate input/output split (this is approximate for streaming)
                        estimated_input = len(str(messages)) // 4  # Rough estimate
                        estimated_output = total_tokens - estimated_input
                        generation.update(
                            output=output_data,
                            usage_details={"input": estimated_input, "output": estimated_output, "total": total_tokens},
                            metadata=metadata,
                        )
                    else:
                        generation.update(output=output_data, metadata=metadata)

                    # End the generation with appropriate status
                    generation.end()
                except Exception as gen_error:
                    logger.warning(f"Failed to update/end Langfuse generation for streaming: {gen_error}")

    def validate(self) -> bool:
        """
        Check that the LiteLLM client is valid to run.

        Returns:
            (bool): True if valid to run, otherwise raises error
        """
        messages = [{"role": "user", "content": "Hello"}]
        try:
            litellm.completion(model=f"{self.config.provider}/{self.config.model}", messages=messages, max_tokens=10)
            return True
        except Exception:
            raise
