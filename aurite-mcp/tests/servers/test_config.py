"""
Configuration loader for MCP server tests.
This module provides utility functions to load and parse configuration files.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# Base project directory
PROJECT_DIR = Path(__file__).parent.parent.parent


def load_json_config(config_path: str) -> Dict[str, Any]:
    """
    Load a JSON configuration file.
    
    Args:
        config_path: Path to the JSON configuration file, relative to the project root
        
    Returns:
        Parsed JSON configuration as a dictionary
    """
    full_path = PROJECT_DIR / config_path
    
    if not full_path.exists():
        raise FileNotFoundError(f"Config file not found: {full_path}")
        
    with open(full_path, 'r') as f:
        return json.load(f)


def load_host_config() -> Dict[str, Any]:
    """
    Load the host configuration.
    
    Returns:
        Host configuration as a dictionary
    """
    return load_json_config("config/host/aurite_host.json")


def load_agent_configs() -> List[Dict[str, Any]]:
    """
    Load agent configurations.
    
    Returns:
        List of agent configurations
    """
    host_config = load_host_config()
    agents_path = host_config.get("agents")
    
    if not agents_path:
        raise ValueError("No agents path defined in host config")
        
    agent_config = load_json_config(agents_path)
    return agent_config.get("agents", [])


def load_workflow_configs() -> List[Dict[str, Any]]:
    """
    Load workflow configurations.
    
    Returns:
        List of workflow configurations
    """
    host_config = load_host_config()
    workflows_path = host_config.get("workflows")
    
    if not workflows_path:
        raise ValueError("No workflows path defined in host config")
        
    workflow_config = load_json_config(workflows_path)
    return workflow_config.get("workflows", [])


def get_agent_config_by_id(client_id: str) -> Optional[Dict[str, Any]]:
    """
    Get agent configuration by client ID.
    
    Args:
        client_id: The client ID to look for
        
    Returns:
        Agent configuration or None if not found
    """
    agents = load_agent_configs()
    
    for agent in agents:
        if agent.get("client_id") == client_id:
            return agent
            
    return None


def get_all_server_paths() -> List[str]:
    """
    Get all MCP server paths from the configuration.
    
    Returns:
        List of absolute paths to MCP servers
    """
    agents = load_agent_configs()
    server_paths = []
    
    for agent in agents:
        if "server_path" in agent:
            # Convert relative path to absolute
            rel_path = agent["server_path"]
            abs_path = str(PROJECT_DIR / rel_path)
            server_paths.append(abs_path)
            
    return server_paths