import asyncio
import logging
from aurite import Aurite

# Configure basic logging. For more detailed logs, set level to logging.INFO or logging.DEBUG.
logging.basicConfig(level=logging.INFO)
# It's good practice to get a logger instance per module.
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
        # Asynchronously initialize the Aurite application.
        # This sets up the MCPHost, loads project components (agents, clients, etc.),
        # and prepares the execution facade.
        await aurite.initialize()
\

        # Ensure Aurite is fully initialized before proceeding.
        if not await aurite.is_initialized():
            print(
                "Error: Aurite application is not properly initialized. Please check logs."
            )
            return

        # Define the user's query for the agent.
        user_query = "What is the weather in London?"

        print(f"\nRunning agent 'Weather Agent' with query: '{user_query}'...")

        # Run the agent using the execution facade.
        # `agent_name` refers to an agent defined in your project's configuration.
        # The result is an `AgentExecutionResult` Pydantic model instance.
        agent_result = await aurite.execution.run_agent(
            agent_name="Weather Agent",
            user_message=user_query
        )

        # The `agent_result` is an AgentExecutionResult Pydantic model instance.
        # Its `primary_text` property conveniently handles displaying:
        # 1. The main text content if the agent responded successfully.
        # 2. A formatted error message if an error occurred during the agent's execution.
        # 3. A message indicating if no text was found in an otherwise successful response.
        print("\n--- Agent Result ---")
        print(f"Agent's response: {agent_result.primary_text}")

    except Exception as e:
        # Catch any unexpected errors during the process, including if agent_result was not assigned.
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure Aurite and its components (like MCPHost and clients) are shut down gracefully.
        if aurite.host: # Check if host was initialized before trying to shut down
            logger.info("Shutting down Aurite...")
            await aurite.shutdown()
            logger.info("Aurite shutdown complete.")


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())
