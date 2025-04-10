#!/usr/bin/env python
import os
import sys
import logging
import asyncio
from mcp.server.fastmcp import FastMCP  # Import FastMCP

# Basic logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Environment Variables to Check ---
# These names should match the 'env_var_name' defined in the
# 'gcp_secrets' section of the ClientConfig in the test JSON file.
SECRET_VAR_1 = "TEST_SECRET_1"
SECRET_VAR_2 = "TEST_SECRET_DB_PASSWORD"  # Example of a more realistic name
OUTPUT_FILE_ENV_VAR = "ENV_CHECK_OUTPUT_FILE"

# Create a minimal FastMCP server instance
mcp = FastMCP("env-check-server")


async def run_server():
    logger.info("env_check_server starting.")

    output_file_path = os.getenv(OUTPUT_FILE_ENV_VAR)
    output_target = None

    if output_file_path:
        try:
            # Open in append mode in case the server restarts or runs multiple times in a test setup
            output_target = open(output_file_path, "a", encoding="utf-8")
            logger.info(f"Will write output to file: {output_file_path}")
        except IOError as e:
            logger.error(
                f"Could not open output file {output_file_path}: {e}. Falling back to stdout."
            )
            output_target = sys.stdout
    else:
        logger.info(
            "No output file specified via ENV_CHECK_OUTPUT_FILE. Writing to stdout."
        )
        output_target = sys.stdout

    # Retrieve and log the environment variables (still write to file for test assertion)
    secret_value_1 = os.getenv(SECRET_VAR_1)
    secret_value_2 = os.getenv(SECRET_VAR_2)

    # Write clearly identifiable output for the test to capture
    print(
        f"ENV_CHECK_OUTPUT: {SECRET_VAR_1}={secret_value_1}",
        file=output_target,
        flush=True,
    )
    print(
        f"ENV_CHECK_OUTPUT: {SECRET_VAR_2}={secret_value_2}",
        file=output_target,
        flush=True,
    )

    logger.info(f"Value for {SECRET_VAR_1}: {'SET' if secret_value_1 else 'NOT SET'}")
    logger.info(f"Value for {SECRET_VAR_2}: {'SET' if secret_value_2 else 'NOT SET'}")

    logger.info("env_check_server finished writing output.")

    # Close the file if it was opened
    if output_target is not sys.stdout:
        output_target.close()

    # Run the MCP server briefly to handle initialization, then exit
    # This allows the host's stdio_client to connect and disconnect cleanly
    try:
        logger.info("Starting minimal MCP server loop...")
        # Run the server with a short timeout to allow initialization then exit
        await asyncio.wait_for(
            mcp.run(transport="stdio", run_forever=False), timeout=2.0
        )
        logger.info("MCP server loop finished or timed out.")
    except asyncio.TimeoutError:
        logger.info("MCP server run timed out as expected.")
    except Exception as e:
        logger.error(f"Error running MCP server loop: {e}")


if __name__ == "__main__":
    asyncio.run(run_server())
