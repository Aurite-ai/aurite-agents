"""
Host Manager for orchestrating MCPHost, Agents, and Workflows.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

if sys.version_info < (3, 11):
    try:
        from exceptiongroup import ExceptionGroup as BaseExceptionGroup
    except ImportError:

        class BaseExceptionGroup(Exception):  # type: ignore
            exceptions: List[Exception] = []
else:
    pass

from langfuse import Langfuse
from termcolor import colored

from .execution.aurite_engine import AuriteEngine
from .execution.mcp_host.mcp_host import MCPHost
from .lib.config.config_manager import ConfigManager
from .lib.models.api.responses import AgentRunResult, LinearWorkflowExecutionResult
from .lib.models.config.components import (
    AgentConfig,
    ClientConfig,
    CustomWorkflowConfig,
    LLMConfig,
    WorkflowConfig,
)
from .lib.storage.db.db_connection import create_db_engine
from .lib.storage.db.db_manager import StorageManager
from .lib.storage.sessions.cache_manager import CacheManager
from .utils.logging_config import setup_logging_if_needed

logger = logging.getLogger(__name__)


class AuriteKernel:
    """
    The internal kernel of the Aurite framework.

    This class is responsible for managing the lifecycle of all core
    components (Host, Storage, etc.). It is an internal implementation
    detail and should not be used directly. Its primary purpose is to hold
    the state and async-native components that the public-facing Aurite
    class will manage.
    """

    def __init__(self, start_dir: Optional[Path] = None, disable_logging: bool = False):
        if start_dir and isinstance(start_dir, str):
            start_dir = Path(start_dir).resolve()
        elif start_dir is None:
            start_dir = Path(os.getcwd()).resolve()

        # Setup logging based on the disable_logging flag
        setup_logging_if_needed(disable_logging)

        self.config_manager = ConfigManager(start_dir=start_dir)
        self.project_root = self.config_manager.project_root
        self.host = MCPHost()
        self.storage_manager: Optional["StorageManager"] = None
        if os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
            self.langfuse = Langfuse(
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                host=os.getenv("LANGFUSE_HOST"),
            )
        else:
            self.langfuse = None

        # Initialize CacheManager with project-specific cache directory
        if self.project_root:
            cache_dir = self.project_root / ".aurite_cache"
            self.cache_manager = CacheManager(cache_dir=cache_dir)
        else:
            # Fallback to current directory if no project root
            self.cache_manager = CacheManager(cache_dir=Path(".aurite_cache"))
        self._db_engine = None
        self._is_shut_down = False

        if os.getenv("AURITE_ENABLE_DB", "false").lower() == "true":
            self._db_engine = create_db_engine()
            if self._db_engine:
                self.storage_manager = StorageManager(engine=self._db_engine)

        self.execution = AuriteEngine(
            config_manager=self.config_manager,
            host_instance=self.host,
            storage_manager=self.storage_manager,
            cache_manager=self.cache_manager,
            langfuse=self.langfuse,
        )
        logger.debug(f"Aurite Kernel initialized for project root: {self.project_root}")

    async def initialize(self):
        logger.debug("Initializing Aurite Kernel services...")
        try:
            if self.storage_manager:
                self.storage_manager.init_db()
            if self.host:
                await self.host.__aenter__()
            logger.info(colored("Aurite Kernel initialization complete.", "yellow", attrs=["bold"]))
        except Exception as e:
            logger.error(f"Error during Aurite Kernel initialization: {e}", exc_info=True)
            await self.shutdown()
            raise RuntimeError(f"Aurite Kernel initialization failed: {e}") from e

    async def shutdown(self):
        if self._is_shut_down:
            return
        logger.debug("Shutting down Aurite Kernel...")

        # Clean up litellm's global module-level clients
        try:
            import litellm

            # Check if litellm has module_level_aclient (async client)
            if hasattr(litellm, "module_level_aclient") and litellm.module_level_aclient:
                logger.debug("Closing litellm module-level async client...")
                try:
                    await litellm.module_level_aclient.close()
                except Exception as e:
                    logger.debug(f"Error closing litellm async client: {e}")

            # Check if litellm has module_level_client (sync client)
            if hasattr(litellm, "module_level_client") and litellm.module_level_client:
                logger.debug("Closing litellm module-level sync client...")
                try:
                    litellm.module_level_client.close()
                except Exception as e:
                    logger.debug(f"Error closing litellm sync client: {e}")
        except Exception as e:
            logger.debug(f"Error during litellm cleanup: {e}")

        if self.host:
            await self.host.__aexit__(None, None, None)
            self.host = None

        if self._db_engine:
            self._db_engine.dispose()
            self._db_engine = None
        self.storage_manager = None
        self._is_shut_down = True
        logger.info("Aurite Kernel shutdown complete.")


class Aurite:
    """
    The main entrypoint for the Aurite framework.

    This class provides the primary API for running agents and workflows.
    It manages the underlying async lifecycle, ensuring graceful shutdown
    even when not used as an explicit context manager.

    This class uses a wrapper pattern around an internal `AuriteKernel`
    to solve a critical async challenge: the `mcp` library's use of `anyio`
    for subprocesses conflicts with the main `asyncio` event loop.
    """

    def __init__(self, start_dir: Optional[Path] = None, disable_logging: bool = False):
        # The kernel holds the actual state and core components.
        self.kernel = AuriteKernel(start_dir=start_dir, disable_logging=disable_logging)
        # We capture the event loop on initialization to ensure we can
        # schedule the shutdown correctly, even if the loop is manipulated later.
        self._loop = asyncio.get_event_loop()
        self._initialized = False

    async def _ensure_initialized(self):
        """
        Initializes the kernel on the first call (lazy initialization).
        This improves performance by only starting up the host and other
        services when they are actually needed.
        """
        if not self._initialized:
            await self.kernel.initialize()
            self._initialized = True

    def initialize(self):
        """
        Initializes the Aurite framework.
        """
        logger.warning("The initialize method is no longer needed and will be removed in a future update.")

    def get_config_manager(self) -> ConfigManager:
        # This method is now primarily for external use; internal access
        # should be through the kernel.
        return self.kernel.config_manager

    async def register_agent(self, config: AgentConfig):
        """Programmatically register an agent configuration."""
        await self._ensure_initialized()
        self.kernel.config_manager.register_component_in_memory("agent", config.model_dump())
        self.kernel.execution.set_config_manager(self.kernel.config_manager)

    async def register_llm(self, config: LLMConfig):
        """Programmatically register an LLM configuration."""
        await self._ensure_initialized()
        self.kernel.config_manager.register_component_in_memory("llm", config.model_dump())
        self.kernel.execution.set_config_manager(self.kernel.config_manager)

    async def register_mcp_server(self, config: ClientConfig):
        """Programmatically register an MCP server configuration."""
        await self._ensure_initialized()
        self.kernel.config_manager.register_component_in_memory("mcp_server", config.model_dump())
        self.kernel.execution.set_config_manager(self.kernel.config_manager)

    async def register_linear_workflow(self, config: WorkflowConfig):
        """Programmatically register a linear workflow configuration."""
        await self._ensure_initialized()
        self.kernel.config_manager.register_component_in_memory("linear_workflow", config.model_dump())
        self.kernel.execution.set_config_manager(self.kernel.config_manager)

    async def register_custom_workflow(self, config: CustomWorkflowConfig):
        """Programmatically register a custom workflow configuration."""
        await self._ensure_initialized()
        self.kernel.config_manager.register_component_in_memory("custom_workflow", config.model_dump())
        self.kernel.execution.set_config_manager(self.kernel.config_manager)

    async def unregister_server(self, server_name: str):
        """Dynamically unregisters a client and cleans up its resources."""
        await self._ensure_initialized()
        if self.kernel.host:
            await self.kernel.host.unregister_client(server_name)

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        unregister_servers: Optional[List[str]] = None,
    ) -> AgentRunResult:
        await self._ensure_initialized()
        result = await self.kernel.execution.run_agent(
            agent_name=agent_name,
            user_message=user_message,
            system_prompt=system_prompt,
            session_id=session_id,
        )
        if unregister_servers and self.kernel.host:
            for server_name in unregister_servers:
                await self.kernel.host.unregister_client(server_name)
        return result

    async def run_linear_workflow(self, workflow_name: str, initial_input: Any) -> LinearWorkflowExecutionResult:
        await self._ensure_initialized()
        return await self.kernel.execution.run_linear_workflow(workflow_name=workflow_name, initial_input=initial_input)

    async def run_custom_workflow(
        self, workflow_name: str, initial_input: Any, session_id: Optional[str] = None
    ) -> Any:
        await self._ensure_initialized()
        return await self.kernel.execution.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
            session_id=session_id,
        )

    async def stream_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs an agent and streams the response back event by event.
        """
        await self._ensure_initialized()
        async for event in self.kernel.execution.stream_agent_run(
            agent_name=agent_name,
            user_message=user_message,
            system_prompt=system_prompt,
            session_id=session_id,
        ):
            yield event

    # Allow the wrapper to be used as a context manager for users who
    # prefer explicit resource management over relying on the __del__ finalizer.
    async def __aenter__(self):
        await self._ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.kernel.shutdown()
