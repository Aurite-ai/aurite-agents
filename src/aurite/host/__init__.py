"""
Initialization for the MCP Host package.
Exposes key classes for easier import.
"""

from .host import MCPHost

# Optionally expose other key components if needed directly under aurite.host
# from aurite.config.config_models import HostConfig, ClientConfig, AgentConfig, WorkflowConfig
# from .foundation import SecurityManager, RootManager, MessageRouter
# from .resources import ToolManager, PromptManager, ResourceManager

__all__ = ["MCPHost"]  # Explicitly define what 'from aurite.host import *' imports
