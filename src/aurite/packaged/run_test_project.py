import asyncio
import logging
from aurite import Aurite

# Configure logging for visibility
logging.basicConfig(level=logging.INFO)
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

        print("\n--- Agent Result ---")
        if agent_result and "final_response" in agent_result:
            final_response = agent_result.get("final_response", {})
            content_list = final_response.get("content", [{}])
            if (
                content_list
                and isinstance(content_list, list)
                and len(content_list) > 0
            ):
                message_text = content_list[0].get(
                    "text", "No text in agent's final response."
                )
                print(f"Agent's response: {message_text}")
            else:
                print(
                    "Agent's final response content is empty or not in the expected format."
                )
        else:
            print("No final_response found in agent_result or agent_result is None.")
            print("Full agent_result for debugging:", agent_result)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        print(f"An error occurred: {e}")
    finally:
        if aurite.host:
            await aurite.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
