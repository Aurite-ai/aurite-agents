"""
Command-line interface for interacting with the Aurite API server.
Allows registering and executing agents, workflows, etc., via HTTP requests.
"""

import asyncio  # Add asyncio back
import httpx
import logging
import os
import sys

from dotenv import load_dotenv  # Add this import
import typer
from typing import Callable, Coroutine, Any, cast, Optional  # Added cast

# Import models needed for request bodies, even if commands aren't fully implemented

# Import models needed for request bodies, even if commands aren't fully implemented
import json

# Configure logging
logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("aurite_cli_api")

# Load environment variables from .env file
load_dotenv()  # Add this call

# Create Typer app instance
app = typer.Typer(
    name="aurite-cli",
    help="CLI for interacting with the Aurite API server.",
    add_completion=False,
)

# Shared state for API details
state = {"api_base_url": "http://localhost:8000", "api_key": None}


@app.callback()
def main_callback(
    ctx: typer.Context,
    api_base_url: str = typer.Option(
        state["api_base_url"],
        "--url",
        help="Base URL of the Aurite API server.",
        show_default=True,
    ),
    # Try reading API_KEY from environment, prompt if missing
    api_key: Optional[str] = os.environ.get("API_KEY"),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Set logging level (DEBUG, INFO, WARNING, ERROR).",
        is_eager=True,  # Process log level early
    ),
):
    """
    Callback to set log level and capture API connection details.
    """
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise typer.BadParameter(f"Invalid log level: {log_level}")
    logging.getLogger().setLevel(numeric_level)
    logger.setLevel(numeric_level)

    # Store API details
    state["api_base_url"] = api_base_url
    if not api_key:
        logger.error(
            "API Key is required. Provide via --api-key option or API_KEY environment variable."
        )
        raise typer.Exit(code=1)
    state["api_key"] = api_key
    logger.debug(f"Using API Base URL: {api_base_url}")
    logger.debug("API Key captured.")


# --- Command Groups ---
register_app = typer.Typer(help="Register new components via API.")
execute_app = typer.Typer(help="Execute components via API.")
app.add_typer(register_app, name="register")
app.add_typer(execute_app, name="execute")


# --- Helper for Running Async API Calls with CLI Error Handling ---


def run_async_with_cli_error_handling(
    async_func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any
):
    """
    Runs an async function using asyncio.run and provides standardized CLI error handling.

    Args:
        async_func: The asynchronous function to execute (e.g., _execute_agent_async_logic).
        *args: Positional arguments to pass to the async function.
        **kwargs: Keyword arguments to pass to the async function.
    """
    try:
        # Run the async logic within asyncio.run
        asyncio.run(async_func(*args, **kwargs))
        logger.info("CLI command executed successfully via API.")  # Generic success log
    except httpx.HTTPStatusError as e:
        # API returned an error status (4xx or 5xx)
        # Error details should have been logged within the async_func
        logger.error(
            f"API request failed with status {e.response.status_code}. Check previous logs for response details."
        )
        raise typer.Exit(code=1)
    except httpx.ConnectError:
        # Connection failed (already logged in async_func)
        logger.error(f"Failed to connect to the API server at {state['api_base_url']}.")
        raise typer.Exit(code=1)
    except ValueError as e:
        # Handle specific ValueErrors like invalid JSON input
        if "Invalid JSON input" in str(e):
            # Error logged in async_func, raise Typer error for user feedback
            raise typer.BadParameter(str(e))
        else:
            # Handle other potential ValueErrors
            logger.error(f"CLI command failed due to ValueError: {e}", exc_info=True)
            raise typer.Exit(code=1)
    except Exception as e:
        # Catch any other unexpected errors from the async logic or asyncio.run
        logger.error(f"CLI command failed unexpectedly: {e}", exc_info=True)
        raise typer.Exit(code=1)


# --- Async API Logic Functions (Remain largely unchanged, focus on API interaction) ---


