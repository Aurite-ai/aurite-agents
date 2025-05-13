"""
Initialization for the MCP Host package.
Exposes key classes for easier import.
"""

from .host import MCPHost

# Optionally expose other key components if needed directly under src.host
# from src.config.config_models import HostConfig, ClientConfig, AgentConfig, WorkflowConfig
# from .foundation import SecurityManager, RootManager, MessageRouter
# from .resources import ToolManager, PromptManager, ResourceManager

__all__ = ["MCPHost"]  # Explicitly define what 'from src.host import *' imports
