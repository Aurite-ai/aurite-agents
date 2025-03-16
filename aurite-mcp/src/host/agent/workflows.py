"""
Workflow management for MCP Host.

This module provides a WorkflowManager class that handles:
1. Workflow registration and lifecycle management
2. Workflow execution and result handling
3. Integration with the host system

This is part of Layer 4 (Agent Layer) in the Host architecture.
"""

from typing import Dict, Any, Optional, Type, List
import logging
import asyncio
import time

from ...agents.base_workflow import BaseWorkflow
from ...agents.base_models import AgentContext, AgentData
from ..resources.tools import ToolManager
from ..resources.prompts import PromptManager
from ..resources.resources import ResourceManager

logger = logging.getLogger(__name__)


class WorkflowManager:
    """
    Manages workflow registration, execution, and lifecycle.
    Part of the agent layer of the Host system.
    
    This manager allows the host to register, execute, and manage workflows
    without requiring direct dependencies between workflows and the host system.
    """
    
    def __init__(
        self, 
        tool_manager: ToolManager, 
        prompt_manager: Optional[PromptManager] = None,
        resource_manager: Optional[ResourceManager] = None
    ):
        """
        Initialize the workflow manager.
        
        Args:
            tool_manager: The tool manager for workflow access to tools
            prompt_manager: Optional prompt manager for workflow access to prompts
            resource_manager: Optional resource manager for workflow access to resources
        """
        self._tool_manager = tool_manager
        self._prompt_manager = prompt_manager
        self._resource_manager = resource_manager
        
        # Workflow registry
        self._workflows: Dict[str, BaseWorkflow] = {}
        self._workflow_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Active executions
        self._active_executions: Dict[str, asyncio.Task] = {}
        
    async def initialize(self):
        """Initialize the workflow manager"""
        logger.info("Initializing workflow manager")
        # No initialization needed beyond the constructor at this point
    
    async def register_workflow(
        self, 
        workflow_class: Type[BaseWorkflow], 
        name: Optional[str] = None, 
        **kwargs
    ) -> str:
        """
        Register a workflow with the manager.
        
        Args:
            workflow_class: The workflow class to register
            name: Optional name for the workflow (defaults to class's name attribute)
            **kwargs: Additional arguments to pass to the workflow constructor
            
        Returns:
            The registered workflow name
        """
        # Create workflow instance with tool manager instead of host
        workflow = workflow_class(tool_manager=self._tool_manager, **kwargs)
        
        # Use provided name or the workflow's own name
        workflow_name = name or workflow.name
        
        # Store in registry
        self._workflows[workflow_name] = workflow
        
        # Store metadata
        self._workflow_metadata[workflow_name] = {
            "class": workflow_class.__name__,
            "registration_time": time.time(),
            "description": getattr(workflow, "description", ""),
            "custom_args": kwargs
        }
        
        # Initialize the workflow
        await workflow.initialize()
        
        logger.info(f"Registered workflow: {workflow_name}")
        return workflow_name
    
    async def execute_workflow(
        self, 
        workflow_name: str, 
        input_data: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentContext:
        """
        Execute a registered workflow.
        
        Args:
            workflow_name: The name of the workflow to execute
            input_data: Input data for the workflow
            metadata: Optional metadata for the execution
            
        Returns:
            The final workflow context with results
        """
        # Validate workflow exists
        if workflow_name not in self._workflows:
            raise ValueError(f"Workflow not found: {workflow_name}")
        
        workflow = self._workflows[workflow_name]
        
        # Execute the workflow
        start_time = time.time()
        logger.info(f"Executing workflow: {workflow_name}")
        
        try:
            # Create execution ID for tracking
            execution_id = f"{workflow_name}_{int(start_time)}"
            
            # Execute the workflow
            result_context = await workflow.execute(input_data, metadata)
            
            # Record execution metrics
            execution_time = time.time() - start_time
            logger.info(f"Workflow {workflow_name} completed in {execution_time:.2f} seconds")
            
            return result_context
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Workflow {workflow_name} failed after {execution_time:.2f} seconds: {e}")
            raise
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all registered workflows with metadata.
        
        Returns:
            List of workflows with metadata
        """
        return [
            {
                "name": name,
                "description": self._workflow_metadata[name].get("description", ""),
                "class": self._workflow_metadata[name].get("class", ""),
                "registration_time": self._workflow_metadata[name].get("registration_time", 0),
            }
            for name in self._workflows
        ]
    
    def get_workflow(self, workflow_name: str) -> Optional[BaseWorkflow]:
        """
        Get a workflow by name.
        
        Args:
            workflow_name: The name of the workflow
            
        Returns:
            The workflow if found, None otherwise
        """
        return self._workflows.get(workflow_name)
    
    def has_workflow(self, workflow_name: str) -> bool:
        """
        Check if a workflow exists.
        
        Args:
            workflow_name: The name of the workflow
            
        Returns:
            True if the workflow exists, False otherwise
        """
        return workflow_name in self._workflows
    
    async def shutdown(self):
        """Shutdown the workflow manager"""
        logger.info("Shutting down workflow manager")
        
        # Cancel any active executions
        for task in self._active_executions.values():
            task.cancel()
        
        # Shutdown all workflows
        for name, workflow in self._workflows.items():
            logger.info(f"Shutting down workflow: {name}")
            try:
                await workflow.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down workflow {name}: {e}")
        
        # Clear registries
        self._workflows.clear()
        self._workflow_metadata.clear()