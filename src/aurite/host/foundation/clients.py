"""
ClientManager for handling MCP client subprocesses and sessions.
"""

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Optional

import httpx
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import (
    streamablehttp_client,
)

import anyio
from anyio.abc import TaskStatus

from ...config.config_models import ClientConfig
from ..foundation.security import SecurityManager

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
        task_status: TaskStatus[Optional[ClientSession]],
    ):
        """
        Manages the complete lifecycle of a single client connection.
        This task will attempt to connect, and if successful, will run until cancelled.
        If the initial connection fails, it signals this failure and exits gracefully.
        """
        client_id = client_config.name
        session: Optional[ClientSession] = None

        try:
            # --- 1. Connection Attempt ---
            logger.debug(f"Task for client {client_id}: Attempting to connect...")
            transport_context = None
            if client_config.transport_type == "stdio":
                if not client_config.server_path:
                    raise ValueError("server_path is required for stdio transport")

                # Pre-flight check for the python command
                if not shutil.which("python"):
                    logger.error(
                        f"Pre-flight check failed for client {client_id}: 'python' command not found in PATH."
                    )
                    task_status.started(None)
                    return

                client_env = os.environ.copy()
                if client_config.gcp_secrets and security_manager:
                    resolved_env_vars = await security_manager.resolve_gcp_secrets(
                        client_config.gcp_secrets
                    )
                    client_env.update(resolved_env_vars)
                server_path_obj = Path(client_config.server_path).resolve()
                server_params = StdioServerParameters(
                    command="python",
                    args=[str(server_path_obj)],
                    env=client_env,
                    cwd=str(server_path_obj.parent),
                )
                transport_context = stdio_client(
                    server_params, errlog=open(os.devnull, "w")
                )

            elif client_config.transport_type == "http_stream":
                if not client_config.http_endpoint:
                    raise ValueError(
                        "http_endpoint is required for http_stream transport"
                    )
                endpoint_url = client_config.http_endpoint
                placeholders = re.findall(r"\{([^}]+)\}", endpoint_url)
                for placeholder in placeholders:
                    env_value = os.getenv(placeholder)
                    if env_value:
                        endpoint_url = endpoint_url.replace(
                            f"{{{placeholder}}}", env_value
                        )
                    else:
                        raise ValueError(
                            f"Could not resolve placeholder '{{{placeholder}}}' in http_endpoint for client '{client_id}'."
                        )
                if os.environ.get("DOCKER_ENV", "false").lower() == "true":
                    endpoint_url = endpoint_url.replace(
                        "localhost", "host.docker.internal"
                    )

                # Pre-flight check to see if the server is reachable
                try:
                    async with httpx.AsyncClient() as client:
                        await client.head(endpoint_url, timeout=5.0)
                    logger.debug(
                        f"Pre-flight check for {client_id} at {endpoint_url} successful."
                    )
                except httpx.ConnectError as e:
                    logger.error(f"Pre-flight check failed for client {client_id}: {e}")
                    task_status.started(None)
                    return

                transport_context = streamablehttp_client(endpoint_url)

            elif client_config.transport_type == "local":
                if not client_config.command or not client_config.args:
                    raise ValueError(
                        "command and args are required for local transport"
                    )

                # Pre-flight check for the command
                if not shutil.which(client_config.command):
                    logger.error(
                        f"Pre-flight check failed for client {client_id}: command '{client_config.command}' not found in PATH."
                    )
                    task_status.started(None)
                    return

                client_env = os.environ.copy()
                if client_config.gcp_secrets and security_manager:
                    resolved_env_vars = await security_manager.resolve_gcp_secrets(
                        client_config.gcp_secrets
                    )
                    client_env.update(resolved_env_vars)
                updated_args = []
                for arg in client_config.args:
                    env_vars = re.findall(r"\{([^}]+)\}", arg)
                    for var in env_vars:
                        if var in client_env:
                            arg = arg.replace(f"{{{var}}}", client_env[var])
                    updated_args.append(arg)
                server_params = StdioServerParameters(
                    command=client_config.command, args=updated_args, env=client_env
                )
                transport_context = stdio_client(
                    server_params, errlog=open(os.devnull, "w")
                )
            else:
                raise ValueError(
                    f"Unsupported transport_type: {client_config.transport_type}"
                )

            if transport_context is None:
                raise RuntimeError("Transport context was not created.")

            # --- 2. Session Management and Monitoring ---
            with client_cancel_scope:
                async with transport_context as transport_streams, ClientSession(
                    transport_streams[0], transport_streams[1]
                ) as session:
                    logger.debug(f"Transport and session established for {client_id}.")
                    self.active_clients[client_id] = session

                    # Signal success to the parent task
                    task_status.started(session)

                    logger.debug(
                        f"Task for client {client_id}: Monitoring until cancelled."
                    )
                    await anyio.sleep_forever()

        except (Exception, ExceptionGroup) as e:
            logger.error(
                f"Failed to establish or maintain connection for client {client_id}: {e}",
                exc_info=True,
            )
            # Signal failure to the parent task
            try:
                task_status.started(None)
            except RuntimeError:
                # This can happen if the task was already started and then an error occurred,
                # or if a cancellation raced with the error. It's safe to ignore.
                pass
            return  # Exit the task gracefully
        finally:
            logger.debug(f"Client lifecycle task for {client_id} is ending.")
            self.active_clients.pop(client_id, None)

    def get_session(self, client_id: str) -> Optional[ClientSession]:
        """
        Retrieves the active session for a given client ID.
        """
        return self.active_clients.get(client_id)

    def get_all_sessions(self) -> Dict[str, ClientSession]:
        """
        Returns a dictionary of all active client sessions.
        """
        return self.active_clients.copy()
