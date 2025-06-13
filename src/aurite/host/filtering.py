"""
Filtering Manager for MCP Host.

This module provides a centralized FilteringManager class responsible for applying
various filtering rules based on ClientConfig and AgentConfig settings.
"""

import logging
from typing import List, Dict, Any

# Import necessary types and models
from aurite.config.config_models import ClientConfig, AgentConfig
# from .foundation import MessageRouter  # MessageRouter is not used

logger = logging.getLogger(__name__)


class FilteringManager:
    """
    Manages all component filtering logic for the MCP Host.

    This includes:
    - Client-level exclusions during registration (`ClientConfig.exclude`).
    - Agent-level client selection during runtime (`AgentConfig.client_ids`).
    - Agent-level component exclusions during runtime (`AgentConfig.exclude_components`).
    """

    def __init__(self):
        """
        Initialize the FilteringManager.
        """
        # self._message_router = message_router # Removed as it's not used by current methods
        logger.debug("FilteringManager initialized.")  # INFO -> DEBUG

    def is_registration_allowed(
        self, component_name: str, client_config: ClientConfig
    ) -> bool:
        """
        Checks if a component should be registered based on the client's exclude list.

        Args:
            component_name: The name of the component (tool, prompt, resource).
            client_config: The configuration of the client providing the component.

        Returns:
            True if the component is allowed to be registered, False otherwise.
        """
        if client_config.exclude and component_name in client_config.exclude:
            logger.debug(
                f"Component '{component_name}' registration denied for client "
                f"'{client_config.name}' due to ClientConfig.exclude."
            )
            return False
        return True

    def filter_clients_for_request(
        self, available_clients: List[str], agent_config: AgentConfig
    ) -> List[str]:
        """
        Filters a list of clients based on the agent's allowed mcp_servers.

        Args:
            available_clients: A list of client IDs that potentially provide the requested component.
            agent_config: The configuration of the agent making the request.

        Returns:
            A filtered list of client IDs that the agent is allowed to use.
        """
        if agent_config.mcp_servers is None:
            # Agent is allowed to use any client
            return available_clients
        else:
            # Filter available clients by the agent's allowed list
            allowed_clients = [
                client_id
                for client_id in available_clients
                if client_id in agent_config.mcp_servers
            ]
            logger.debug(
                f"Filtered available clients {available_clients} to {allowed_clients} "
                f"based on AgentConfig.mcp_servers for agent '{agent_config.name}'."
            )
            return allowed_clients

    def is_component_allowed_for_agent(
        self, component_name: str, agent_config: AgentConfig
    ) -> bool:
        """
        Checks if a specific component is allowed for an agent based on its exclude_components list.

        Args:
            component_name: The name of the component (tool, prompt, resource).
            agent_config: The configuration of the agent making the request.

        Returns:
            True if the component is allowed for the agent, False otherwise.
        """
        if (
            agent_config.exclude_components
            and component_name in agent_config.exclude_components
        ):
            logger.debug(
                f"Component '{component_name}' denied for agent '{agent_config.name}' "
                f"due to AgentConfig.exclude_components."
            )
            return False
        return True

    def filter_component_list(
        self, components: List[Dict[str, Any]], agent_config: AgentConfig
    ) -> List[Dict[str, Any]]:
        """
        Filters a list of component dictionaries (e.g., tools for LLM)
        based on the agent's exclude_components list.

        Assumes each dictionary in the list has a 'name' key.

        Args:
            components: A list of dictionaries, each representing a component.
            agent_config: The configuration of the agent.

        Returns:
            A filtered list of component dictionaries.
        """
        if not agent_config.exclude_components:
            # No agent-specific exclusions, return the original list
            return components

        filtered_components = [
            comp
            for comp in components
            if comp.get("name") not in agent_config.exclude_components
        ]

        if len(filtered_components) < len(components):
            excluded_count = len(components) - len(filtered_components)
            logger.debug(
                f"Filtered out {excluded_count} components for agent '{agent_config.name}' "
                f"based on AgentConfig.exclude_components."
            )

        return filtered_components

    # Potential future enhancement:
    # async def get_allowed_clients_for_component(
    #     self, component_name: str, component_type: str, agent_config: AgentConfig
    # ) -> List[str]:
    #     """Combines router lookup and filtering."""
    #     # 1. Use self._message_router to find all clients for component_name/type
    #     # 2. Use self.filter_clients_for_request to filter based on agent_config.client_ids
    #     # 3. (Maybe?) Check is_component_allowed_for_agent here too, though it might be better checked just before execution.
    #     pass
