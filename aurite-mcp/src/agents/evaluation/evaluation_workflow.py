import asyncio
from asyncio.log import logger
import logging
from pathlib import Path
from dotenv import load_dotenv
from src.host.host import MCPHost, HostConfig, ClientConfig

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def execute_agent():
    """Test the weather/time tools and prompts."""
    # Get the absolute path to the server script
    current_dir = Path(__file__).parent.resolve()
    server_path = current_dir / "evaluation_server.py"

    logger.info(f"Testing with server at: {server_path}")

    print(f"Testing with server at: {server_path}")

    # Configure and initialize the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="evaluation_client",
                server_path=server_path,
                roots=[],
                capabilities=["tools", "prompts"],  # Added prompts capability
                timeout=30.0,
            )
        ]
    )

    host = MCPHost(config)
    await host.initialize()

    tools = host.tools.list_tools()

    prompts = await host.prompts.list_prompts()

    logger.info(f"Tools: {tools}")
    logger.info(f"Prompts: {prompts}")

    response = await host.execute_prompt_with_tools(
        prompt_name="evaluation_prompt",
        prompt_arguments={},
        client_id="evaluation_client",
        user_message="Can you say hello world",
        tool_names=["evaluate_agent"],
        model="claude-3-sonnet-20240229",  # Using a smaller model for testing
        max_tokens=1000,
        temperature=0.7,
    )

    logger.info(f"Response: {response}")

    await host.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(execute_agent())
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
