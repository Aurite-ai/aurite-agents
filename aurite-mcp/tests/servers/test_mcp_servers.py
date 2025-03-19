"""
Test suite for MCP servers.
This module automatically discovers and tests all MCP servers in the codebase.
"""

import asyncio
import os
import glob
import logging
from pathlib import Path
import pytest

from tests.servers.test_mcp_functional import run_mcp_server_test

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define paths to search for MCP servers
SERVER_PATHS = [
    "src/agents/planning/planning_server.py",
    "src/agents/evaluation/evaluation_server.py", 
    "src/storage/sql/sql_server.py",
]

def get_mcp_servers():
    """Find all MCP server files in the codebase."""
    base_dir = Path(__file__).parent.parent.parent  # root of project
    server_files = []
    
    # First check our known server paths
    for rel_path in SERVER_PATHS:
        server_path = base_dir / rel_path
        if server_path.exists():
            server_files.append(str(server_path))
            logger.info(f"Found known server: {server_path}")
    
    # Then look for any additional server files we might have missed
    # This glob pattern looks for any Python file with "server" in the name
    # but we exclude files that start with "test_" to avoid test files
    for pattern in ["**/[!test_]*server.py"]:
        path_pattern = os.path.join(base_dir, "src", pattern)
        additional_servers = glob.glob(path_pattern)
        
        # Only add servers that weren't already found
        for server in additional_servers:
            if server not in server_files:
                server_files.append(server)
                logger.info(f"Found additional server: {server}")
    
    return server_files

@pytest.mark.parametrize("server_path", get_mcp_servers())
@pytest.mark.asyncio
async def test_all_mcp_servers(server_path):
    """Run functional tests on each MCP server."""
    logger.info(f"Testing MCP server: {server_path}")
    # Direct call to the test function, not the pytest wrapper
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
    # When run directly, this will list all the servers that would be tested
    servers = get_mcp_servers()
    print(f"Found {len(servers)} MCP servers to test:")
    for server in servers:
        print(f"  - {server}")
    
    print("\nRun with pytest to execute tests:")