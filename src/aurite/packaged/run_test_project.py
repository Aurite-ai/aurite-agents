import asyncio
import logging
from termcolor import colored  # For colored print statements

from aurite import Aurite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """
    A simple example demonstrating how to initialize Aurite, run an agent,
    and print its response.
    """
    # Initialize the main Aurite application object.
    # This will load configurations based on `aurite_config.json` or environment variables.
    aurite = Aurite()

    try:
        await aurite.initialize()

        # Define the user's query for the agent.
        user_query = "What is the weather in London?"

        # Run the agent with the user's query.
        agent_result = await aurite.execution.run_agent(
            agent_name="Weather Agent", user_message=user_query
        )

        # Print the agent's response in a colored format for better visibility.
        print(colored("\n--- Agent Result ---", "yellow", attrs=["bold"]))
        response_text = agent_result.primary_text

        print(colored(f"Agent's response: {response_text}", "cyan", attrs=["bold"]))

    except Exception:
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())
