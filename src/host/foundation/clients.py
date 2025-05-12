"""
ClientManager for handling MCP client subprocesses and sessions.
"""

import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, Optional

from mcp import ClientSession, StdioServerParameters, stdio_client

# Assuming SecurityManager and ClientConfig are accessible for import
import anyio # Import anyio
from anyio.abc import TaskStatus # For type hinting task_status

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

    def __init__(self):
        """
        Initializes the ClientManager.
        """
        self.active_clients: Dict[str, ClientSession] = {}
        logger.debug("ClientManager initialized.")

    async def manage_client_lifecycle(
        self,
        client_config: ClientConfig,
        security_manager: SecurityManager,
        client_cancel_scope: anyio.CancelScope,
        *,
        task_status: TaskStatus[ClientSession],
    ):
        """
        Manages the complete lifecycle of a single client connection,
        including startup, session management, and shutdown.
        This method is intended to be run as a task within an AnyIO TaskGroup.
        """
        client_id = client_config.client_id
        session_instance = None  # To hold the session if successfully created

        try:
            with client_cancel_scope: # Enter the passed-in cancel scope
                logger.debug(f"Task for client {client_id}: Starting stdio_client and ClientSession.")

                client_env = os.environ.copy()
                if client_config.gcp_secrets and security_manager:
                    logger.debug(f"Resolving GCP secrets for client: {client_id}")
                    try:
                        resolved_env_vars = await security_manager.resolve_gcp_secrets(
                            client_config.gcp_secrets
                        )
                        if resolved_env_vars:
                            client_env.update(resolved_env_vars)
                            logger.debug(
                                f"Injected {len(resolved_env_vars)} secrets into environment for client: {client_id}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to resolve GCP secrets for client {client_id}: {e}. Proceeding without them.",
                            exc_info=True,
                        )

                server_params = StdioServerParameters(
                    command="python",
                    args=[str(client_config.server_path.resolve())], # Ensure path is resolved
                    env=client_env,
                    cwd=str(client_config.server_path.parent.resolve()) # Set CWD to server's directory
                )
                logger.debug(
                    f"Attempting to start stdio_client for {client_id} with command: "
                    f"{server_params.command} {' '.join(server_params.args)} in CWD: {server_params.cwd}"
                )

                async with stdio_client(server_params) as (reader, writer):
                    logger.debug(f"stdio_client transport acquired for {client_id}.")
                    async with ClientSession(reader, writer) as session:
                        session_instance = session
                        self.active_clients[client_id] = session
                        logger.debug(f"ClientSession created and stored for {client_id}.")

                        # Signal MCPHost that session is ready and pass it back
                        task_status.started(session)
                        logger.debug(f"Task for client {client_id}: Session established and reported. Running until cancelled.")

                        # Keep the task alive until its cancel scope is cancelled
                        await anyio.sleep_forever()

        except anyio.get_cancelled_exc_class():
            logger.info(f"Client lifecycle task for {client_id} cancelled.")
        except Exception as e:
            logger.error(f"Error in client lifecycle task for {client_id}: {e}", exc_info=True)
            # If task_status.started() hasn't been called yet, and an error occurs,
            # anyio's task_group.start() will re-raise this error in the parent task.
            # If it was already called, the error propagates to the task group's __aexit__.
            if session_instance is None and hasattr(task_status, "_future") and not task_status._future.done():
                 # This is a bit of a hack to check if started() was called; normally TaskStatus doesn't expose _future
                 # A more robust way might be to set a flag after calling started().
                 # For now, if an error occurs before session is established, it will be raised by tg.start()
                 pass # Error will be propagated by tg.start() if started() not called.
            raise # Re-raise to ensure task group sees the error if it occurs after started()
        finally:
            logger.info(f"Cleaning up client {client_id} resources in ClientManager.")
            self.active_clients.pop(client_id, None)
            # __aexit__ of ClientSession and stdio_client are automatically called here
            # due to the `async with` blocks exiting.

    # Old lifecycle methods are removed.
    # start_client, shutdown_client, shutdown_all_clients are now handled by
    # manage_client_lifecycle and the controlling logic in MCPHost.

    def get_session(self, client_id: str) -> Optional[ClientSession]:
        """
        Retrieves the active session for a given client ID.
        (This method remains as it's a simple getter)

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
