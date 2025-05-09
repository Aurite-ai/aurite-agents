"""
ClientManager for handling MCP client subprocesses and sessions.
"""

import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, Optional

from mcp import ClientSession, StdioServerParameters, stdio_client

# Assuming SecurityManager and ClientConfig are accessible for import
# Adjust import paths as necessary based on actual project structure
from ...config.config_models import ClientConfig
from ..foundation.security import (
    SecurityManager,
)  # Assuming SecurityManager is in foundation

logger = logging.getLogger(__name__)


class ClientManager:
    """
    Manages the lifecycle of MCP client (server subprocess) connections,
    including starting, stopping, and tracking them.
    """

    def __init__(self, exit_stack: AsyncExitStack):
        """
        Initializes the ClientManager.

        Args:
            exit_stack: An AsyncExitStack for managing the lifecycle of
                        client subprocesses and sessions.
        """
        self.exit_stack: AsyncExitStack = exit_stack
        self.active_clients: Dict[str, ClientSession] = {}
        self.client_processes: Dict[str, Any] = {}  # Stores subprocess handles
        logger.debug("ClientManager initialized.")

    async def start_client(
        self, client_config: ClientConfig, security_manager: SecurityManager
    ) -> ClientSession:
        """
        Starts a new client subprocess and establishes a ClientSession.

        Args:
            client_config: The configuration for the client to start.
            security_manager: The security manager for resolving secrets.

        Returns:
            The established ClientSession.

        Raises:
            Exception: If client startup or session establishment fails.
        """
        client_id = client_config.client_id
        logger.info(f"Starting client: {client_id}...")

        if client_id in self.active_clients:
            logger.error(f"Client {client_id} is already active.")
            # Or raise an error, depending on desired behavior for re-starting
            # For now, let's assume this shouldn't happen if called correctly.
            raise ValueError(f"Client {client_id} is already active.")

        try:
            client_env = os.environ.copy()
            if client_config.gcp_secrets and security_manager:
                logger.info(f"Resolving GCP secrets for client: {client_id}")
                try:
                    resolved_env_vars = await security_manager.resolve_gcp_secrets(
                        client_config.gcp_secrets
                    )
                    if resolved_env_vars:
                        client_env.update(resolved_env_vars)
                        logger.info(
                            f"Injected {len(resolved_env_vars)} secrets into environment for client: {client_id}"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to resolve GCP secrets for client {client_id}: {e}. Proceeding without them.",
                        exc_info=True,
                    )

            server_params = StdioServerParameters(
                command="python",  # Assuming python, could be configurable
                args=[str(client_config.server_path)],  # server_path should be absolute
                env=client_env,
            )
            logger.debug(
                f"Attempting to start stdio_client for {client_id} with command: "
                f"{server_params.command} {' '.join(server_params.args)}"
            )

            # Start the server process and get transport
            # The transport itself is a tuple (process, reader, writer)
            # We store the process handle for later termination.
            transport_tuple = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            # transport_tuple[0] is the process, transport_tuple[1] is reader, transport_tuple[2] is writer
            self.client_processes[client_id] = transport_tuple[0]  # Store the process
            logger.debug(
                f"stdio_client transport acquired for {client_id}, process stored."
            )

            # Create the ClientSession using the reader and writer from the transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(transport_tuple[1], transport_tuple[2])
            )
            logger.debug(f"ClientSession created for {client_id}")

            self.active_clients[client_id] = session
            logger.info(
                f"Client {client_id} started and session established successfully."
            )
            return session

        except Exception as e:
            logger.error(f"Failed to start client {client_id}: {e}", exc_info=True)
            # Clean up if process started but session failed, or other partial failures
            if client_id in self.client_processes:
                try:
                    # Attempt to terminate the process if it was started
                    process_to_kill = self.client_processes[client_id]
                    if hasattr(process_to_kill, "terminate"):
                        process_to_kill.terminate()
                    await process_to_kill.wait()  # Wait for termination
                except Exception as cleanup_err:
                    logger.error(
                        f"Error during cleanup of failed client {client_id}: {cleanup_err}"
                    )
                del self.client_processes[client_id]
            if client_id in self.active_clients:  # Should not happen if session failed
                del self.active_clients[client_id]
            raise  # Re-throw the original exception

    async def shutdown_client(self, client_id: str):
        """
        Shuts down a specific client session and its subprocess.

        Args:
            client_id: The ID of the client to shut down.
        """
        logger.info(f"Shutting down client: {client_id}...")
        session = self.active_clients.pop(client_id, None)
        process = self.client_processes.pop(client_id, None)

        if session:
            try:
                # ClientSession doesn't have an explicit close/shutdown in mcp-py's public API
                # The AsyncExitStack handles closing the reader/writer streams.
                logger.debug(
                    f"Session for client {client_id} will be closed by AsyncExitStack."
                )
            except Exception as e:
                logger.error(
                    f"Error during (implicit) session shutdown for client {client_id}: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"No active session found for client {client_id} to shutdown."
            )

        if process:
            try:
                logger.debug(f"Terminating process for client {client_id}...")
                if hasattr(process, "terminate"):
                    process.terminate()
                await process.wait()  # Ensure process is terminated
                logger.info(f"Process for client {client_id} terminated.")
            except Exception as e:
                logger.error(
                    f"Error terminating process for client {client_id}: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"No active process found for client {client_id} to terminate."
            )

        if not session and not process:
            logger.info(f"Client {client_id} was not active or already shut down.")

    async def shutdown_all_clients(self):
        """
        Shuts down all active client sessions and their subprocesses.
        """
        logger.info("Shutting down all active clients...")
        # Create a list of client IDs to avoid issues with modifying dict during iteration
        client_ids_to_shutdown = list(self.active_clients.keys())
        for client_id in client_ids_to_shutdown:
            await self.shutdown_client(client_id)

        # Ensure dictionaries are cleared, though shutdown_client should handle individual removals
        self.active_clients.clear()
        self.client_processes.clear()
        logger.info("All active clients have been processed for shutdown.")

    def get_session(self, client_id: str) -> Optional[ClientSession]:
        """
        Retrieves the active session for a given client ID.

        Args:
            client_id: The ID of the client.

        Returns:
            The ClientSession if active, otherwise None.
        """
        return self.active_clients.get(client_id)

    def get_all_sessions(self) -> Dict[str, ClientSession]:
        """
        Returns a dictionary of all active client sessions.
        """
        return self.active_clients.copy()  # Return a copy
