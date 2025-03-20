import asyncio
from asyncio.log import logger
import logging
from pathlib import Path
from dotenv import load_dotenv
from src.host.host import MCPHost, HostConfig, ClientConfig


load_dotenv()  # load environment variables from .env



RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'  # Reset to default color

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def execute_agent():
    """Call the March Madness Agent with the MM Server"""
    # Get the absolute path to the server script
    current_dir = Path(__file__).parent.resolve()
    server_path = current_dir / "march_madness_server.py"

    logger.info(f"Testing with server at: {server_path}")

    print(f"Testing with server at: {server_path}")

    # Configure and initialize the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="mm_client",
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
        prompt_name="march_madness_prompt",
        prompt_arguments={},
        client_id="mm_client",
        user_message="You are a bracket filler agent. Go through all rounds of the bracket by comparing matchups and fill it out. Return all results.",
        tool_names=["get_first_round", "compare_matchup", "store_round_results"],
        model="claude-3-7-sonnet-latest",  # Using a smaller model for testing
        max_tokens=2000,
        temperature=0.7,
        max_iterations=100,
    )

    logger.info(f"Response: {response}")
    
    # Extract the final response text from the AI model
    final_response_text = response['final_response'].content[0].text
    logger.info(f"{GREEN}Final output: {final_response_text}{RESET}")


    # Outpt the final response text to a file
    with open("march_madness_output.txt", "w") as f:
        f.write(final_response_text)

    await host.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(execute_agent())
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
