import asyncio
import logging
from termcolor import colored  # For colored print statements

from aurite import Aurite
from aurite.config.config_models import AgentConfig, LLMConfig, ClientConfig

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

        # --- Dynamic Registration Example ---
        # The following section demonstrates how to dynamically register components
        # with Aurite. This is useful for adding or modifying configurations at
        # runtime without changing the project's JSON/YAML files.

        # Construct an absolute path to the server script to ensure it's always found,
        # making the example robust regardless of the current working directory.
        project_root = aurite.project_manager.current_project_root
        if not project_root:
            raise RuntimeError(
                "Could not determine the project root from the Aurite instance. "
                "Ensure aurite_config.json is present."
            )
        server_path = project_root / "mcp_servers" / "weather_mcp_server.py"

        # 1. Define and register an LLM configuration
        llm_config = LLMConfig(
            llm_id="openai_gpt4_turbo",
            provider="openai",
            model_name="gpt-4-turbo-preview",
        )

        await aurite.register_llm_config(llm_config)

        # 2. Define and register an MCP server configuration
        mcp_server_config = ClientConfig(
            name="my_weather_server",
            server_path=server_path,  # Use the resolved absolute path
            capabilities=["tools"],
        )
        await aurite.register_client(mcp_server_config)

        # 3. Define and register an Agent configuration
        agent_config = AgentConfig(
            name="My Weather Agent",
            system_prompt="Your job is to use the tools at your disposal to learn the weather information needed to answer the user's query.",
            mcp_servers=["my_weather_server"],
            llm_config_id="openai_gpt4_turbo",
        )
        await aurite.register_agent(agent_config)
        # --- End of Dynamic Registration Example ---

        # Define the user's query for the agent.
        user_query = "What is the weather in London?"

        # Run the agent with the user's query. The check for the execution
        # facade is now handled internally by the `aurite.run_agent` method.
        agent_result = await aurite.run_agent(
            agent_name="My Weather Agent", user_message=user_query
        )

        # Print the agent's response in a colored format for better visibility.
        print(colored("\n--- Agent Result ---", "yellow", attrs=["bold"]))
        response_text = agent_result.primary_text

        print(colored(f"Agent's response: {response_text}", "cyan", attrs=["bold"]))

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())