async def _execute_agent_async_logic(agent_name: str, message: str):
    """Contains the actual async logic for executing an agent via API."""
    # TODO (Refactor): Update to use ExecutionFacade if CLI interacts directly with manager/facade in the future
    api_url = f"{state['api_base_url']}/agents/{agent_name}/execute"
    # Assign key to local var first to help mypy
    api_key_value = cast(str, state["api_key"])
    headers = {
        "X-API-Key": api_key_value,
        "Content-Type": "application/json",
    }
    payload = {"user_message": message}

    logger.info(f"Sending request to API: POST {api_url}")
    try:
        # Increase timeout to 60 seconds
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)

        logger.info(f"API Response Status: {response.status_code}")

        # Try to parse and print JSON response, fall back to raw text
        try:
            response_data = response.json()
            print(json.dumps(response_data, indent=2))
            if response.status_code >= 400:
                logger.error(f"API returned error status {response.status_code}.")
                # Optionally raise typer.Exit(code=1) on API errors
        except json.JSONDecodeError:
            logger.warning("Could not decode JSON response from API.")
            print("--- Raw API Response ---")
            print(response.text)
            print("------------------------")
            if response.status_code >= 400:
                logger.error(f"API returned error status {response.status_code}.")

        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

    except httpx.ConnectError as e:
        logger.error(f"Connection to API server failed: {e}")
        # Re-raise HTTPStatusError to be caught by the sync wrapper
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during async API call: {e}", exc_info=True
        )
        # Re-raise other exceptions to be caught by the sync wrapper
        raise


# --- Async Logic for Workflow Execution ---
async def _execute_workflow_async_logic(workflow_name: str, message: str):
    """Contains the actual async logic for executing a simple workflow via API."""
    # TODO (Refactor): Update to use ExecutionFacade if CLI interacts directly with manager/facade in the future
    api_url = f"{state['api_base_url']}/workflows/{workflow_name}/execute"
    # Assign key to local var first to help mypy
    api_key_value = cast(str, state["api_key"])
    headers = {
        "X-API-Key": api_key_value,
        "Content-Type": "application/json",
    }
    # Correct payload key for simple workflows
    payload = {"initial_user_message": message}

    logger.info(f"Sending request to API: POST {api_url}")
    try:
        # Increase timeout for potentially longer workflows (e.g., 120 seconds)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)

        logger.info(f"API Response Status: {response.status_code}")

        # Try to parse and print JSON response
        try:
            response_data = response.json()
            if response.status_code >= 400:
                logger.error(
                    f"API returned error status {response.status_code}. Response: {response_data}"
                )
                print(json.dumps(response_data, indent=2))
            else:
                if response_data.get("status") == "completed":
                    print(response_data.get("final_message"))
                else:
                    print(json.dumps(response_data, indent=2))

        except json.JSONDecodeError:
            logger.warning("Could not decode JSON response from API.")
            print("--- Raw API Response ---")
            print(response.text)
            print("------------------------")
            if response.status_code >= 400:
                logger.error(f"API returned error status {response.status_code}.")

        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

    except httpx.ConnectError as e:
        logger.error(f"Connection to API server failed: {e}")
        raise  # Re-raise to be caught by the sync wrapper
    except httpx.HTTPStatusError as e:
        # Log the status error here as well for clarity before re-raising
        logger.error(
            f"API request failed with status {e.response.status_code}. Response: {e.response.text}"
        )
        raise  # Re-raise to be caught by the sync wrapper
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during async API call: {e}", exc_info=True
        )
        raise  # Re-raise other exceptions


