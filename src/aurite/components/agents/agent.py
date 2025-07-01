"""
Manages the multi-turn conversation loop for an Agent.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai.types.chat import ChatCompletionMessage, ChatCompletionAssistantMessageParam, ChatCompletionToolMessageParam, ChatCompletionMessageToolCallParam
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function

from ...config.config_models import AgentConfig, LLMConfig
from ...host.host import MCPHost
from ..llm.providers.litellm_client import LiteLLMClient
from .agent_turn_processor import AgentTurnProcessor

logger = logging.getLogger(__name__)


class Agent:
    """
    Orchestrates the conversation with an LLM, including tool use,
    by managing the conversation history and delegating to a turn processor.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: LiteLLMClient,
        host_instance: MCPHost,
        initial_messages: List[Dict[str, Any]],
        system_prompt_override: Optional[str] = None,
        llm_config_for_override: Optional[LLMConfig] = None,
    ):
        self.config = config
        self.llm = llm_client
        self.host = host_instance
        self.system_prompt_override = system_prompt_override
        self.llm_config_for_override = llm_config_for_override
        self.conversation_history: List[Dict[str, Any]] = initial_messages
        self.final_response: Optional[ChatCompletionMessage] = None
        self.tool_uses_in_last_turn: List[ChatCompletionMessageToolCall] = []
        logger.debug(f"Agent '{self.config.name or 'Unnamed'}' initialized.")

    async def run_conversation(self) -> Optional[ChatCompletionMessage]:
        """
        Runs the agent's conversation loop until a final response is generated
        or the max iteration limit is reached.
        """
        logger.debug(f"Agent starting run for '{self.config.name or 'Unnamed'}'.")
        effective_system_prompt = (
            self.system_prompt_override or self.config.system_prompt
        )
        tools_data = self.host.get_formatted_tools(agent_config=self.config)
        max_iterations = self.config.max_iterations or 10

        for current_iteration in range(max_iterations):
            logger.debug(f"Conversation loop iteration {current_iteration + 1}")

            turn_processor = AgentTurnProcessor(
                config=self.config,
                llm_client=self.llm,
                host_instance=self.host,
                current_messages=self.conversation_history,
                tools_data=tools_data,
                effective_system_prompt=effective_system_prompt,
                llm_config_for_override=self.llm_config_for_override,
            )

            try:
                (
                    final_response_this_turn,
                    tool_results_for_next_turn,
                    is_final_turn,
                ) = await turn_processor.process_turn()

                assistant_message = turn_processor.get_last_llm_response()
                if assistant_message:
                    self.conversation_history.append(
                        assistant_message.model_dump(exclude_none=True)
                    )

                if tool_results_for_next_turn:
                    self.conversation_history.extend(tool_results_for_next_turn)
                    self.tool_uses_in_last_turn = (
                        turn_processor.get_tool_uses_this_turn()
                    )

                if is_final_turn:
                    self.final_response = final_response_this_turn
                    logger.debug("Final response received. Ending conversation.")
                    return self.final_response

            except Exception as e:
                logger.error(
                    f"Error during conversation turn {current_iteration + 1}: {e}",
                    exc_info=True,
                )
                # In case of an error, we might want to return a custom error message
                # For now, we'll just end the conversation.
                return None

        logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
        return self.final_response

    async def stream_conversation(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams the agent's conversation, handling multiple turns and tool executions.
        Note: This implementation currently relies on a fallback to the non-streaming
        turn processor. A future enhancement would be to process the token stream
        directly to enable real-time tool execution.
        """
        logger.info(
            f"Starting streaming conversation for agent '{self.config.name or 'Unnamed'}'"
        )

        effective_system_prompt = (
            self.system_prompt_override or self.config.system_prompt
        )
        tools_data = self.host.get_formatted_tools(agent_config=self.config)
        max_iterations = self.config.max_iterations or 10

        for current_iteration in range(max_iterations):
            logger.debug(f"Starting conversation turn {current_iteration + 1}")            
            
            turn_processor = AgentTurnProcessor(
                config=self.config,
                llm_client=self.llm,
                host_instance=self.host,
                current_messages=self.conversation_history,
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
                        
                                message = ChatCompletionAssistantMessageParam(
                                    role="assistant",
                                    tool_calls=[ChatCompletionMessageToolCallParam(
                                        id=event.get("tool_id"),
                                        function=Function(
                                            name=event.get("name"),
                                            arguments=event.get("arguments"),
                                        ),
                                        type="function",
                                    )],
                                )
                                
                                self.conversation_history.append(message)
                            case "message_complete":
                                message = ChatCompletionAssistantMessageParam(
                                    role="assistant",
                                    content=[{
                                        "type": "text",
                                        "text": event.get("content")
                                    }],
                                )
                                
                                logger.info(f"Streaming message complete: {event.get("content")}")
                                
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
                        tool_message = ChatCompletionToolMessageParam(
                            role="tool",
                            tool_call_id=result["tool_id"],
                            content=result["result"] if result["status"] == "success" else result["error"],
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

        logger.warning(
            f"Reached max iterations ({max_iterations}) in stream. Ending conversation."
        )
