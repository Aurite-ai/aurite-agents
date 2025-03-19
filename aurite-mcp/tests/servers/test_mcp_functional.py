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

from src.host.host import MCPHost
from src.host.config import ClientConfig, RootConfig, HostConfigModel
from tests.servers.test_config import get_agent_config_by_id


class MCPServerTester:
    """Tester class for MCP servers."""
    
    def __init__(self, server_path: str, host: Optional[MCPHost] = None):
        """Initialize the tester with the path to the MCP server.
        
        Args:
            server_path: Path to the MCP server python file
            host: Optional pre-initialized host (from test_mcp_host fixture)
        """
        self.server_path = Path(server_path).resolve()
        self.server_name = self.server_path.stem
        self.host = host
        self.tools = []
        self.prompts = []
        self.resources = []
        self.using_existing_host = host is not None
        
        # Derive client_id from server_path if possible
        # For example, extract "planning" from "planning_server.py"
        self.client_id = self.server_name.replace("_server", "")
        
        # For non-standard names, default to test-client
        if self.client_id == self.server_name:
            self.client_id = "test-client"
        
    def prepare_host_config(self) -> HostConfigModel:
        """Prepare host configuration for initialization.
        
        This method loads the configuration from the JSON files if available.
        Otherwise, it falls back to a default configuration.
        
        Returns:
            HostConfigModel object ready for host initialization
        """
        # Try to get the agent config from JSON files
        agent_config = get_agent_config_by_id(self.client_id)
        
        if agent_config:
            # Convert the JSON config to ClientConfig
            logger.info(f"Using configuration from JSON for client: {self.client_id}")
            
            # But ensure we're using our test server path
            agent_config["server_path"] = str(self.server_path)
            
            # Convert roots from dict to RootConfig objects
            roots = []
            for root_dict in agent_config.get("roots", []):
                roots.append(
                    RootConfig(
                        name=root_dict.get("name", "default"),
                        uri=root_dict.get("uri", "test:///"),
                        capabilities=root_dict.get("capabilities", ["read", "write"])
                    )
                )
                
            # Create ClientConfig
            client_config = ClientConfig(
                client_id=self.client_id,
                server_path=self.server_path, 
                roots=roots,
                capabilities=agent_config.get("capabilities", ["tools", "prompts", "resources", "roots"]),
                timeout=agent_config.get("timeout", 30.0)
            )
        else:
            # Fallback to default configuration
            logger.info(f"No JSON configuration found for {self.client_id}, using defaults")
            client_config = ClientConfig(
                client_id=self.client_id,
                server_path=self.server_path,
                roots=[
                    # Add generic roots for testing
                    RootConfig(name="test", uri="test:///", capabilities=["read", "write"]),
                ],
                capabilities=["tools", "prompts", "resources", "roots"],
                timeout=30.0,
            )
            
        # Create the host config model with the client configuration
        config = HostConfigModel(clients=[client_config])
        return config
    
    async def initialize_host(self, config: Optional[HostConfigModel] = None) -> None:
        """Initialize the MCP host with the server.
        
        Args:
            config: Optional host configuration. If not provided, a default one will be created.
        """
        # If we're using the shared host from the fixture, we don't need to initialize
        if self.using_existing_host:
            logger.info(f"Using existing host with {len(self.host.tools.list_tools())} tools")
            return
            
        if config is None:
            config = self.prepare_host_config()
        
        # Create and initialize host
        self.host = MCPHost(config=config)
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
        
    async def test_tools(self) -> Dict[str, Any]:
        """Test all tools and return results.
        
        For each tool, this method checks its schema structure and validates
        that required parameters are defined.
        
        Returns:
            Dictionary mapping tool names to test results including success status and schema info
        """
        results = {}
        
        # For each tool, check its schema (but don't execute)
        for tool in self.tools:
            tool_name = tool["name"]
            try:
                # Get the tool's schema and validate it
                schema = tool.get("inputSchema", {})
                
                # Extract schema properties if available
                properties = schema.get("properties", {})
                required_params = schema.get("required", [])
                
                # Log schema details
                if properties:
                    prop_list = [f"{p} ({'required' if p in required_params else 'optional'})" 
                                 for p in properties.keys()]
                    logger.info(f"Tool '{tool_name}' parameters: {', '.join(prop_list)}")
                else:
                    logger.info(f"Tool '{tool_name}' has no defined parameters in schema")
                
                # Store detailed results
                results[tool_name] = {
                    "success": True,
                    "properties": properties,
                    "required": required_params,
                    "schema": schema
                }
            except Exception as e:
                logger.error(f"Error checking tool '{tool_name}': {e}")
                results[tool_name] = {
                    "success": False,
                    "error": str(e)
                }
                
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
        # Only shut down if we're not using a shared host (which will be cleaned up by the fixture)
        if self.host and not self.using_existing_host:
            try:
                await self.host.shutdown()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                # Don't re-raise, we're in cleanup
            
            
async def run_mcp_server_test(server_path: str, shared_host: Optional[MCPHost] = None) -> Dict[str, Dict[str, bool]]:
    """Test an MCP server for basic functionality.
    
    This is a helper function, not a pytest test function.
    
    Args:
        server_path: Path to the MCP server python file
        shared_host: Optional shared host from test_mcp_host fixture
        
    Returns:
        Dictionary of test results
    """
    logger.info(f"Testing MCP server at: {server_path}")
    
    tester = MCPServerTester(server_path, host=shared_host)
    try:
        results = await tester.test_server_components()
        
        # Validate results
        all_passed = True
        
        # Check tool results
        if results["tools"]:
            tool_success = all(result.get("success", False) 
                              for result in results["tools"].values())
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
@pytest.mark.parametrize("server_path", 
    [
        # Hardcode paths for now to avoid dependency on external test functions
        "/home/wilcoxr/workspace/aurite-agents/aurite-mcp/src/agents/planning/planning_server.py",
        "/home/wilcoxr/workspace/aurite-agents/aurite-mcp/src/agents/evaluation/evaluation_server.py"
    ]
)
async def test_mcp_server_functional(server_path: str, test_mcp_host) -> None:
    """Pytest wrapper for testing an MCP server.
    
    Args:
        server_path: Path to the MCP server python file
        test_mcp_host: Host fixture with JSON-configured host
    """
    results = await run_mcp_server_test(server_path, shared_host=test_mcp_host)
    
    # Make assertions for pytest
    
    # Assert that we have at least one tool or prompt
    has_components = bool(results["tools"]) or bool(results["prompts"]) or results["resources"]["found"]
    assert has_components, f"Server at {server_path} has no accessible components"
    
    # If we have tools, assert they all work
    if results["tools"]:
        for tool_name, tool_result in results["tools"].items():
            assert tool_result.get("success", False), f"Tool '{tool_name}' is not accessible"
            
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