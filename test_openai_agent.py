import asyncio
import logging
import os

# Configure basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s') # Changed to DEBUG
logger = logging.getLogger(__name__)

# Ensure the src directory is in the Python path if running from the root directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from aurite.host_manager import Aurite

async def main():
    """
    Initializes Aurite, runs the OpenAI Weather Agent, and prints the result.
    """
    logger.info("Starting OpenAI agent test script...")

    # IMPORTANT: Ensure the OPENAI_API_KEY environment variable is set before running this script.
    # For example: export OPENAI_API_KEY="your_key_here"
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("CRITICAL: OPENAI_API_KEY environment variable is not set.")
        print("Please set the OPENAI_API_KEY environment variable before running this script.")
        return

    aurite_app = Aurite() # Uses aurite_config.json from CWD by default

    try:
        logger.info("Initializing Aurite...")
        await aurite_app.initialize()
        logger.info("Aurite initialized successfully.")

        if aurite_app.execution is None:
            logger.error("Aurite execution facade was not initialized. Cannot run agent.")
            return

        agent_name = "OpenAI Weather Agent"
        user_message = "What is the weather like in London?"

        logger.info(f"Running agent: '{agent_name}' with message: '{user_message}'")

        result = await aurite_app.execution.run_agent(
            agent_name=agent_name,
            user_message=user_message
        )

        logger.info("Agent run completed.")
        print("\nAgent Result:")
        import json
        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(f"An error occurred during the agent test: {e}", exc_info=True)
        print(f"\nAn error occurred: {e}")
    finally:
        logger.info("Shutting down Aurite...")
        await aurite_app.shutdown()
        logger.info("Aurite shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
