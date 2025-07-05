import asyncio
from pathlib import Path

from aurite.host_manager import Aurite


async def main():
    """
    A simple test script to debug the interactive agent stream.
    """
    print("Initializing Aurite...")
    async with Aurite(start_dir=Path.cwd()) as aurite:
        agent_name = "Weather Agent"
        session_id = "debug_session"

        print(f"Starting interactive session with agent: {agent_name}")
        print("---")

        user_message = "Weather in London?"

        stream = aurite.stream_agent(
            agent_name=agent_name,
            user_message=user_message,
            session_id=session_id,
        )

        print(f"--> Streaming response for: '{user_message}'")
        async for event in stream:
            print(event)
        print("---> Stream finished.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")
