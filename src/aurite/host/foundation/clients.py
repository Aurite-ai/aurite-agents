"""
ClientManager for handling MCP client subprocesses and sessions.
"""

import logging
import os
from typing import Dict, Optional

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import (
    streamablehttp_client,
)  # Import streamablehttp_client
# from mcp.client.sse import sse_client # Comment out sse_client

# Assuming SecurityManager and ClientConfig are accessible for import
import anyio  # Import anyio
from anyio.abc import TaskStatus  # For type hinting task_status

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
            with client_cancel_scope:  # Enter the passed-in cancel scope
                logger.debug(
                    f"Task for client {client_id}: Establishing transport and ClientSession."
                )

                transport_context = None
                if client_config.transport_type == "stdio":
                    if not client_config.server_path:
                        raise ValueError("server_path is required for stdio transport")

                    client_env = os.environ.copy()
                    if client_config.gcp_secrets and security_manager:
                        logger.debug(f"Resolving GCP secrets for client: {client_id}")
                        try:
                            resolved_env_vars = (
                                await security_manager.resolve_gcp_secrets(
                                    client_config.gcp_secrets
                                )
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
                        command="python",  # Or make this configurable if needed
                        args=[str(client_config.server_path.resolve())],
                        env=client_env,
                        cwd=str(client_config.server_path.parent.resolve()),
                    )
                    logger.debug(
                        f"Attempting to start stdio_client for {client_id} with command: "
                        f"{server_params.command} {' '.join(server_params.args)} in CWD: {server_params.cwd}"
                    )
                    transport_context = stdio_client(server_params)

                elif client_config.transport_type == "http_stream":  # Use http_stream
                    if not client_config.http_endpoint:  # Use http_endpoint
                        raise ValueError(
                            "http_endpoint is required for http_stream transport"
                        )

                    endpoint_url = client_config.http_endpoint
                    # Check for DOCKER_ENV environment variable
                    if os.environ.get("DOCKER_ENV", "false").lower() == "true":
                        if endpoint_url.startswith("http://localhost"):
                            endpoint_url = endpoint_url.replace(
                                "http://localhost", "http://host.docker.internal", 1
                            )
                            logger.info(
                                f"DOCKER_ENV is true, updated http_endpoint to: {endpoint_url}"
                            )
                        elif endpoint_url.startswith(
                            "https://localhost"
                        ):  # Also handle https if necessary
                            endpoint_url = endpoint_url.replace(
                                "https://localhost", "https://host.docker.internal", 1
                            )
                            logger.info(
                                f"DOCKER_ENV is true, updated http_endpoint to: {endpoint_url}"
                            )

                    logger.debug(
                        f"Attempting to connect streamablehttp_client for {client_id} to URL: {endpoint_url}"
                    )
                    transport_context = streamablehttp_client(
                        endpoint_url
                    )  # Use streamablehttp_client

                else:
                    raise ValueError(
                        f"Unsupported transport_type: {client_config.transport_type}"
                    )

                async with (
                    transport_context as transport_streams
                ):  # streamablehttp_client yields (reader, writer, get_session_id_callback)
                    reader, writer = transport_streams[0], transport_streams[1]
                    # get_session_id_callback = transport_streams[2] # We don't need this for ClientSession
                    logger.debug(
                        f"{client_config.transport_type} transport acquired for {client_id}."
                    )
                    async with ClientSession(reader, writer) as session:
                        session_instance = session
                        self.active_clients[client_id] = session
                        logger.debug(
                            f"ClientSession created and stored for {client_id}."
                        )

                        # Signal MCPHost that session is ready and pass it back
                        task_status.started(session)
                        logger.debug(
                            f"Task for client {client_id}: Session established and reported. Running until cancelled."
                        )

                        # Keep the task alive until its cancel scope is cancelled
                        # await anyio.sleep_forever() # Replaced with an event
                        # Create an event that will never be set, to wait for cancellation
                        # This is a cleaner way to wait for cancellation than sleep_forever
                        # in some contexts, though sleep_forever should also work with cancellation.
                        never_set_event = anyio.Event()
                        await never_set_event.wait()

        except anyio.get_cancelled_exc_class():
            logger.debug(f"Client lifecycle task for {client_id} cancelled.")
        except Exception as e:
            logger.error(
                f"Error in client lifecycle task for {client_id}: {e}", exc_info=True
            )
            # If task_status.started() hasn't been called yet, and an error occurs,
            # anyio's task_group.start() will re-raise this error in the parent task.
            # If it was already called, the error propagates to the task group's __aexit__.
            if (
                session_instance is None
                and hasattr(task_status, "_future")
                and not task_status._future.done()
            ):
                # This is a bit of a hack to check if started() was called; normally TaskStatus doesn't expose _future
                # A more robust way might be to set a flag after calling started().
                # For now, if an error occurs before session is established, it will be raised by tg.start()
                pass  # Error will be propagated by tg.start() if started() not called.
            raise  # Re-raise to ensure task group sees the error if it occurs after started()
        finally:
            logger.debug(
                f"Client {client_id}: Entering manage_client_lifecycle finally block."
            )
            self.active_clients.pop(client_id, None)
            logger.debug(
                f"Client {client_id}: Popped from active_clients. Exiting async with blocks now..."
            )
            # __aexit__ of ClientSession and stdio_client are automatically called here
            # due to the `async with` blocks exiting.
        logger.debug(
            f"Client {client_id}: Exited manage_client_lifecycle finally block."
        )

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
