import asyncio

from termcolor import colored  # For colored print statements

from aurite import Aurite
from aurite.lib.models.config.components import AgentConfig, LLMConfig


async def main():
    """
    A simple example demonstrating how to initialize Aurite, run an agent,
    and print its response.
    """
    # Load environment variables from a .env file if it exists
    from dotenv import load_dotenv

    load_dotenv()

    try:
        # Initialize the main Aurite application object.
        # This will load aurite configurations from your json files (in the config/ folder if you ran aurite init)
        # You can execute your components with the Aurite class, or register new configurations with in-line python (example below)!
        aurite = Aurite()

        # --- Dynamic Registration Example ---
        # The following section demonstrates how to dynamically register components
        # with Aurite. This is useful for adding or modifying configurations at
        # runtime without changing the project's JSON/YAML files.

        # 1. Define and register an LLM configuration
        llm_config = LLMConfig(
            name="openai_gpt4_turbo",
            provider="openai",
            model="gpt-4-turbo-preview",
            api_key_env_var="OPENAI_API_KEY",  # Optional, this will default to the expected environment variable name for each provider, like OPENAI_API_KEY for OpenAI.
        )

        await aurite.register_llm(llm_config)

        # # 2. Define and register an MCP server configuration
        # mcp_server_config = ClientConfig(
        #     name="my_weather_server",
        #     server_path="example_mcp_servers/weather_mcp_server.py",  # Use the resolved absolute path
        #     capabilities=["tools"],
        # )
        # await aurite.register_client(mcp_server_config)

        # 3. Define and register an Agent configuration
        agent_config = AgentConfig(
            name="My Weather Agent",
            system_prompt="You are a helpful weather assistant. Your job is to use the tools at your disposal to get the weather for the provided location.",
            mcp_servers=["weather_server"],
            llm_config_id="openai_gpt4_turbo",
        )
        await aurite.register_agent(agent_config)
        # --- End of Dynamic Registration Example ---

        # Define the user's query for the agent.
        user_query = "What's the weather like in New York?"

        # Run the agent with the user's query. The check for the execution
        # engine is now handled internally by the `aurite.run_agent` method.
        agent_result = await aurite.run_agent(agent_name="My Weather Agent", user_message=user_query)

        # Print the agent's response in a colored format for better visibility.
        print(colored("\n--- Agent Result ---", "yellow", attrs=["bold"]))
        response_text = agent_result.primary_text

        print(colored(f"Agent's response: {response_text}", "cyan", attrs=["bold"]))

        await aurite.kernel.shutdown()

    except Exception as e:
        print(f"An error occurred during agent execution: {e}")


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())
