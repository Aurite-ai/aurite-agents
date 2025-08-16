import asyncio

from aurite import Aurite


async def main():
    """
    Runs the Weather Agent and prints the result.
    """
    print("Initializing Aurite...")
    aurite = Aurite()
    print("Running agent...")
    result = await aurite.run_agent(
        agent_name="Weather Agent",
        user_message="Weather in London?",
    )

    print("\n--- Unregistering Server ---")
    await aurite.unregister_server("weather_server")
    print("Server unregistered.")

    print("\n--- Agent Result ---")
    if result and result.primary_text:
        print(result.primary_text)
    else:
        print("Agent did not return a response.")
    print("--------------------")


if __name__ == "__main__":
    asyncio.run(main())
