import asyncio
import logging
from aurite import Aurite

# Configure logging for visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    aurite = Aurite()

    try:
        logger.info("Initializing Aurite...")
        await aurite.initialize()

        logger.info("Aurite initialized successfully.")

        workflow_input = {"city": "London"}  # Example input for the workflow

        logger.info(
            f"Running workflow 'ExampleCustomWorkflow' with input: {workflow_input}"
        )
        print(f"Running workflow 'ExampleCustomWorkflow' with input: {workflow_input}")

        result = await aurite.execution.run_custom_workflow(
            workflow_name="ExampleCustomWorkflow",
            initial_input=workflow_input,
        )

        print("\\nWorkflow Result:")
        print(result)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        print(f"An error occurred: {e}")
    finally:
        await aurite.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
