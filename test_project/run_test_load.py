import asyncio
import os
from pathlib import Path

# Attempt to import from the installed package
try:
    from aurite_agents import HostManager, AgentConfig, LLMConfig
except ImportError:
    print("Failed to import from 'aurite_agents'. Ensure the package is installed correctly in your virtual environment.")
    exit(1)

async def main():
    # Set the PROJECT_CONFIG_PATH environment variable to point to our test project's config
    # This assumes run_test_load.py is in the root of 'test_project'
    project_config_file = Path("aurite_config.json").resolve()
    os.environ["PROJECT_CONFIG_PATH"] = str(project_config_file)

    # For the test, we also need a dummy API_KEY and ANTHROPIC_API_KEY if default LLM config expects it
    # The default_llms.json might use anthropic.
    os.environ["API_KEY"] = "test_api_key_for_load_test"
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy-key-for-load-test" # Needed if default_claude_opus is used

    print(f"Attempting to initialize HostManager with project: {project_config_file}")

    host_manager = HostManager(config_path=project_config_file)
    initialized_correctly = False
    try:
        await host_manager.initialize()
        print("HostManager initialized successfully.")
        initialized_correctly = True

        # Try to get the agent config
        agent_name_to_test = "MyTestAgent"
        retrieved_agent_config = host_manager.project_manager.get_active_project_config().agents.get(agent_name_to_test) # type: ignore

        if retrieved_agent_config and isinstance(retrieved_agent_config, AgentConfig):
            print(f"Successfully retrieved AgentConfig for '{agent_name_to_test}':")
            print(f"  Name: {retrieved_agent_config.name}")
            print(f"  System Prompt: {retrieved_agent_config.system_prompt}")
            print(f"  LLM ID: {retrieved_agent_config.llm_id}")

            # Check if the LLM config was also loaded (assuming default_claude_opus)
            llm_id_to_test = "default_claude_opus"
            retrieved_llm_config = host_manager.project_manager.get_active_project_config().llms.get(llm_id_to_test) # type: ignore
            if retrieved_llm_config and isinstance(retrieved_llm_config, LLMConfig):
                print(f"Successfully retrieved LLMConfig for '{llm_id_to_test}'.")
            else:
                print(f"Warning: LLMConfig '{llm_id_to_test}' not found or invalid type.")

            print("\n--- TEST SUCCEEDED ---")

        else:
            print(f"Error: AgentConfig for '{agent_name_to_test}' not found or invalid type after initialization.")
            active_project_agents = host_manager.project_manager.get_active_project_config().agents if host_manager.project_manager.get_active_project_config() else {} # type: ignore
            print(f"Available agents in active project: {list(active_project_agents.keys())}")
            print("\n--- TEST FAILED ---")

    except Exception as e:
        print(f"An error occurred during HostManager initialization or test: {e}")
        import traceback
        traceback.print_exc()
        print("\n--- TEST FAILED ---")
    finally:
        if initialized_correctly and host_manager:
            print("Shutting down HostManager...")
            await host_manager.shutdown()
            print("HostManager shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
