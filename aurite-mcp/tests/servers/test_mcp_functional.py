"""
Functional tests for MCP servers.
This module provides a standardized way to test MCP servers for
basic functionality and accessibility of prompts, tools, and resources.
"""

import asyncio
import importlib.util
import inspect
import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
from contextlib import AsyncExitStack

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent directory to path if needed for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.host.host import MCPHost, HostConfig, ClientConfig, RootConfig


class MCPServerTester:
    """Tester class for MCP servers."""
    
    def __init__(self, server_path: str):
        """Initialize the tester with the path to the MCP server.
        
        Args:
            server_path: Path to the MCP server python file
        """
        self.server_path = Path(server_path).resolve()
        self.server_name = self.server_path.stem
        self.host = None
        self.client_id = "test-client"
        self.tools = []
        self.prompts = []
        self.resources = []
        
    def prepare_host_config(self) -> HostConfig:
        """Prepare host configuration for initialization.
        
        This method allows tests to customize the configuration before host initialization.
        
        Returns:
            HostConfig object ready for host initialization
        """
        config = HostConfig(
            clients=[
                ClientConfig(
                    client_id=self.client_id,
                    server_path=self.server_path,
                    roots=[
                        # Add generic roots for testing - specific servers may need more
                        RootConfig(name="test", uri="test:///", capabilities=["read", "write"]),
                    ],
                    capabilities=["tools", "prompts", "resources", "roots"],
                    timeout=30.0,
                )
            ]
        )
        return config
    
    async def initialize_host(self, config: Optional[HostConfig] = None) -> None:
        """Initialize the MCP host with the server.
        
        Args:
            config: Optional host configuration. If not provided, a default one will be created.
        """
        if config is None:
            config = self.prepare_host_config()
        
        # Create and initialize host
        self.host = MCPHost(config)
        await self.host.initialize()
    
    async def discover_components(self) -> Dict[str, List]:
        """Discover tools, prompts and resources in the server."""
        if not self.host:
            await self.initialize_host()
            
        # Discover tools
        self.tools = self.host.tools.list_tools()
        logger.info(f"Found {len(self.tools)} tools: {[t['name'] for t in self.tools]}")
        
        # Discover prompts
        try:
            self.prompts = await self.host.prompts.list_prompts(self.client_id)
            logger.info(f"Found {len(self.prompts)} prompts: {[p.name for p in self.prompts]}")
        except Exception as e:
            logger.warning(f"Error listing prompts: {e}")
            self.prompts = []
        
        # Discover resources
        try:
            self.resources = await self.host.resources.list_resources(self.client_id)
            logger.info(f"Found resources: {self.resources}")
        except Exception as e:
            logger.warning(f"Error listing resources: {e}")
            self.resources = []
            
        return {
            "tools": self.tools,
            "prompts": self.prompts,
            "resources": self.resources
        }
        
    async def test_tools(self) -> Dict[str, bool]:
        """Test all tools and return results."""
        results = {}
        
        # For each tool, check its schema (but don't execute)
        for tool in self.tools:
            tool_name = tool["name"]
            try:
                # Just check that we can get the tool's schema
                schema = tool.get("inputSchema", {})
                logger.info(f"Tool '{tool_name}' schema: {schema}")
                results[tool_name] = True
            except Exception as e:
                logger.error(f"Error checking tool '{tool_name}': {e}")
                results[tool_name] = False
                
        return results
    
    async def test_prompts(self) -> Dict[str, bool]:
        """Test all prompts and return results."""
        results = {}
        
        # For each prompt, check we can get its details
        for prompt in self.prompts:
            prompt_name = prompt.name
            try:
                # Get the prompt details
                prompt_details = await self.host.prompts.get_prompt(prompt_name, self.client_id)
                logger.info(f"Prompt '{prompt_name}' description: {prompt_details.description}")
                results[prompt_name] = True
            except Exception as e:
                logger.error(f"Error checking prompt '{prompt_name}': {e}")
                results[prompt_name] = False
                
        return results
                    
    async def test_server_components(self) -> Dict[str, Dict[str, bool]]:
        """Test all server components and return results."""
        await self.discover_components()
        
        results = {
            "tools": await self.test_tools(),
            "prompts": await self.test_prompts(),
            "resources": {"found": len(self.resources) > 0}
        }
        
        return results
        
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.host:
            await self.host.shutdown()
            
            
async def run_mcp_server_test(server_path: str) -> Dict[str, Dict[str, bool]]:
    """Test an MCP server for basic functionality.
    
    This is a helper function, not a pytest test function.
    
    Args:
        server_path: Path to the MCP server python file
        
    Returns:
        Dictionary of test results
    """
    logger.info(f"Testing MCP server at: {server_path}")
    
    tester = MCPServerTester(server_path)
    try:
        results = await tester.test_server_components()
        
        # Validate results
        all_passed = True
        
        # Check tool results
        if results["tools"]:
            tool_success = all(results["tools"].values())
            logger.info(f"Tools test {'passed' if tool_success else 'failed'}")
            all_passed = all_passed and tool_success
            
        # Check prompt results  
        if results["prompts"]:
            prompt_success = all(results["prompts"].values())
            logger.info(f"Prompts test {'passed' if prompt_success else 'failed'}")
            all_passed = all_passed and prompt_success
                
        # Report on resources
        logger.info(f"Resources {'found' if results['resources']['found'] else 'not found'}")
        
        logger.info(f"Overall test {'passed' if all_passed else 'failed'}")
        return results
        
    finally:
        await tester.cleanup()


@pytest.mark.asyncio
async def test_mcp_server_functional(server_path: str) -> None:
    """Pytest wrapper for testing an MCP server.
    
    Args:
        server_path: Path to the MCP server python file
    """
    results = await run_mcp_server_test(server_path)
    
    # Make assertions for pytest
    
    # Assert that we have at least one tool or prompt
    has_components = bool(results["tools"]) or bool(results["prompts"]) or results["resources"]["found"]
    assert has_components, f"Server at {server_path} has no accessible components"
    
    # If we have tools, assert they all work
    if results["tools"]:
        for tool_name, success in results["tools"].items():
            assert success, f"Tool '{tool_name}' is not accessible"
            
    # If we have prompts, assert they all work    
    if results["prompts"]:
        for prompt_name, success in results["prompts"].items():
            assert success, f"Prompt '{prompt_name}' is not accessible"
    

if __name__ == "__main__":
    # Example usage when run directly
    if len(sys.argv) > 1:
        server_path = sys.argv[1]
        asyncio.run(run_mcp_server_test(server_path))
    else:
        print("Usage: python test_mcp_functional.py <path_to_server>")