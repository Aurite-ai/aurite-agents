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

        # 1. Define and register an LLM configuration
        llm_config = LLMConfig(
            llm_id="openai_gpt4_turbo",
            provider="openai",
            model_name="gpt-4-turbo-preview",
            api_key_env_var="OPENAI_API_KEY",
        )

        await aurite.register_llm_config(llm_config)
        logger.info(f"Dynamically registered LLM: {llm_config.llm_id}")

        # 2. Define and register an MCP server configuration
        mcp_server_config = ClientConfig(
            name="my_weather_server",
            server_path="mcp_servers/weather_mcp_server.py",
            capabilities=["tools"],
        )
        await aurite.register_client(mcp_server_config)
        logger.info(f"Dynamically registered MCP Server: {mcp_server_config.name}")

        # 3. Define and register an Agent configuration
        agent_config = AgentConfig(
            name="My Weather Agent",
            system_prompt="Your job is to use the tools at your disposal to learn the weather information needed to answer the user's query.",
            mcp_servers=["my_weather_server"],
            llm_config_id="openai_gpt4_turbo",
        )
        await aurite.register_agent(agent_config)
        logger.info(f"Dynamically registered Agent: {agent_config.name}")
        # --- End of Dynamic Registration Example ---

        # Define the user's query for the agent.
        user_query = "What is the weather in London?"

        # Run the agent with the user's query.
        agent_result = await aurite.execution.run_agent(
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
