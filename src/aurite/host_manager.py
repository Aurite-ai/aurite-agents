"""
Host Manager for orchestrating MCPHost, Agents, and Workflows.
"""

import asyncio
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


class _AuriteCore:
    """
    The internal core of the Aurite framework, designed to be used as an
    async context manager to ensure proper resource management.
    """

    def __init__(self):
        self.config_manager = ConfigManager()
        self.project_root = self.config_manager.project_root
        self.host = MCPHost()
        self.storage_manager: Optional["StorageManager"] = None
        self._db_engine = None
        self._is_shut_down = False

        if os.getenv("AURITE_ENABLE_DB", "false").lower() == "true":
            self._db_engine = create_db_engine()
            if self._db_engine:
                self.storage_manager = StorageManager(engine=self._db_engine)

        self.execution = ExecutionFacade(
            config_manager=self.config_manager,
            host_instance=self.host,
            storage_manager=self.storage_manager,
        )
        logger.debug(f"Aurite Core initialized for project root: {self.project_root}")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    async def initialize(self):
        logger.debug("Initializing Aurite Core services...")
        try:
            if self.storage_manager:
                self.storage_manager.init_db()
            if self.host:
                await self.host.__aenter__()
            logger.info(
                colored(
                    "Aurite Core initialization complete.", "yellow", attrs=["bold"]
                )
            )
        except Exception as e:
            logger.error(f"Error during Aurite Core initialization: {e}", exc_info=True)
            await self.shutdown()
            raise RuntimeError(f"Aurite Core initialization failed: {e}") from e

    async def shutdown(self):
        if self._is_shut_down:
            return
        logger.debug("Shutting down Aurite Core...")
        if self.host:
            await self.host.__aexit__(None, None, None)
            self.host = None
        if self._db_engine:
            self._db_engine.dispose()
            self._db_engine = None
        self.storage_manager = None
        self._is_shut_down = True
        logger.info("Aurite Core shutdown complete.")

    def get_config_manager(self) -> ConfigManager:
        return self.config_manager

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AgentRunResult:
        return await self.execution.run_agent(
            agent_name=agent_name,
            user_message=user_message,
            system_prompt=system_prompt,
            session_id=session_id,
        )

    async def run_simple_workflow(
        self, workflow_name: str, initial_input: Any
    ) -> SimpleWorkflowExecutionResult:
        return await self.execution.run_simple_workflow(
            workflow_name=workflow_name, initial_input=initial_input
        )

    async def run_custom_workflow(
        self, workflow_name: str, initial_input: Any, session_id: Optional[str] = None
    ) -> Any:
        return await self.execution.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
            session_id=session_id,
        )


class Aurite:
    """
    A user-friendly wrapper for the Aurite framework that manages the
    underlying async lifecycle, ensuring graceful shutdown even when not
    used as a context manager.
    """

    def __init__(self):
        self._core = _AuriteCore()
        self._loop = asyncio.get_event_loop()

    def __del__(self):
        if not self._core._is_shut_down:
            if self._loop.is_running():
                self._loop.create_task(self._core.shutdown())
            else:
                asyncio.run(self._core.shutdown())

    def get_config_manager(self) -> ConfigManager:
        return self._core.get_config_manager()

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AgentRunResult:
        async with self._core as core:
            return await core.run_agent(
                agent_name=agent_name,
                user_message=user_message,
                system_prompt=system_prompt,
                session_id=session_id,
            )

    async def run_simple_workflow(
        self, workflow_name: str, initial_input: Any
    ) -> SimpleWorkflowExecutionResult:
        async with self._core as core:
            return await core.run_simple_workflow(
                workflow_name=workflow_name, initial_input=initial_input
            )

    async def run_custom_workflow(
        self, workflow_name: str, initial_input: Any, session_id: Optional[str] = None
    ) -> Any:
        async with self._core as core:
            return await core.run_custom_workflow(
                workflow_name=workflow_name,
                initial_input=initial_input,
                session_id=session_id,
            )

    # Allow the wrapper to be used as a context manager as well
    async def __aenter__(self):
        return await self._core.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._core.__aexit__(exc_type, exc_val, exc_tb)
