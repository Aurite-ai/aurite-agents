import asyncio
import os

from aurite import AgentConfig, Aurite, LLMConfig

# Disable force refresh to prevent in-memory registrations from being lost
os.environ["AURITE_CONFIG_FORCE_REFRESH"] = "false"


async def main():
    print("--- Starting Debug Script ---")

    # 1. Initialize Aurite
    aurite = Aurite(disable_logging=True)
    print("Aurite instance created.")

    # 2. Define and register LLM
    llm_config = LLMConfig(name="debug_llm", provider="openai", model="gpt-4-turbo-preview")
    await aurite.register_llm(llm_config)
    print(f"LLM '{llm_config.name}' registered.")

    # 3. Define and register Agent
    agent_config = AgentConfig(name="Debug Agent", llm_config_id="debug_llm")
    await aurite.register_agent(agent_config)
    print(f"Agent '{agent_config.name}' registered.")

    # 4. Verify registration in ConfigManager
    print("\n--- Verifying Registration ---")
    config_manager = aurite.get_config_manager()

    registered_agent_config = config_manager.get_config("agent", "Debug Agent")
    if registered_agent_config:
        print("✅ Agent 'Debug Agent' FOUND in ConfigManager.")
        # print("   Config:", registered_agent_config)
    else:
        print("❌ Agent 'Debug Agent' NOT FOUND in ConfigManager.")

    registered_llm_config = config_manager.get_config("llm", "debug_llm")
    if registered_llm_config:
        print("✅ LLM 'debug_llm' FOUND in ConfigManager.")
    else:
        print("❌ LLM 'debug_llm' NOT FOUND in ConfigManager.")

    # 5. Attempt to run the agent
    print("\n--- Attempting to Run Agent ---")
    try:
        user_message = "This is a test."
        result = await aurite.run_agent(agent_name="Debug Agent", user_message=user_message)
        print("✅ Agent run successful!")
        print("Response:", result.primary_text)
    except Exception as e:
        print(f"❌ Agent run FAILED: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await aurite.kernel.shutdown()

    print("\n--- Debug Script Finished ---")


if __name__ == "__main__":
    asyncio.run(main())
