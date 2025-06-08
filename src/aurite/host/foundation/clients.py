"""
ClientManager for handling MCP client subprocesses and sessions.
"""

import logging
import os
import re
from pathlib import Path
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
        client_id = client_config.name
        session_started = False  # Flag to track if started() has been called

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

                    # Correctly handle both absolute and relative paths
                    server_path_obj = Path(client_config.server_path)
                    if not server_path_obj.is_absolute():
                        server_path_obj = server_path_obj.resolve()

                    server_params = StdioServerParameters(
                        command="python",
                        args=[str(server_path_obj)],
                        env=client_env,
                        cwd=str(server_path_obj.parent),
                    )
                    logger.debug(
                        f"Attempting to start stdio_client for {client_id} with command: "
                        f"{server_params.command} {' '.join(server_params.args)} in CWD: {server_params.cwd}"
                    )
                    transport_context = stdio_client(
                        server_params, errlog=open(os.devnull, "w")
                    )

                elif client_config.transport_type == "http_stream":  # Use http_stream
                    if not client_config.http_endpoint:  # Use http_endpoint
                        raise ValueError(
                            "http_endpoint is required for http_stream transport"
                        )

                    endpoint_url = client_config.http_endpoint

                    # Resolve environment variable placeholders in the URL
                    placeholders = re.findall(r"\{([^}]+)\}", endpoint_url)
                    for placeholder in placeholders:
                        env_value = os.getenv(placeholder)
                        if env_value:
                            endpoint_url = endpoint_url.replace(
                                f"{{{placeholder}}}", env_value
                            )
                        else:
                            raise ValueError(
                                f"Could not resolve placeholder '{{{placeholder}}}' in http_endpoint for client '{client_id}'. "
                                f"Please ensure the environment variable '{placeholder}' is set."
                            )

                    # Check for DOCKER_ENV environment variable
                    if os.environ.get("DOCKER_ENV", "false").lower() == "true":
                        if "localhost" in endpoint_url:
                            endpoint_url = endpoint_url.replace(
                                "localhost", "host.docker.internal"
                            )
                            logger.info(
                                f"DOCKER_ENV is true, updated http_endpoint to: {endpoint_url}"
                            )

                    logger.debug(
                        f"Attempting to connect streamablehttp_client for {client_id} to URL: {endpoint_url}"
                    )
                    transport_context = streamablehttp_client(endpoint_url)

                elif client_config.transport_type == "local":
                    if not client_config.command:
                        raise ValueError("command is required for stdio transport")
                    if not client_config.args:
                        raise ValueError("args is required for stdio transport")

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

                    # update args to replace env values
                    updated_args = []
                    for arg in client_config.args:
                        env_vars = re.findall(r"\{([^}]+)\}", arg)

                        for var in env_vars:
                            if var in client_env:
                                arg = arg.replace(f"{{{var}}}", client_env[var])

                        updated_args.append(arg)

                    server_params = StdioServerParameters(
                        command=client_config.command,
                        args=updated_args,
                        env=client_env,
                    )
                    logger.debug(
                        f"Attempting to start local stdio_client for {client_id} with command: "
                        f"{server_params.command} {' '.join(server_params.args)} in CWD: {server_params.cwd}"
                    )
                    transport_context = stdio_client(
                        server_params, errlog=open(os.devnull, "w")
                    )
                else:
                    raise ValueError(
                        f"Unsupported transport_type: {client_config.transport_type}"
                    )

                async with anyio.create_task_group() as tg:
                    async with transport_context as transport_streams:
                        logger.debug(
                            f"Transport streams established for {client_id} with {client_config.transport_type} in Task Group {tg}."
                        )
                        reader, writer = transport_streams[0], transport_streams[1]
                        logger.debug(
                            f"{client_config.transport_type} transport acquired for {client_id}."
                        )
                        async with ClientSession(reader, writer) as session:
                            self.active_clients[client_id] = session
                            logger.debug(
                                f"ClientSession created and stored for {client_id}."
                            )

                            # Signal MCPHost that session is ready and pass it back
                            task_status.started(session)
                            session_started = True  # Set the flag
                            logger.debug(
                                f"Task for client {client_id}: Session established and reported. Running until cancelled."
                            )

                            never_set_event = anyio.Event()
                            await never_set_event.wait()

        except anyio.get_cancelled_exc_class():
            logger.debug(f"Client lifecycle task for {client_id} cancelled.")
        except Exception as e:
            logger.error(
                f"Error in client lifecycle task for {client_id}: {e}", exc_info=True
            )
            # If an error occurs before task_status.started() is called, the exception
            # will be propagated by the task group's start() method. If it occurs after,
            # we must re-raise it to ensure the task group sees the failure.
            if not session_started:
                # Let the error propagate via the start() mechanism.
                # No need to re-raise here as anyio handles it.
                pass
            else:
                # If started() was called, the error would be suppressed unless re-raised.
                raise
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
