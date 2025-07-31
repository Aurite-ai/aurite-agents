"""
Manages the multi-turn conversation loop for an Agent.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageToolCallParam,
    ChatCompletionToolMessageParam,
)
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function

from ...config.config_models import AgentConfig, LLMConfig
from ...host.host import MCPHost
from ..llm.litellm_client import LiteLLMClient
from .agent_models import AgentRunResult
from .agent_turn_processor import AgentTurnProcessor

if TYPE_CHECKING:
    from langfuse.client import StatefulTraceClient


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
        session_id: Optional[str] = None,
        trace: Optional["StatefulTraceClient"] = None,
    ):
        self.config = agent_config
        self.host = host_instance
        self.conversation_history: List[Dict[str, Any]] = initial_messages
        self.final_response: Optional[ChatCompletionMessage] = None
        self.tool_uses_in_last_turn: List[ChatCompletionMessageToolCall] = []
        self.session_id = session_id
        self.trace = trace

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

    def _create_turn_processor(self) -> AgentTurnProcessor:
        """Creates and configures an AgentTurnProcessor for the current turn."""
        tools_data = self.host.get_formatted_tools(agent_config=self.config)
        return AgentTurnProcessor(
            config=self.config,
            llm_client=self.llm,
            host_instance=self.host,
            current_messages=self.conversation_history,
            tools_data=tools_data,
            effective_system_prompt=self.resolved_llm_config.default_system_prompt,
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
        max_iterations = self.config.max_iterations or 10

        for current_iteration in range(max_iterations):
            logger.debug(f"Conversation loop iteration {current_iteration + 1}")

            turn_processor = self._create_turn_processor()

            try:
                (
                    final_response_this_turn,
                    tool_results_for_next_turn,
                    is_final_turn,
                ) = await turn_processor.process_turn()

                # Always append the assistant's attempt to the history
                assistant_message = turn_processor.get_last_llm_response()
                if assistant_message:
                    self.conversation_history.append(assistant_message.model_dump(exclude_none=True))

                # Append tool results if any were generated
                if tool_results_for_next_turn:
                    self.conversation_history.extend(tool_results_for_next_turn)
                    self.tool_uses_in_last_turn = turn_processor.get_tool_uses_this_turn()

                if is_final_turn:
                    self.final_response = final_response_this_turn
                    logger.debug("Final response received. Ending conversation.")
                    # Convert to OpenAI type before validation
                    if self.final_response:
                        self.final_response = ChatCompletionMessage.model_validate(self.final_response.model_dump())
                    return AgentRunResult(
                        status="success",
                        final_response=self.final_response,
                        conversation_history=self.conversation_history,
                        error_message=None,
                        session_id=self.session_id,
                    )

            except Exception as e:
                error_message = f"Error during conversation turn {current_iteration + 1}: {type(e).__name__}: {e}"
                logger.error(error_message)
                return AgentRunResult(
                    status="error",
                    final_response=None,
                    conversation_history=self.conversation_history,
                    error_message=error_message,
                    session_id=self.session_id,
                    exception=e,
                )

        logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
        return AgentRunResult(
            status="max_iterations_reached",
            final_response=self.final_response,  # Could be None if no response was ever generated
            conversation_history=self.conversation_history,
            error_message=f"Agent stopped after reaching the maximum of {max_iterations} iterations.",
            session_id=self.session_id,
        )

    async def stream_conversation(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams the agent's conversation, handling multiple turns and tool executions.
        This method acts as a translator, consuming the raw event stream from the
        turn processor and yielding a standardized, UI-friendly event stream.
        """
        logger.info(f"Starting streaming conversation for agent '{self.config.name or 'Unnamed'}'")

        max_iterations = self.config.max_iterations or 10
        llm_started = False

        for current_iteration in range(max_iterations):
            logger.debug(f"Starting conversation turn {current_iteration + 1}")

            turn_processor = self._create_turn_processor()

            try:
                is_tool_turn = False
                tool_results = []
                current_tool_name = None

                async for event in turn_processor.stream_turn_response():
                    # --- Event Translation Logic ---

                    # It's a raw litellm chunk for text delta
                    if "choices" in event:
                        if not event["choices"]:
                            continue
                        delta = event["choices"][0].get("delta", {})
                        if delta.get("role") == "assistant" and not llm_started:
                            yield {"type": "llm_response_start", "data": {}}
                            llm_started = True
                        if content := delta.get("content"):
                            yield {"type": "llm_response", "data": {"content": content}}
                        continue

                    # It's a structured internal event
                    if event.get("internal"):
                        event_type = event["type"]

                        if event_type == "tool_complete":
                            is_tool_turn = True
                            current_tool_name = event.get("name")
                            if not current_tool_name:
                                logger.error("Tool name missing in 'tool_complete' event.")
                                continue  # Skip this malformed event

                            tool_args_str = event.get("arguments", "{}")
                            try:
                                tool_args = json.loads(tool_args_str)
                            except json.JSONDecodeError:
                                tool_args = {"raw_arguments": tool_args_str}

                            yield {"type": "tool_call", "data": {"name": current_tool_name, "input": tool_args}}

                            # Update history for the next turn
                            message = ChatCompletionAssistantMessageParam(
                                role="assistant",
                                tool_calls=[
                                    ChatCompletionMessageToolCallParam(
                                        id=event["tool_id"],
                                        function=Function(name=current_tool_name, arguments=tool_args_str),
                                        type="function",
                                    )
                                ],
                            )
                            self.conversation_history.append(dict(message))

                        elif event_type == "tool_result":
                            tool_results.append(event)  # Collect for history
                            yield {
                                "type": "tool_output",
                                "data": {"name": current_tool_name, "output": event.get("result")},
                            }

                        elif event_type == "message_complete":
                            content = event.get("content", "")
                            self.conversation_history.append({"role": "assistant", "content": content})
                            yield {"type": "llm_response_stop", "data": {}}
                            if not is_tool_turn:
                                return  # End of conversation

                # After the turn, append all tool results to history
                if tool_results:
                    for result in tool_results:
                        tool_message = ChatCompletionToolMessageParam(
                            role="tool",
                            tool_call_id=result["tool_id"],
                            content=result["result"] if result["status"] == "success" else result["error"],
                        )
                        self.conversation_history.append(dict(tool_message))

            except Exception as e:
                logger.error(f"Error in conversation turn {current_iteration}: {e}")
                yield {"type": "error", "data": {"message": str(e)}}
                return

        logger.warning(f"Reached max iterations ({max_iterations}) in stream. Ending conversation.")
