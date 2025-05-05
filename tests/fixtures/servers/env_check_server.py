#!/usr/bin/env python
import os
import sys
import logging
from mcp.server.fastmcp import FastMCP  # Removed RequestContext import
import mcp.types as types  # Import MCP types

# Basic logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Environment Variables to Check ---
SECRET_VAR_1 = "TEST_SECRET_1"
SECRET_VAR_2 = "TEST_SECRET_DB_PASSWORD"
OUTPUT_FILE_ENV_VAR = "ENV_CHECK_OUTPUT_FILE"

# Create a FastMCP server instance
mcp = FastMCP("env-check-server")

# --- Define the 'check_env' tool ---
check_env_tool = types.Tool(
    name="check_env",
    description="Checks the value of a specified environment variable on the server.",
    inputSchema={
        "type": "object",
        "properties": {
            "var_name": {
                "type": "string",
                "description": "The name of the environment variable to check.",
            }
        },
        "required": ["var_name"],
    },
)


# --- Synchronous function to check env and write to file (runs at startup) ---
def check_env_and_write_output():
    logger.info("env_check_server: Checking environment and writing output.")
    output_file_path = os.getenv(OUTPUT_FILE_ENV_VAR)
    output_target = None

    if output_file_path:
        try:
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

    secret_value_1 = os.getenv(SECRET_VAR_1)
    secret_value_2 = os.getenv(SECRET_VAR_2)

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

    if output_target is not sys.stdout:
        output_target.close()
    logger.info("env_check_server: Finished writing output.")


# --- MCP Handlers ---


@mcp.handle("list_tools")
async def list_tools_handler() -> types.ListToolsResult:  # Removed ctx parameter
    """Handles the list_tools request."""
    logger.info("env_check_server: Received list_tools request.")
    return types.ListToolsResult(tools=[check_env_tool])


@mcp.handle("call_tool")
async def call_tool_handler(
    params: types.CallToolRequestParams,
) -> types.CallToolResult:  # Removed ctx parameter
    """Handles the call_tool request."""
    logger.info(f"env_check_server: Received call_tool request for tool: {params.name}")
    if params.name == "check_env":
        var_name = params.arguments.get("var_name")
        if not var_name:
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(text="Missing required argument: var_name")],
            )

        value = os.getenv(var_name, "NOT_FOUND")  # Default to NOT_FOUND if not set
        logger.info(f"env_check_server: Checked env var '{var_name}', value: '{value}'")
        return types.CallToolResult(
            isError=False, content=[types.TextContent(text=value)]
        )
    else:
        logger.warning(
            f"env_check_server: Received call for unknown tool: {params.name}"
        )
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(text=f"Unknown tool: {params.name}")],
        )


# --- Main execution block ---
if __name__ == "__main__":
    # Removed the check_env_and_write_output() call from startup

    # Start the MCP server
    logger.info("env_check_server: Starting MCP server loop...")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"env_check_server: Error during MCP run: {e}")
    finally:
        logger.info("env_check_server: MCP server loop exited.")
