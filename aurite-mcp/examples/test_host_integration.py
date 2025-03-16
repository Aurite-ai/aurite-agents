"""
Test script for host integration with prompts and tools
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_tools_and_prompts():
    """Test the weather/time tools and prompts."""
    # Get the absolute path to the server script
    current_dir = Path(__file__).parent.resolve()
    server_path = current_dir / "test_mcp_server.py"

    logger.info(f"Testing with server at: {server_path}")

    # Configure and initialize the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="test-client",
                server_path=server_path,
                roots=[],
                capabilities=["tools", "prompts"],  # Added prompts capability
                timeout=30.0,
            )
        ]
    )

    host = MCPHost(config)
    await host.initialize()

    try:
        # Test tool execution
        logger.info("\n=== Testing Tools ===")

        logger.info("\nTesting weather lookup...")
        weather_result = await host.tools.execute_tool(
            "weather_lookup", {"location": "San Francisco", "units": "imperial"}
        )
        logger.info(f"Weather result: {weather_result[0].text}")

        logger.info("\nTesting current time...")
        time_result = await host.tools.execute_tool(
            "current_time", {"timezone": "America/New_York"}
        )
        logger.info(f"Time result: {time_result[0].text}")

        # Test prompt functionality
        logger.info("\n=== Testing Prompts ===")

        # Test getting available prompts
        prompts = await host.prompts.list_prompts("test-client")
        logger.info(f"\nAvailable prompts: {[p.name for p in prompts]}")

        # Test getting a specific prompt
        logger.info("\nTesting get_prompt...")
        prompt = await host.prompts.get_prompt("weather_assistant", "test-client")
        if prompt:
            logger.info(f"Found prompt: {prompt.name}")
            logger.info(f"Description: {prompt.description}")
            logger.info("Arguments:")
            for arg in prompt.arguments:
                logger.info(
                    f"  - {arg.name}: {arg.description} (required: {arg.required})"
                )

        # Test preparing a prompt with tools
        logger.info("\nTesting prepare_prompt_with_tools...")
        prompt_data = await host.prepare_prompt_with_tools(
            prompt_name="weather_assistant",
            prompt_arguments={"user_name": "Tester", "preferred_units": "imperial"},
            client_id="test-client",
            tool_names=["weather_lookup", "current_time"],
        )

        logger.info("Prompt preparation successful!")
        logger.info(f"System prompt: {prompt_data['system']}")
        logger.info(f"Number of tools: {len(prompt_data['tools'])}")
        for i, tool in enumerate(prompt_data["tools"]):
            logger.info(f"Tool {i+1}: {tool['name']} - {tool['description']}")
        
        # If ANTHROPIC_API_KEY is available, test execute_prompt_with_tools
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            logger.info("\n=== Testing execute_prompt_with_tools ===")
            try:
                logger.info("Executing prompt with tools...")
                response = await host.execute_prompt_with_tools(
                    prompt_name="weather_assistant",
                    prompt_arguments={"user_name": "Tester", "preferred_units": "imperial"},
                    client_id="test-client",
                    user_message="What's the current weather in San Francisco and what time is it in New York?",
                    tool_names=["weather_lookup", "current_time"],
                    model="claude-3-sonnet-20240229",  # Using a smaller model for testing
                    max_tokens=1000,
                    temperature=0.7,
                )
                
                # Log the results
                logger.info("\nExecution complete!")
                logger.info(f"Conversation history length: {len(response['conversation'])}")
                
                if 'tool_uses' in response and response['tool_uses']:
                    logger.info(f"Number of tool calls: {len(response['tool_uses'])}")
                    for i, tool_use in enumerate(response['tool_uses']):
                        logger.info(f"Tool call {i+1}: {tool_use.get('content', '')}")
                
                if 'final_response' in response and response['final_response']:
                    logger.info("\nFinal response content:")
                    for block in response['final_response'].content:
                        if hasattr(block, 'text'):
                            logger.info(f"- {block.text[:100]}...")  # Just show beginning
                
                logger.info("\nexecute_prompt_with_tools test successful!")
            except Exception as e:
                logger.error(f"Error testing execute_prompt_with_tools: {e}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning("\nNo ANTHROPIC_API_KEY found, skipping execute_prompt_with_tools test")

        return True

    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await host.shutdown()


async def test_execute_prompt_only():
    """Test only the execute_prompt_with_tools function"""
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable is required for this test")
        return False
    
    # Get the absolute path to the server script
    current_dir = Path(__file__).parent.resolve()
    server_path = current_dir / "test_mcp_server.py"
    
    # Configure and initialize the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="test-client",
                server_path=server_path,
                roots=[],
                capabilities=["tools", "prompts"],
                timeout=30.0,
            )
        ]
    )
    
    host = MCPHost(config)
    await host.initialize()
    
    try:
        logger.info("\n=== Testing execute_prompt_with_tools only ===")
        
        response = await host.execute_prompt_with_tools(
            prompt_name="weather_assistant",
            prompt_arguments={"user_name": "Tester", "preferred_units": "imperial"},
            client_id="test-client",
            user_message="What's the weather like in Tokyo? And what time is it in London right now?",
            tool_names=["weather_lookup", "current_time"],
            model="claude-3-sonnet-20240229",  # Using a smaller model for testing
            max_tokens=1000,
            temperature=0.7,
        )
        
        # Log the results
        logger.info("\nExecution complete!")
        
        # Pretty print conversation history
        logger.info("\nConversation history:")
        for i, msg in enumerate(response['conversation']):
            logger.info(f"Message {i+1} ({msg['role']}):")
            logger.info(f"  {str(msg['content'])[:200]}...")  # Truncate for readability
        
        # Print tool uses if any
        if 'tool_uses' in response and response['tool_uses']:
            logger.info(f"\nNumber of tool calls: {len(response['tool_uses'])}")
            for i, tool_use in enumerate(response['tool_uses']):
                logger.info(f"Tool call {i+1}:")
                logger.info(f"  {str(tool_use)[:200]}...")  # Truncate for readability
        
        logger.info("\nTest successful!")
        return True
        
    except Exception as e:
        logger.error(f"Error in execute_prompt_with_tools test: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await host.shutdown()


if __name__ == "__main__":
    try:
        # Check command line arguments
        if len(sys.argv) > 1 and sys.argv[1] == "--prompt-only":
            # Run only the execute_prompt_with_tools test
            asyncio.run(test_execute_prompt_only())
        else:
            # Run the full test suite
            asyncio.run(test_tools_and_prompts())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
