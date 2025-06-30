"""
Provides a helper function for dynamically selecting tools for an agent using an LLM.
"""

import json
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

from ..config.config_models import AgentConfig, LLMConfig
from ..components.llm.providers.litellm_client import LiteLLMClient

if TYPE_CHECKING:
    from ..config.config_models import ProjectConfig


logger = logging.getLogger(__name__)


async def select_tools_for_agent(
    agent_config: AgentConfig,
    user_message: str,
    system_prompt_for_agent: Optional[str],
    current_project: "ProjectConfig",
    llm_client_cache: Dict[str, "LiteLLMClient"],
) -> Optional[List[str]]:
    """
    Uses an LLM to dynamically select client_ids for an agent based on the user message,
    agent's system prompt, and available tools.

    Args:
        agent_config: The configuration of the agent for which to select tools.
        user_message: The user's input message to the agent.
        system_prompt_for_agent: The system prompt that will be used for the agent.
        current_project: The active ProjectConfig containing available MCP servers.
        llm_client_cache: A cache of LLM clients to reuse for the selector LLM.

    Returns:
        A list of selected client IDs, or None if the selection process fails.
    """
    logger.debug(
        f"Attempting to dynamically select client_ids for agent '{agent_config.name}'."
    )

    tool_selector_llm_config = LLMConfig(
        llm_id="internal_dynamic_tool_selector_haiku",
        provider="anthropic",
        model_name="claude-3-haiku-20240307",
        temperature=0.2,
        max_tokens=1024,
        default_system_prompt=(
            "You are an expert AI assistant responsible for selecting the most relevant set of tools (MCP Clients) "
            "for another AI agent to accomplish a given task.\n"
            "You will be provided with:\n"
            "1. The user's message to the agent.\n"
            "2. The agent's primary system prompt.\n"
            "3. A list of available tool sets (MCP Clients) with their capabilities.\n"
            "Your goal is to choose the minimal set of tool sets that will provide the necessary capabilities "
            "for the agent to best respond to the user's message, guided by its system prompt.\n"
            'Respond with a JSON object containing a single key "selected_client_ids", which is a list of strings '
            "representing the IDs of the chosen tool sets.\n"
            'If no tool sets are relevant or necessary, return an empty list for "selected_client_ids".'
        ),
    )

    tool_selector_llm_client = llm_client_cache.get(tool_selector_llm_config.llm_id)
    if not tool_selector_llm_client:
        try:
            tool_selector_llm_client = LiteLLMClient(
                model_name=tool_selector_llm_config.model_name
                or "claude-3-haiku-20240307",
                provider=tool_selector_llm_config.provider,
                temperature=tool_selector_llm_config.temperature,
                max_tokens=tool_selector_llm_config.max_tokens,
                system_prompt=tool_selector_llm_config.default_system_prompt,
                api_base=tool_selector_llm_config.api_base,
                api_key=tool_selector_llm_config.api_key,
                api_version=tool_selector_llm_config.api_version,
            )
            llm_client_cache[tool_selector_llm_config.llm_id] = tool_selector_llm_client
            logger.debug(
                f"Created and cached LLM client for tool selection: {tool_selector_llm_config.llm_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create LLM client for tool selection: {e}", exc_info=True
            )
            return None
    else:
        logger.debug(
            f"Reusing cached LLM client for tool selection: {tool_selector_llm_config.llm_id}"
        )

    available_clients = current_project.mcp_servers
    client_info_parts = ["Available Tool Sets (MCP Clients):"]
    if not available_clients:
        client_info_parts.append("No tool sets are currently available.")
    else:
        for client_id, client_cfg in available_clients.items():
            client_capabilities = set(client_cfg.capabilities or [])
            root_names = []
            for root in client_cfg.roots:
                client_capabilities.update(root.capabilities or [])
                root_names.append(root.name)

            cap_string = (
                ", ".join(sorted(list(client_capabilities)))
                if client_capabilities
                else "None"
            )
            roots_string = ", ".join(root_names) if root_names else "N/A"
            client_info_parts.append(
                f"---\nTool Set ID: {client_id}\nCapabilities: {cap_string}\nRoot Names: {roots_string}"
            )
    client_info_parts.append("---")

    prompt_for_tool_selection_llm_parts = [
        *client_info_parts,
        "\nAgent's System Prompt:",
        system_prompt_for_agent or "No system prompt provided for the agent.",
        "\nUser's Message to Agent:",
        user_message,
        "\nBased on the Agent's System Prompt and the User's Message, which tool sets should be selected?",
    ]
    prompt_content_for_tool_selection = "\n".join(prompt_for_tool_selection_llm_parts)

    tool_selection_schema = {
        "type": "object",
        "properties": {
            "selected_client_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of client_ids that should be selected for the agent.",
            }
        },
        "required": ["selected_client_ids"],
    }

    try:
        response_message = await tool_selector_llm_client.create_message(
            messages=[{"role": "user", "content": prompt_content_for_tool_selection}],
            tools=None,
            schema=tool_selection_schema,
            llm_config_override=tool_selector_llm_config,
        )

        if not response_message.content:
            logger.error("Tool selection LLM returned empty content.")
            return None

        llm_response_text = response_message.content
        parsed_response = json.loads(llm_response_text)
        selected_ids_from_llm = parsed_response.get("selected_client_ids")

        if selected_ids_from_llm is None or not isinstance(selected_ids_from_llm, list):
            logger.error(
                f"Tool selection LLM response missing 'selected_client_ids' list or invalid format: {llm_response_text}"
            )
            return None

        valid_selected_ids = [
            client_id
            for client_id in selected_ids_from_llm
            if isinstance(client_id, str) and client_id in available_clients
        ]

        if len(valid_selected_ids) != len(selected_ids_from_llm):
            logger.warning(
                "Some selected client_ids were invalid and have been ignored."
            )

        logger.info(
            f"Dynamically selected client_ids: {valid_selected_ids} (Agent: {agent_config.name})"
        )
        return valid_selected_ids

    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse JSON response from tool selection LLM: {e}\nResponse: {llm_response_text}",
            exc_info=True,
        )
        return None
    except Exception as e:
        logger.error(
            f"Error during LLM call for dynamic tool selection: {e}", exc_info=True
        )
        return None
