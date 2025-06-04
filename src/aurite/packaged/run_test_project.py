import asyncio
import logging
from aurite import Aurite

# Configure logging for visibility
logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)


async def main():
    aurite = Aurite()

    try:
        await aurite.initialize() # Initialize the Aurite application
        logger.info("Aurite initialized successfully.")

        user_query = "What is the weather in London?"  # The question for our agent
        session_id = (
            "cli_tutorial_session_001"  # Optional: for tracking conversation history
        )

        print(f"Running agent 'Weather Agent' with query: '{user_query}'")

        if not aurite.execution:
            print(
                "Error: Execution facade not initialized. This is unexpected after aurite_app.initialize()."
            )
            return

        agent_result = await aurite.execution.run_agent(
            agent_name="Weather Agent",  # The name of the agent to run
            user_message=user_query, # The user query to send to the agent
            session_id=session_id, # Optional: session ID for tracking
        )

        print(f"Agent's response: {agent_result.primary_text}")

        print("\n--- Agent Result ---")
        if agent_result: # agent_result is now an AgentExecutionResult instance
            if agent_result.has_error:
                print(f"Agent execution error: {agent_result.error}")
            elif agent_result.primary_text:
                print(f"Agent's response: {agent_result.primary_text}")
            else:
                # This handles cases where final_response is None, content is empty, or no text block exists
                print("Agent's final response did not contain primary text.")
        else:
            # This case implies the error_factory in facade returned an AgentExecutionResult with an error,
            # or an even earlier error occurred where facade might return None (though less likely with current error_factory).
            # If agent_result can be None from facade due to very early errors:
            print("Agent execution failed to produce a result object.")
            # For debugging, you might log what `agent_result` is if it's not an expected model instance or None.
            # print("Full agent_result for debugging:", agent_result) # Keep if useful for debugging None cases

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        print(f"An error occurred: {e}")
    finally:
        if aurite.host:
            await aurite.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
