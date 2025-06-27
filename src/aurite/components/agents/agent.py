"""
Manages the multi-turn conversation loop for an Agent.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, cast

from anthropic.types import MessageParam
from pydantic import ValidationError

from ...config.config_models import AgentConfig, LLMConfig

# Project imports
from ...host.host import MCPHost

# from ..llm.base_client import BaseLLM # Moved to TYPE_CHECKING
from .agent_models import (
    AgentExecutionResult,
    AgentOutputMessage,
)
from .agent_turn_processor import AgentTurnProcessor

if TYPE_CHECKING:
    from aurite.components.llm.base_client import BaseLLM  # Moved here

    pass

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        llm_client: "BaseLLM",  # Changed to string literal
        host_instance: MCPHost,
        initial_messages: List[MessageParam],
        system_prompt_override: Optional[str] = None,
        llm_config_for_override: Optional[LLMConfig] = None,
    ):
        self.config = config
        self.llm = llm_client
        self.host = host_instance
        self.system_prompt_override = system_prompt_override
        self.llm_config_for_override = llm_config_for_override
        # The conversation history now exclusively stores AgentOutputMessage objects.
        self.conversation_history: List[AgentOutputMessage] = [
            AgentOutputMessage.model_validate(message) for message in initial_messages
        ]
        self.final_response: Optional[AgentOutputMessage] = None
        self.tool_uses_in_last_turn: List[Dict[str, Any]] = []
        logger.debug(f"Agent '{self.config.name or 'Unnamed'}' initialized.")

    async def run_conversation(self) -> AgentExecutionResult:
        logger.debug(f"Agent starting run for agent '{self.config.name or 'Unnamed'}'.")
        effective_system_prompt = (
            self.system_prompt_override
            or self.config.system_prompt
            or "You are a helpful assistant."
        )
        tools_data = self.host.get_formatted_tools(agent_config=self.config)
        max_iterations = self.config.max_iterations or 10
        current_iteration = 0

        while current_iteration < max_iterations:
            # Create the API-compliant message list for the LLM call in each turn.
            current_messages_for_run: List[MessageParam] = [
                cast(MessageParam, msg.to_api_message_param())
                for msg in self.conversation_history
            ]
            current_iteration += 1
            logger.debug(f"Conversation loop iteration {current_iteration}")

            turn_processor = AgentTurnProcessor(
                config=self.config,
                llm_client=self.llm,
                host_instance=self.host,
                current_messages=current_messages_for_run,
                tools_data=tools_data,
                effective_system_prompt=effective_system_prompt,
                llm_config_for_override=self.llm_config_for_override,
            )

            try:
                (
                    turn_final_response,
                    turn_tool_results_params,
                    is_final_turn,
                ) = await turn_processor.process_turn()

                assistant_message_this_turn = turn_processor.get_last_llm_response()

                if assistant_message_this_turn:
                    # The full AgentOutputMessage is the source of truth.
                    self.conversation_history.append(assistant_message_this_turn)

                if turn_tool_results_params:
                    # Convert tool result dicts (MessageParam) to AgentOutputMessage objects
                    # before adding them to the history.
                    self.conversation_history.extend(
                        [
                            AgentOutputMessage.model_validate(result)
                            for result in turn_tool_results_params
                        ]
                    )
                    # Store tool uses from the turn processor
                    self.tool_uses_in_last_turn = (
                        turn_processor.get_tool_uses_this_turn()
                    )

                if is_final_turn:
                    self.final_response = turn_final_response
                    break
                elif not turn_tool_results_params and not is_final_turn:
                    logger.warning(
                        "Schema validation failed. Preparing correction message."
                    )
                    if self.config.config_validation_schema:
                        correction_message_content = f"""Your response must be a valid JSON object matching this schema:
{json.dumps(self.config.config_validation_schema, indent=2)}

