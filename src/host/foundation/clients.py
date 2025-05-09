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
            # The transport itself is a tuple (reader, writer) as stdio_client's context manager yields this.
            # The process object is managed internally by the stdio_client context manager.
            transport_tuple = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            # self.client_processes[client_id] = transport_tuple[0] # This was incorrect; stdio_client's __aenter__ returns (reader, writer)
            # The process is managed by the stdio_client context manager itself.
            logger.debug(f"stdio_client transport acquired for {client_id}.")

            # Create the ClientSession using the reader and writer from the transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(
                    transport_tuple[0], transport_tuple[1]
                )  # Corrected indices for reader and writer
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
            # No direct process handle to kill here if stdio_client context failed to enter or during its management.
            # AsyncExitStack will handle cleanup of successfully entered contexts.
            if (
                client_id in self.active_clients
            ):  # Should not happen if session failed after transport
                del self.active_clients[client_id]
            # self.client_processes dictionary is no longer used to store direct process handles from stdio_client
            if client_id in self.client_processes:
                del self.client_processes[
                    client_id
                ]  # Clean up if it was somehow added before error
            raise  # Re-throw the original exception

    async def shutdown_client(self, client_id: str):
        """
        Shuts down a specific client session. The underlying process is managed
        by the AsyncExitStack via the stdio_client context manager.

        Args:
            client_id: The ID of the client to shut down.
        """
        logger.info(f"Shutting down client: {client_id}...")
        session = self.active_clients.pop(client_id, None)
        # Process is managed by stdio_client context manager within AsyncExitStack
        process_details_removed = self.client_processes.pop(
            client_id, None
        )  # Keep for now if other types of clients might store process details

        if session:
            try:
                # ClientSession doesn't have an explicit close/shutdown in mcp-py's public API.
                # The AsyncExitStack handles closing the reader/writer streams when the
                # ClientSession context and stdio_client context are exited.
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

        # The stdio_client context manager (managed by AsyncExitStack) is responsible
        # for terminating the subprocess when its context is exited.
        # We don't manually terminate `process` here if it came from `stdio_client`.
        if process_details_removed:  # If we were storing other process types
            logger.debug(
                f"Removed process details for client {client_id}. Process termination handled by context manager."
            )
        elif (
            not session and not process_details_removed
        ):  # only log if neither was found
            logger.info(f"Client {client_id} was not active or already shut down.")
        elif (
            not session and process_details_removed
        ):  # If session was gone but process details remained
            logger.warning(
                f"Process details found for {client_id} but no active session. Cleanup handled by context manager."
            )

    async def shutdown_all_clients(self):
        """
        Shuts down all active client sessions. Processes are managed by AsyncExitStack.
        """
        logger.info("Shutting down all active clients...")
        # Create a list of client IDs to avoid issues with modifying dict during iteration
        client_ids_to_shutdown = list(self.active_clients.keys())
        for client_id in client_ids_to_shutdown:
            await self.shutdown_client(client_id)  # This will pop from active_clients

        # Ensure dictionaries are cleared, though shutdown_client should handle individual removals
        self.active_clients.clear()
        self.client_processes.clear()  # Clear any stored process details
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
