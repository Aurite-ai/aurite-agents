"""
Host Manager for orchestrating MCPHost, Agents, and Workflows.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

if sys.version_info < (3, 11):
    try:
        from exceptiongroup import ExceptionGroup as BaseExceptionGroup
    except ImportError:

        class BaseExceptionGroup(Exception):  # type: ignore
            exceptions: List[Exception] = []
else:
    pass

from .config.config_models import (
    AgentConfig,
    ClientConfig,
    CustomWorkflowConfig,
    LLMConfig,
    WorkflowConfig,
)
from .config.component_manager import ComponentManager
from .config.project_manager import ProjectManager
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
    Manages the lifecycle of MCPHost and orchestrates the execution of
    agents, simple workflows, and custom workflows based on loaded configurations.
    """

    def __init__(self, config_path: Optional[Path] = None):
        determined_path_source = ""
        final_config_path: Optional[Path] = None

        if config_path:
            final_config_path = Path(config_path)
            determined_path_source = "direct argument"
        else:
            env_config_path_str = os.getenv("PROJECT_CONFIG_PATH", "aurite_config.json")
            final_config_path = Path(env_config_path_str)
            determined_path_source = (
                f"PROJECT_CONFIG_PATH environment variable ('{env_config_path_str}')"
            )

        if not final_config_path.is_absolute():
            final_config_path = final_config_path.resolve()

        self.config_path: Path = final_config_path
        self.host: Optional["MCPHost"] = None
        self.storage_manager: Optional["StorageManager"] = None
        self.execution: Optional[ExecutionFacade] = None
        self._db_engine = None
        self.component_manager = ComponentManager()
        self.project_manager = ProjectManager(self.component_manager)
        self._dynamic_registration_enabled = (
            os.getenv("AURITE_ALLOW_DYNAMIC_REGISTRATION", "true").lower() == "true"
        )

        if os.getenv("AURITE_ENABLE_DB", "false").lower() == "true":
            self._db_engine = create_db_engine()
            if self._db_engine:
                self.storage_manager = StorageManager(engine=self._db_engine)

        logger.debug(
            f"Aurite initialized with config path: {self.config_path} from {determined_path_source}"
        )

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    async def initialize(self):
        logger.debug(f"Initializing Aurite with project config: {self.config_path}...")
        try:
            self.project_manager.load_project(self.config_path)
            active_project = self.project_manager.get_active_project_config()
            if not active_project:
                raise RuntimeError(f"Failed to load project '{self.config_path}'.")

            if self.storage_manager:
                self.storage_manager.init_db()

            host_config = self.project_manager.get_host_config_for_active_project()
            if not host_config:
                raise RuntimeError("Failed to get HostConfig from ProjectManager.")

            self.host = MCPHost(config=host_config)
            await self.host.__aenter__()

            if self.storage_manager:
                # Convert lists to dictionaries before syncing with the database
                agents_dict = {a.name: a for a in active_project.agents if a.name}
                workflows_dict = {w.name: w for w in active_project.simple_workflows}
                custom_workflows_dict = {
                    cw.name: cw for cw in active_project.custom_workflows
                }
                llm_configs_dict = {llm.name: llm for llm in active_project.llms}
                self.storage_manager.sync_all_configs(
                    agents=agents_dict,
                    workflows=workflows_dict,
                    custom_workflows=custom_workflows_dict,
                    llm_configs=llm_configs_dict,
                )

            self.execution = ExecutionFacade(
                host_instance=self.host,
                current_project=active_project,
                storage_manager=self.storage_manager,
            )
            logger.info(
                colored("Aurite initialization complete.", "yellow", attrs=["bold"])
            )
        except Exception as e:
            logger.error(f"Error during Aurite initialization: {e}", exc_info=True)
            if self.host:
                await self.shutdown()
            raise RuntimeError(f"Aurite initialization failed: {e}") from e

    async def shutdown(self):
        logger.debug("Shutting down Aurite...")
        if self.host:
            await self.host.__aexit__(None, None, None)
            self.host = None
        if self._db_engine:
            self._db_engine.dispose()
            self._db_engine = None
        self.storage_manager = None
        logger.info("Aurite shutdown complete.")

    async def change_project(self, new_project_config_path: Path):
        logger.info(f"Attempting to change project to: {new_project_config_path}...")
        await self.shutdown()
        self.project_manager.unload_active_project()
        self.config_path = new_project_config_path.resolve()
        await self.initialize()
        logger.info(
            f"Successfully changed project and initialized with {self.config_path}."
        )

    async def register_client(self, client_config: ClientConfig):
        if not self._dynamic_registration_enabled:
            raise PermissionError("Dynamic registration is disabled.")
        if not self.host:
            raise ValueError("Aurite is not initialized.")

        await self.host.register_client(client_config)
        self.project_manager.add_component_to_active_project(
            "mcp_servers", client_config.name, client_config
        )

    async def register_agent(self, agent_config: AgentConfig):
        if not self._dynamic_registration_enabled:
            raise PermissionError("Dynamic registration is disabled.")
        if not self.host:
            raise ValueError("Aurite is not initialized.")
        if not agent_config.name:
            raise ValueError("Agent configuration must have a name.")

        # Simplified for now, will need to re-add JIT registration logic
        self.project_manager.add_component_to_active_project(
            "agents", agent_config.name, agent_config
        )
        if self.storage_manager:
            self.storage_manager.sync_agent_config(agent_config)

    async def register_llm_config(self, llm_config: LLMConfig):
        if not self._dynamic_registration_enabled:
            raise PermissionError("Dynamic registration is disabled.")
        if not self.host:
            raise ValueError("Aurite is not initialized.")

        self.project_manager.add_component_to_active_project(
            "llms", llm_config.name, llm_config
        )
        if self.storage_manager:
            self.storage_manager.sync_llm_config(llm_config)

    async def register_workflow(self, workflow_config: WorkflowConfig):
        if not self._dynamic_registration_enabled:
            raise PermissionError("Dynamic registration is disabled.")
        if not self.host:
            raise ValueError("Aurite is not initialized.")

        self.project_manager.add_component_to_active_project(
            "simple_workflows", workflow_config.name, workflow_config
        )
        if self.storage_manager:
            self.storage_manager.sync_workflow_config(workflow_config)

    async def register_custom_workflow(
        self, custom_workflow_config: CustomWorkflowConfig
    ):
        if not self._dynamic_registration_enabled:
            raise PermissionError("Dynamic registration is disabled.")
        if not self.host:
            raise ValueError("Aurite is not initialized.")

        self.project_manager.add_component_to_active_project(
            "custom_workflows", custom_workflow_config.name, custom_workflow_config
        )
        if self.storage_manager:
            self.storage_manager.sync_custom_workflow_config(custom_workflow_config)

    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        active_project = self.project_manager.get_active_project_config()
        if not active_project:
            return None
        for agent in active_project.agents:
            if agent.name == agent_name:
                return agent
        return None

    def get_llm_config(self, llm_config_id: str) -> Optional[LLMConfig]:
        active_project = self.project_manager.get_active_project_config()
        if not active_project:
            return None
        for llm_config in active_project.llms:
            if llm_config.name == llm_config_id:
                return llm_config
        return None

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