Please correct your previous response to conform to the schema."""
                        correction_message_param: MessageParam = {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": correction_message_content}
                            ],
                        }
                        # Convert the correction message to an AgentOutputMessage before
                        # adding it to the history.
                        self.conversation_history.append(
                            AgentOutputMessage.model_validate(correction_message_param)
                        )
                    else:
                        # If no schema, treat the invalid response as final
                        # Use the full object obtained from the processor
                        self.final_response = assistant_message_this_turn
                        break
            except Exception as e:
                error_msg = f"Error during conversation turn {current_iteration}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return self._prepare_agent_result(execution_error=error_msg)

        if current_iteration >= max_iterations and self.final_response is None:
            logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
            # Find the last AgentOutputMessage in the history
            last_assistant_message_obj = next(
                (
                    msg
                    for msg in reversed(self.conversation_history)
                    if isinstance(msg, AgentOutputMessage)
                ),
                None,
            )
            if last_assistant_message_obj:
                # It's already the correct type
                self.final_response = last_assistant_message_obj
            else:
                logger.warning(
                    "Could not find a final assistant message in history for max iterations fallback."
                )
                self.final_response = (
                    None  # Ensure it's None if no suitable message found
                )

        logger.debug(f"Agent finished run for agent '{self.config.name or 'Unnamed'}'.")
        return self._prepare_agent_result(execution_error=None)

    def _prepare_agent_result(
        self, execution_error: Optional[str] = None
    ) -> AgentExecutionResult:
        logger.debug("Preparing final agent execution result...")

        # The conversation history is now guaranteed to contain only AgentOutputMessage objects,
        # so no parsing is needed.
        output_dict_for_validation = {
            "conversation": self.conversation_history,
            "final_response": self.final_response,
            "tool_uses_in_final_turn": self.tool_uses_in_last_turn,
            "error": execution_error,
        }
        try:
            agent_result = AgentExecutionResult.model_validate(
                output_dict_for_validation
            )
            if execution_error and not agent_result.error:
                agent_result.error = execution_error
            elif not execution_error and agent_result.error:
                logger.info(
                    f"AgentExecutionResult validation failed: {agent_result.error}"
                )
            return agent_result
        except ValidationError as e:
            error_msg = f"Failed to validate final AgentExecutionResult: {e}"
            logger.error(error_msg, exc_info=True)
            final_error_message = (
                f"{execution_error}\n{error_msg}" if execution_error else error_msg
            )
            try:
                return AgentExecutionResult(
                    conversation=self.conversation_history,
                    final_response=self.final_response,
                    tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                    error=final_error_message,
                )
            except Exception as fallback_e:
                logger.error(
                    f"Failed to create even a fallback AgentExecutionResult: {fallback_e}"
                )
                return AgentExecutionResult(
                    conversation=[],
                    final_response=None,
                    tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                    error=final_error_message
                    + f"\nAdditionally, fallback result creation failed: {fallback_e}",
                )
        except Exception as e:
            error_msg = f"Unexpected error during final AgentExecutionResult preparation/validation: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            final_error_message = (
                f"{execution_error}\n{error_msg}" if execution_error else error_msg
            )
            return AgentExecutionResult(
                conversation=[],
                final_response=None,
                tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                error=final_error_message,
            )

    async def stream_conversation(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams the entire conversation with the agent, handling multiple turns
        and tool executions.

        Yields:
            Dict[str, Any]: Event dictionaries containing:
                - type: Event type identifier
                - data: Event-specific data
        """
        logger.info(f"Starting streaming conversation for agent '{self.config.name or 'Unnamed'}'")
        
        effective_system_prompt = self.system_prompt_override or self.config.system_prompt or "You are a helpful assistant."
        tools_data = self.host.get_formatted_tools(agent_config=self.config)
        max_iterations = self.config.max_iterations or 10
        current_iteration = 0
        
        while current_iteration < max_iterations:
            current_iteration += 1
            logger.debug(f"Starting conversation turn {current_iteration}")
            
            # Prepare messages for LLM
            messages_for_turn = [
                cast(MessageParam, msg.to_api_message_param())
                for msg in self.conversation_history
            ]
            
            turn_processor = AgentTurnProcessor(
                config=self.config,
                llm_client=self.llm,
                host_instance=self.host,
                current_messages=messages_for_turn,
                tools_data=tools_data,
                effective_system_prompt=effective_system_prompt,
                llm_config_for_override=self.llm_config_for_override,
            )
            
            # Process the turn
            is_tool_turn = False
            tool_results = []
            
            try:
                async for event in turn_processor.stream_turn_response():
                    # Pass through the event
                    if not event.get("internal"):
                        yield event
                    else:
                        event_type = event["type"]
                        
                        match event_type:
                            case "tool_complete":
                                is_tool_turn = True
                        
                                message = AgentOutputMessage(
                                    id=event.get("message_id"),
                                    role="assistant",
                                    content=[{
                                        "type": "tool_use",
                                        "id": event.get("tool_id"),
                                        "name": event.get("name"),
                                        "input": event.get("arguments"),
                                    }],
                                    stop_reason="tool_use"
                                )
                                
                                self.conversation_history.append(message)
                            case "message_complete":
                                message = AgentOutputMessage(
                                    id=event.get("message_id"),
                                    role="assistant",
                                    content=[{
                                        "type": "text",
                                        "text": event.get("content")
                                    }],
                                    stop_reason=event.get("stop_reason")
                                )
                                self.conversation_history.append(message)
                                
                                # Store as final response if not a tool turn
                                if not is_tool_turn:
                                    self.final_response = message
                                    return
                            case "tool_result":
                                tool_results.append(event)
                            case _:
                                raise ValueError(f"Unrecognized internal type while streaming: {event_type}")

                # Process tool results if any
                if tool_results:
                    for result in tool_results:
                        tool_message = AgentOutputMessage(
                            role="user",
                            content=[{
                                "type": "tool_result",
                                "tool_use_id": result["tool_id"],
                                "content": result["result"] if result["status"] == "success" else result["error"],
                                "is_error": result["status"] == "error"
                            }]
                        )
                        self.conversation_history.append(tool_message)

            except Exception as e:
                logger.error(f"Error in conversation turn {current_iteration}: {e}")
                yield {
                    "type": "error",
                    "error": str(e),
                    "turn": current_iteration
                }
                break

            # Check iteration limit
            if current_iteration >= max_iterations:
                logger.warning(f"Reached max iterations ({max_iterations})")
                yield {
                    "type": "conversation_complete", 
                    "reason": "max_iterations"
                }
                break
                
        logger.info("Conversation streaming completed")
