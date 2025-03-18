"""
Planning module for creating and managing task plans.

This module provides:
1. A planning MCP server for creating structured plans
2. Tools for saving and retrieving plans
3. A workflow for plan creation and management
"""

# Import the mcp object instead of PlanningServer
from .planning_server import mcp

__all__ = ["mcp"]
