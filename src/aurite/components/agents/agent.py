"""
Manages the multi-turn conversation loop for an Agent.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionMessageToolCallParam,
)
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function

from ...config.config_models import AgentConfig, LLMConfig
from ...host.host import MCPHost
from ..llm.providers.litellm_client import LiteLLMClient
from .agent_models import AgentRunResult
from .agent_turn_processor import AgentTurnProcessor

logger = logging.getLogger(__name__)


class Agent:
    """
    Orchestrates the conversation with an LLM, including tool use,
    by managing the conversation history and delegating to a turn processor.
    """

    def __init__(
        self,
        agent_config: AgentConfig,
        base_llm_config: LLMConfig,
        host_instance: MCPHost,
        initial_messages: List[Dict[str, Any]],
    ):
        self.config = agent_config
        self.host = host_instance
        self.conversation_history: List[Dict[str, Any]] = initial_messages
        self.final_response: Optional[ChatCompletionMessage] = None
        self.tool_uses_in_last_turn: List[ChatCompletionMessageToolCall] = []

        # --- Configuration Resolution ---
        # The Agent is responsible for resolving its final LLM configuration.
        resolved_config = base_llm_config.model_copy(deep=True)

        if agent_config.llm:
            # Get the override values, excluding any that are not explicitly set
            overrides = agent_config.llm.model_dump(exclude_unset=True)
            # Update the resolved config with the overrides
            resolved_config = resolved_config.model_copy(update=overrides)

        # The agent's specific system prompt always takes precedence if provided.
        if agent_config.system_prompt:
            resolved_config.default_system_prompt = agent_config.system_prompt

        self.resolved_llm_config: LLMConfig = resolved_config
        self.llm = LiteLLMClient(config=self.resolved_llm_config)

        logger.debug(
            f"Agent '{self.config.name or 'Unnamed'}' initialized with resolved LLM config: {self.resolved_llm_config.model_dump_json(indent=2)}"
        )

    async def run_conversation(self) -> AgentRunResult:
        """
        Runs the agent's conversation loop until a final response is generated
        or the max iteration limit is reached.

        Returns:
            AgentRunResult: An object containing the final status, response,
                            history, and any errors.
        """
        logger.debug(f"Agent starting run for '{self.config.name or 'Unnamed'}'.")
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
                effective_system_prompt=self.resolved_llm_config.default_system_prompt,
            )

            try:
                (
                    final_response_this_turn,
                    tool_results_for_next_turn,
                    is_final_turn,
                ) = await turn_processor.process_turn()

                # Always append the assistant's attempt to the history
                assistant_message = turn_processor.get_last_llm_response()
                if assistant_message:
                    self.conversation_history.append(
                        assistant_message.model_dump(exclude_none=True)
                    )

                # Append tool results if any were generated
                if tool_results_for_next_turn:
                    self.conversation_history.extend(tool_results_for_next_turn)
                    self.tool_uses_in_last_turn = (
                        turn_processor.get_tool_uses_this_turn()
                    )

                if is_final_turn:
                    self.final_response = final_response_this_turn
                    logger.debug("Final response received. Ending conversation.")
                    return AgentRunResult(
                        status="success",
                        final_response=self.final_response,
                        conversation_history=self.conversation_history,
                        error_message=None,
                    )

            except Exception as e:
                error_message = f"Error during conversation turn {current_iteration + 1}: {type(e).__name__}: {e}"
                logger.error(error_message, exc_info=True)
                return AgentRunResult(
                    status="error",
                    final_response=None,
                    conversation_history=self.conversation_history,
                    error_message=error_message,
                )

        logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
        return AgentRunResult(
            status="max_iterations_reached",
            final_response=self.final_response,  # Could be None if no response was ever generated
            conversation_history=self.conversation_history,
            error_message=f"Agent stopped after reaching the maximum of {max_iterations} iterations.",
        )

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
                effective_system_prompt=self.resolved_llm_config.default_system_prompt,
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
                                tool_id = event.get("tool_id")
                                tool_name = event.get("name")
                                tool_args = event.get("arguments")

                                if tool_id and tool_name and tool_args is not None:
                                    message = ChatCompletionAssistantMessageParam(
                                        role="assistant",
                                        tool_calls=[
                                            ChatCompletionMessageToolCallParam(
                                                id=tool_id,
                                                function=Function(
                                                    name=tool_name,
                                                    arguments=tool_args,
                                                ),
                                                type="function",
                                            )
                                        ],
                                    )
                                    self.conversation_history.append(dict(message))
                            case "message_complete":
                                content = event.get("content") or ""
                                message = ChatCompletionAssistantMessageParam(
                                    role="assistant",
                                    content=content,
                                )

                                logger.info(f"Streaming message complete: {content}")

                                self.conversation_history.append(dict(message))

                                # Store as final response if not a tool turn
                                if not is_tool_turn:
                                    # We need to construct a full ChatCompletionMessage
                                    self.final_response = ChatCompletionMessage(
                                        role="assistant", content=content
                                    )
                                    return
                            case "tool_result":
                                tool_results.append(event)
                            case _:
                                raise ValueError(
                                    f"Unrecognized internal type while streaming: {event_type}"
                                )

                # Process tool results if any
                if tool_results:
                    for result in tool_results:
                        tool_message = ChatCompletionToolMessageParam(
                            role="tool",
                            tool_call_id=result["tool_id"],
                            content=result["result"]
                            if result["status"] == "success"
                            else result["error"],
                        )
                        self.conversation_history.append(dict(tool_message))

            except Exception as e:
                logger.error(f"Error in conversation turn {current_iteration}: {e}")
                yield {"type": "error", "error": str(e), "turn": current_iteration}
                break

        logger.warning(
            f"Reached max iterations ({max_iterations}) in stream. Ending conversation."
        )
