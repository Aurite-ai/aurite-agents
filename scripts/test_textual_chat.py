#!/usr/bin/env python3
"""
Test script for the new textual chat interface.
"""

import asyncio
from pathlib import Path

from aurite.bin.tui.chat import TextualChatApp
from aurite.host_manager import Aurite


async def main():
    """Test the textual chat app with a weather agent."""
    # Initialize Aurite
    aurite = Aurite(start_dir=Path.cwd())

    try:
        # Create the chat app (it will create its own Aurite instance with logging disabled)
        chat_app = TextualChatApp(
            agent_name="Weather Agent",
            session_id="test-session-123",
            system_prompt=None,
            start_dir=Path.cwd(),
        )

        # Run the chat app
        await chat_app.run_async()

    except KeyboardInterrupt:
        print("Chat interrupted by user")
    except Exception as e:
        print(f"Error running chat: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Ensure clean shutdown
        await aurite.kernel.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
