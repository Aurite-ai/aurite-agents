"""
Host Manager for orchestrating MCPHost, Agents, and Workflows.
"""

import logging
import os
import sys
from typing import Any, List, Optional

if sys.version_info < (3, 11):
    try:
        from exceptiongroup import ExceptionGroup as BaseExceptionGroup
    except ImportError:

        class BaseExceptionGroup(Exception):  # type: ignore
            exceptions: List[Exception] = []
else:
    pass

from .config.config_manager import ConfigManager
from .execution.facade import ExecutionFacade
from .host.host import MCPHost
from .storage.db_connection import create_db_engine
from .storage.db_manager import StorageManager
from .components.agents.agent_models import AgentRunResult
from .components.workflows.workflow_models import SimpleWorkflowExecutionResult
from termcolor import colored

logger = logging.getLogger(__name__)

try:
    from .bin.logging_config import setup_logging

    log_level_str = os.getenv("AURITE_LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level_str, logging.INFO)
    setup_logging(level=numeric_level)
except ImportError:
    logger.warning(
        "aurite.bin.logging_config not found. Colored logging will not be applied."
    )
    if not logging.getLogger().hasHandlers():
        log_level_str = os.getenv("AURITE_LOG_LEVEL", "INFO").upper()
        numeric_level = getattr(logging, log_level_str, logging.INFO)
        logging.basicConfig(level=numeric_level)


class DuplicateClientIdError(ValueError):
    """Custom exception for duplicate client ID registration attempts."""

    pass


class Aurite:
    """
    Manages the lifecycle of the Aurite framework services and provides
    a simplified entrypoint for executing agents and workflows.
    """

    def __init__(self):
        self.config_manager = ConfigManager()
        self.project_root = self.config_manager.project_root
        self.host = MCPHost()
        self.storage_manager: Optional["StorageManager"] = None
        self._db_engine = None

        if os.getenv("AURITE_ENABLE_DB", "false").lower() == "true":
            self._db_engine = create_db_engine()
            if self._db_engine:
                self.storage_manager = StorageManager(engine=self._db_engine)

        self.execution = ExecutionFacade(
            config_manager=self.config_manager,
            host_instance=self.host,
            storage_manager=self.storage_manager,
        )
        logger.debug(f"Aurite initialized for project root: {self.project_root}")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    async def initialize(self):
        logger.debug("Initializing Aurite services...")
        try:
            if self.storage_manager:
                self.storage_manager.init_db()

            if self.host:
                await self.host.__aenter__()

            logger.info(
                colored("Aurite initialization complete.", "yellow", attrs=["bold"])
            )
        except Exception as e:
            logger.error(f"Error during Aurite initialization: {e}", exc_info=True)
            await self.shutdown()
            raise RuntimeError(f"Aurite initialization failed: {e}") from e

    async def shutdown(self):
        logger.debug("Shutting down Aurite...")
        if self.host and self.host._exit_stack:
            await self.host.__aexit__(None, None, None)
            self.host = None
        if self._db_engine:
            self._db_engine.dispose()
            self._db_engine = None
        self.storage_manager = None
        logger.info("Aurite shutdown complete.")

    def get_config_manager(self) -> ConfigManager:
        """Returns the ConfigManager instance."""
        return self.config_manager

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AgentRunResult:
        if not self.execution:
            raise RuntimeError("Aurite execution facade is not initialized.")
        return await self.execution.run_agent(
            agent_name=agent_name,
            user_message=user_message,
            system_prompt=system_prompt,
            session_id=session_id,
        )

    async def run_workflow(
        self, workflow_name: str, initial_input: Any
    ) -> SimpleWorkflowExecutionResult:
        if not self.execution:
            raise RuntimeError("Aurite execution facade is not initialized.")
        return await self.execution.run_simple_workflow(
            workflow_name=workflow_name, initial_input=initial_input
        )

    async def run_custom_workflow(
        self, workflow_name: str, initial_input: Any, session_id: Optional[str] = None
    ) -> Any:
        if not self.execution:
            raise RuntimeError("Aurite execution facade is not initialized.")
        return await self.execution.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
            session_id=session_id,
        )
