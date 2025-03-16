"""
Test script for host integration with prompts and tools
"""

import asyncio
import os
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

async def start_mcp_server():
    """Start the MCP server as a subprocess"""
    current_dir = Path(__file__).parent
    server_path = current_dir / "test_mcp_server.py"
    
    # Start the server in a subprocess
    process = subprocess.Popen(
        [sys.executable, str(server_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give it a moment to start up
    time.sleep(2)
    
    return process

async def test_prompt_with_tools():
    """Manual test of the prompt with tools functionality"""
    # Get the absolute path to the server script
    current_dir = Path(__file__).parent.resolve()
    server_path = current_dir / "test_mcp_server.py"
    
    logger.info(f"Testing with server at: {server_path}")
    
    # Import the host here to avoid circular imports
    from src.host.host import MCPHost, HostConfig, ClientConfig
    
    # Configure the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="test-client",
                server_path=server_path,
                roots=[],
                capabilities=["tools", "prompts"],
                timeout=30.0
            )
        ]
    )
    
    # Create and initialize the host
    host = MCPHost(config)
    await host.initialize()
    
    try:
        # List available prompts
        client_id = "test-client"
        prompts = await host.prompts.list_prompts(client_id)
        logger.info(f"Available prompts: {[p.name for p in prompts]}")
        
        # List available tools
        tools = host.tools.list_tools()
        logger.info(f"Available tools: {[t['name'] for t in tools]}")
        
        # Get the system prompt
        prompt_result = await host._clients[client_id].get_prompt(
            "assistant", 
            {"user_name": "Tester", "temperature_units": "imperial"}
        )
        
        # Handle different response formats
        if hasattr(prompt_result, 'text'):
            system_prompt = prompt_result.text
        elif hasattr(prompt_result, 'result') and hasattr(prompt_result.result, 'text'):
            system_prompt = prompt_result.result.text
        else:
            # Try to extract text from the object's structure
            system_prompt = str(prompt_result)
            
        logger.info(f"System prompt: {system_prompt}")
        
        # Test prompt preparation
        prompt_data = await host.prepare_prompt_with_tools(
            prompt_name="assistant",
            prompt_arguments={"user_name": "Tester", "temperature_units": "imperial"},
            client_id=client_id,
            tool_names=["weather_lookup", "current_time"]
        )
        
        logger.info("Prompt preparation successful!")
        logger.info(f"System prompt: {prompt_data['system']}")
        logger.info(f"Number of tools: {len(prompt_data['tools'])}")
        for i, tool in enumerate(prompt_data['tools']):
            logger.info(f"Tool {i+1}: {tool['name']} - {tool['description']}")
        
        # Skip direct tool execution due to roots validation requirement
        logger.info("Skipping direct tool execution as it requires roots validation")
        logger.info("The prompt preparation step was successful!")
        
        # Do not test execute_prompt_with_tools as it requires a real API key
        logger.info("Not testing execute_prompt_with_tools as it requires an API key")
        logger.info("To test with a real API key, set the ANTHROPIC_API_KEY environment variable")
        
        return True
    
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Shutdown the host
        await host.shutdown()

if __name__ == "__main__":
    import sys
    asyncio.run(test_prompt_with_tools())