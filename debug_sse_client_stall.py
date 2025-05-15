import asyncio
import logging
import anyio
from mcp.client.sse import sse_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_sse")

async def run_sse_client_test():
    url = "http://localhost:8082/sse" # Make sure sse_example_server.py is running
    logger.info(f"Attempting to connect to SSE server at {url}")
    try:
        async with anyio.create_task_group() as tg:
            client_task_scope = anyio.CancelScope()

            async def sse_task_wrapper(scope: anyio.CancelScope):
                with scope:
                    logger.info("sse_task_wrapper: Starting sse_client context manager...")
                    try:
                        async with sse_client(url) as (reader, writer):
                            logger.info("sse_task_wrapper: Successfully entered sse_client context.")
                            logger.info("sse_task_wrapper: Streams obtained. Sleeping for 5 seconds...")
                            await anyio.sleep(5)
                            logger.info("sse_task_wrapper: Sleep finished. Task should be cancellable now.")
                            # Simulate work or just wait for cancellation
                            await anyio.Event().wait() # Wait indefinitely until cancelled
                    except anyio.get_cancelled_exc_class():
                        logger.info("sse_task_wrapper: Explicitly cancelled.")
                        raise
                    except Exception as e:
                        logger.error(f"sse_task_wrapper: Error within sse_client context: {e}", exc_info=True)
                        raise
                    finally:
                        logger.info("sse_task_wrapper: Exiting sse_client context manager and task.")

            tg.start_soon(sse_task_wrapper, client_task_scope)

            logger.info("Main task: Started sse_task_wrapper. Sleeping for 10 seconds before cancelling.")
            await anyio.sleep(10)

            logger.info("Main task: Attempting to cancel sse_task_wrapper via its scope.")
            client_task_scope.cancel()
            logger.info("Main task: Cancellation requested for sse_task_wrapper.")

    except Exception as e:
        logger.error(f"Main task: An error occurred: {e}", exc_info=True)
    finally:
        logger.info("Main task: Exiting run_sse_client_test.")

async def main():
    logger.info("Starting SSE client debug script.")
    # Run the test with a timeout to prevent indefinite hanging if cancellation fails
    try:
        with anyio.move_on_after(20): # Overall timeout for the debug script
            await run_sse_client_test()
        logger.info("SSE client debug script finished within timeout.")
    except TimeoutError:
        logger.error("SSE client debug script TIMED OUT. Cancellation likely failed.")
    except Exception as e:
        logger.error(f"SSE client debug script failed with an unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    anyio.run(main)