# --- Async Logic for Custom Workflow Execution ---
async def _execute_custom_workflow_async_logic(
    workflow_name: str, initial_input_json: str
):
    """Contains the actual async logic for executing a custom workflow via API."""
    # TODO (Refactor): Update to use ExecutionFacade if CLI interacts directly with manager/facade in the future
    api_url = f"{state['api_base_url']}/custom_workflows/{workflow_name}/execute"
    # Assign key to local var first to help mypy
    api_key_value = cast(str, state["api_key"])
    headers = {
        "X-API-Key": api_key_value,
        "Content-Type": "application/json",
    }

    # Try to parse as JSON, but fall back to string if it's not a JSON object/array
    try:
        initial_input = json.loads(initial_input_json)
    except json.JSONDecodeError:
        # If it's not valid JSON, treat it as a raw string.
        # This allows passing simple strings as input directly from the CLI.
        initial_input = initial_input_json

    payload = {"initial_input": initial_input}

    logger.info(f"Sending request to API: POST {api_url}")
    try:
        # Use a potentially longer timeout for custom workflows (e.g., 180 seconds)
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)

        logger.info(f"API Response Status: {response.status_code}")

        # Try to parse and print JSON response
        try:
            response_data = response.json()
            print(json.dumps(response_data, indent=2))
            if response.status_code >= 400:
                logger.error(
                    f"API returned error status {response.status_code}. Response: {response_data}"
                )
        except json.JSONDecodeError:
            logger.warning("Could not decode JSON response from API.")
            print("--- Raw API Response ---")
            print(response.text)
            print("------------------------")
            if response.status_code >= 400:
                logger.error(f"API returned error status {response.status_code}.")

        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

    except httpx.ConnectError as e:
        logger.error(f"Connection to API server failed: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(
            f"API request failed with status {e.response.status_code}. Response: {e.response.text}"
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during async API call: {e}", exc_info=True
        )
        raise


@execute_app.command("agent")
def execute_agent_via_api_sync(  # Make the command function synchronous
    agent_name: str = typer.Argument(..., help="Name of the agent to execute."),
    message: str = typer.Argument(..., help="User message to send to the agent."),
):
    """Executes a registered agent by calling the API endpoint."""
    # Use the error handling wrapper
    run_async_with_cli_error_handling(_execute_agent_async_logic, agent_name, message)


# --- Other Commands (Placeholders - Need similar sync wrapper pattern) ---


@execute_app.command("workflow")
def execute_workflow_via_api_sync(  # Sync wrapper
    workflow_name: str = typer.Argument(..., help="Name of the workflow to execute."),
    message: str = typer.Argument(..., help="Initial user message for the workflow."),
):
    """Executes a registered simple workflow via API."""
    # Use the error handling wrapper
    run_async_with_cli_error_handling(
        _execute_workflow_async_logic, workflow_name, message
    )


@execute_app.command("custom-workflow")
def execute_custom_workflow_via_api_sync(  # Sync wrapper
    workflow_name: str = typer.Argument(
        ..., help="Name of the custom workflow to execute."
    ),
    initial_input_json: str = typer.Argument(
        ..., help="JSON string for the initial input."
    ),
):
    """Executes a registered custom workflow via API."""
    # Use the error handling wrapper
    run_async_with_cli_error_handling(
        _execute_custom_workflow_async_logic, workflow_name, initial_input_json
    )


@register_app.command("client")
def register_client_via_api_sync(  # Sync wrapper
    client_config_json: str = typer.Argument(
        ..., help="JSON string representing the ClientConfig."
    ),
):
    """Registers a new MCP client via API. [TODO: Implement]"""
    logger.warning("Client registration via API not yet implemented.")
    # async def _logic(): ...
    # asyncio.run(_logic())


@register_app.command("agent")
def register_agent_via_api_sync(  # Sync wrapper
    agent_config_json: str = typer.Argument(
        ..., help="JSON string representing the AgentConfig."
    ),
):
    """Registers a new Agent configuration via API. [TODO: Implement]"""
    logger.warning("Agent registration via API not yet implemented.")
    # async def _logic(): ...
    # asyncio.run(_logic())


@register_app.command("workflow")
def register_workflow_via_api_sync(  # Sync wrapper
    workflow_config_json: str = typer.Argument(
        ..., help="JSON string representing the WorkflowConfig."
    ),
):
    """Registers a new simple Workflow configuration via API. [TODO: Implement]"""
    logger.warning("Workflow registration via API not yet implemented.")
    # async def _logic(): ...
    # asyncio.run(_logic())


# --- Main Execution ---

if __name__ == "__main__":
    # Simply run the Typer app. Typer handles the async commands.
    # No complex lifecycle management needed here anymore.
    app()
