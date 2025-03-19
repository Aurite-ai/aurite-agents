"""
Workflow management for MCP Host.

This module provides:
1. Workflow registration and execution
2. Workflow configuration management
3. Integration with the host system

This is part of Layer 3 (Workflow Layer) in the Host architecture.
"""

from typing import Dict, List, Optional, Any, Type
import logging
from pathlib import Path

from ..config import ConfigurableManager, WorkflowConfig, ConfigurationManager
from .base import BaseWorkflow

logger = logging.getLogger(__name__)


class WorkflowManager(ConfigurableManager[WorkflowConfig]):
    """
    Manages workflow registration and execution.
    Part of the workflow layer of the Host system.
    """

    def __init__(self, host):
        """
        Initialize the workflow manager.

        Args:
            host: The host instance for access to all services
        """
        super().__init__("workflows")
        self._host = host
        self._workflows: Dict[str, BaseWorkflow] = {}

    def _config_model_class(self):
        return WorkflowConfig

    def _validate_config_structure(self, config: Dict[str, Any]) -> bool:
        return ConfigurationManager.validate_config_structure(
            config, ["workflows"], "workflows"
        )

    async def register_workflow(
        self,
        workflow_class: Type[BaseWorkflow],
        name: str,
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Register a workflow with optional configuration.

        Args:
            workflow_class: The workflow class to register
            name: Name for the workflow
            config: Optional workflow configuration
            metadata: Optional metadata for the workflow

        Returns:
            True if registration was successful
        """
        try:
            # Create workflow instance
            workflow = workflow_class(self._host, name, config)
            self._workflows[name] = workflow

            # Update configuration
            if not self._config:
                self._config = WorkflowConfig(workflows=[], metadata={})

            # Add or update workflow config
            workflow_data = {
                "name": name,
                "class": f"{workflow_class.__module__}.{workflow_class.__name__}",
                "config": config or {},
            }

            # Update workflows list
            updated = False
            for i, w in enumerate(self._config.workflows):
                if w.get("name") == name:
                    self._config.workflows[i] = workflow_data
                    updated = True
                    break

            if not updated:
                self._config.workflows.append(workflow_data)

            # Update metadata if provided
            if metadata:
                self._config.metadata[name] = metadata

            # Save configuration
            return await self.save_config(self._config)

        except Exception as e:
            logger.error(f"Failed to register workflow {name}: {e}")
            return False

    def get_workflow(self, name: str) -> Optional[BaseWorkflow]:
        """
        Get a workflow by name.

        Args:
            name: Name of the workflow

        Returns:
            The workflow if found, None otherwise
        """
        return self._workflows.get(name)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all registered workflows with metadata.

        Returns:
            List of workflows with their configurations and metadata
        """
        if not self._config:
            return []

        workflows = []
        for workflow in self._config.workflows:
            workflow_info = {
                "name": workflow["name"],
                "class": workflow["class"],
                "config": workflow.get("config", {}),
                "metadata": self._config.metadata.get(workflow["name"], {}),
            }
            workflows.append(workflow_info)
        return workflows

    async def execute_workflow(
        self,
        name: str,
        input_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute a workflow with input data.

        Args:
            name: Name of the workflow to execute
            input_data: Optional input data for the workflow
            **kwargs: Additional keyword arguments for execution

        Returns:
            Workflow execution results
        """
        workflow = self.get_workflow(name)
        if not workflow:
            raise ValueError(f"Workflow not found: {name}")

        try:
            return await workflow.execute(input_data or {}, **kwargs)
        except Exception as e:
            logger.error(f"Error executing workflow {name}: {e}")
            raise

    async def shutdown(self):
        """Shutdown the workflow manager"""
        logger.info("Shutting down workflow manager")

        # Clear workflows
        self._workflows.clear()

        # Clear configuration
        if self._config:
            self._config.workflows.clear()
            self._config.metadata.clear()
