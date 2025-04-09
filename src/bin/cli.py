"""
Command-line interface for interacting with the Aurite Agent Framework HostManager.
Allows registering and executing clients, agents, and workflows.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError  # Added import

# Adjust imports for new location (src/bin -> src)
from ..host_manager import HostManager
from ..config import PROJECT_ROOT_DIR
from ..host.models import (
    ClientConfig,
    AgentConfig,
    WorkflowConfig,
)
import json

# Configure logging (similar to api.py, but maybe simpler for CLI)
logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("aurite_cli")

# Create Typer app instance
app = typer.Typer(
    name="aurite-cli",
    help="CLI for managing and executing Aurite Agents and Workflows.",
    add_completion=False,
)

# Shared state for HostManager instance
state = {"host_manager": None}


# --- Helper Functions ---


async def _initialize_manager(config_path: Path) -> HostManager:
    """Initializes the HostManager."""
    logger.info(f"Initializing HostManager with config: {config_path}...")
    manager = HostManager(config_path=config_path)
    try:
        await manager.initialize()
        logger.info("HostManager initialized successfully.")
        return manager
    except Exception as e:
        logger.error(f"Failed to initialize HostManager: {e}", exc_info=True)
        raise typer.Exit(code=1)


async def _shutdown_manager(manager: Optional[HostManager]):
    """Shuts down the HostManager if it exists."""
    if manager:
        logger.info("Shutting down HostManager...")
        try:
            await manager.shutdown()
            logger.info("HostManager shutdown complete.")
        except Exception as e:
            logger.error(f"Error during HostManager shutdown: {e}", exc_info=True)
            # Don't exit here, just log the error


# --- Typer Commands ---

# Placeholder command groups
register_app = typer.Typer(help="Register new components dynamically.")
execute_app = typer.Typer(help="Execute registered components.")
app.add_typer(register_app, name="register")
app.add_typer(execute_app, name="execute")


@app.callback()
def main_callback(
    ctx: typer.Context,
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to the Host configuration JSON file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Set logging level (DEBUG, INFO, WARNING, ERROR).",
    ),
):
    """
    Main callback to initialize HostManager before running commands.
    """
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise typer.BadParameter(f"Invalid log level: {log_level}")
    logging.getLogger().setLevel(numeric_level)  # Set root logger level
    logger.setLevel(numeric_level)  # Set CLI specific logger level

    logger.debug(f"Using configuration file: {config}")
    # Initialize manager and store in context for commands to use
    # We run this synchronously using asyncio.run for the callback
    try:
        manager = asyncio.run(_initialize_manager(config))
        state["host_manager"] = manager
        ctx.call_on_close(lambda: asyncio.run(_shutdown_manager(state["host_manager"])))
    except Exception:
        # Initialization errors are logged in _initialize_manager
        # Typer will exit due to the raise typer.Exit(code=1)
        pass  # Avoid redundant logging


# --- Registration Commands (Placeholders) ---


@register_app.command("client")
def register_client(
    client_config_json: str = typer.Argument(
        ..., help="JSON string representing the ClientConfig."
    ),
):
    """Registers a new MCP client."""
    manager: Optional[HostManager] = state.get("host_manager")
    if not manager:
        logger.error("HostManager not initialized. Exiting.")
        raise typer.Exit(code=1)

    logger.info("Registering client...")
    # TODO: Implement actual registration logic
    # 1. Parse JSON string into ClientConfig model
    # 2. Resolve server_path relative to project root
    # 3. Call manager.register_client
    # 4. Handle exceptions (ValueError, FileNotFoundError, etc.)
    try:
        config_data = json.loads(client_config_json)
        # Resolve server_path relative to project root
        raw_server_path = config_data.get("server_path")
        if raw_server_path:
            resolved_path = (PROJECT_ROOT_DIR / raw_server_path).resolve()
            config_data["server_path"] = resolved_path
        else:
            logger.error("Client config JSON missing 'server_path'.")
            raise typer.Exit(code=1)

        client_config = ClientConfig(**config_data)
        asyncio.run(manager.register_client(client_config))
        logger.info(
            f"Client '{client_config.client_id}' registration command finished."
        )
    except json.JSONDecodeError:
        logger.error("Invalid JSON provided for client configuration.")
        raise typer.Exit(code=1)
    except (ValidationError, KeyError) as e:
        logger.error(f"Invalid client configuration data: {e}")
        raise typer.Exit(code=1)
    except ValueError as e:  # Catches duplicate ID etc. from manager
        logger.error(f"Failed to register client: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during client registration: {e}",
            exc_info=True,
        )
        raise typer.Exit(code=1)


@register_app.command("agent")
def register_agent(
    agent_config_json: str = typer.Argument(
        ..., help="JSON string representing the AgentConfig."
    ),
):
    """Registers a new Agent configuration."""
    manager: Optional[HostManager] = state.get("host_manager")
    if not manager:
        logger.error("HostManager not initialized. Exiting.")
        raise typer.Exit(code=1)

    logger.info("Registering agent...")
    # TODO: Implement actual registration logic
    try:
        config_data = json.loads(agent_config_json)
        agent_config = AgentConfig(**config_data)
        asyncio.run(manager.register_agent(agent_config))
        logger.info(f"Agent '{agent_config.name}' registration command finished.")
    except json.JSONDecodeError:
        logger.error("Invalid JSON provided for agent configuration.")
        raise typer.Exit(code=1)
    except (ValidationError, KeyError) as e:
        logger.error(f"Invalid agent configuration data: {e}")
        raise typer.Exit(code=1)
    except ValueError as e:  # Catches duplicate name, invalid client ID etc.
        logger.error(f"Failed to register agent: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during agent registration: {e}",
            exc_info=True,
        )
        raise typer.Exit(code=1)


@register_app.command("workflow")
def register_workflow(
    workflow_config_json: str = typer.Argument(
        ..., help="JSON string representing the WorkflowConfig."
    ),
):
    """Registers a new simple Workflow configuration."""
    manager: Optional[HostManager] = state.get("host_manager")
    if not manager:
        logger.error("HostManager not initialized. Exiting.")
        raise typer.Exit(code=1)

    logger.info("Registering workflow...")
    # TODO: Implement actual registration logic
    try:
        config_data = json.loads(workflow_config_json)
        workflow_config = WorkflowConfig(**config_data)
        asyncio.run(manager.register_workflow(workflow_config))
        logger.info(f"Workflow '{workflow_config.name}' registration command finished.")
    except json.JSONDecodeError:
        logger.error("Invalid JSON provided for workflow configuration.")
        raise typer.Exit(code=1)
    except (ValidationError, KeyError) as e:
        logger.error(f"Invalid workflow configuration data: {e}")
        raise typer.Exit(code=1)
    except ValueError as e:  # Catches duplicate name, invalid agent name etc.
        logger.error(f"Failed to register workflow: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during workflow registration: {e}",
            exc_info=True,
        )
        raise typer.Exit(code=1)


# --- Execution Commands (Placeholders) ---


@execute_app.command("agent")
def execute_agent(
    agent_name: str = typer.Argument(..., help="Name of the agent to execute."),
    message: str = typer.Argument(
        ..., help="User message to send to the agent."
    ),  # Keep as Argument, not Option
):
    """Executes a registered agent."""
    manager: Optional[HostManager] = state.get("host_manager")
    if not manager:
        logger.error("HostManager not initialized. Exiting.")
        raise typer.Exit(code=1)

    logger.info(f"Executing agent: {agent_name}")
    try:
        result = asyncio.run(manager.execute_agent(agent_name, message))
        # Extract and print final response text, handle potential errors
        final_response = result.get("final_response")
        if final_response and hasattr(final_response, "content"):
            text_content = ""
            for block in final_response.content:
                if hasattr(block, "text"):
                    text_content += block.text + "\n"
            if text_content:
                print("\n--- Agent Final Response ---")
                print(text_content.strip())
                print("--------------------------")
            else:
                print(
                    "\nAgent finished, but no text content found in the final response."
                )
        elif result.get("error"):
            print(f"\nAgent execution failed: {result.get('error')}")
        else:
            print("\nAgent execution finished, but no final response structure found.")

        logger.info(f"Agent '{agent_name}' execution finished.")
    except KeyError:
        logger.error(f"Agent '{agent_name}' not found.")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error during agent '{agent_name}' execution: {e}", exc_info=True)
        raise typer.Exit(code=1)


@execute_app.command("workflow")
def execute_workflow(
    workflow_name: str = typer.Argument(..., help="Name of the workflow to execute."),
    message: str = typer.Argument(..., help="Initial user message for the workflow."),
):
    """Executes a registered simple workflow."""
    manager: Optional[HostManager] = state.get("host_manager")
    if not manager:
        logger.error("HostManager not initialized. Exiting.")
        raise typer.Exit(code=1)

    logger.info(f"Executing workflow: {workflow_name}")
    try:
        result = asyncio.run(manager.execute_workflow(workflow_name, message))
        print(json.dumps(result, indent=2))
        if result.get("status") == "failed":
            logger.error(f"Workflow '{workflow_name}' failed: {result.get('error')}")
            raise typer.Exit(code=1)
        logger.info(f"Workflow '{workflow_name}' execution finished.")
    except KeyError:
        logger.error(f"Workflow '{workflow_name}' or one of its agents not found.")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(
            f"Error during workflow '{workflow_name}' execution: {e}", exc_info=True
        )
        raise typer.Exit(code=1)


@execute_app.command("custom-workflow")
def execute_custom_workflow(
    workflow_name: str = typer.Argument(
        ..., help="Name of the custom workflow to execute."
    ),
    initial_input_json: str = typer.Argument(
        ..., help="JSON string for the initial input."
    ),
):
    """Executes a registered custom workflow."""
    manager: Optional[HostManager] = state.get("host_manager")
    if not manager:
        logger.error("HostManager not initialized. Exiting.")
        raise typer.Exit(code=1)

    logger.info(f"Executing custom workflow: {workflow_name}")
    try:
        initial_input = json.loads(initial_input_json)
        result = asyncio.run(
            manager.execute_custom_workflow(workflow_name, initial_input)
        )
        # Custom workflows can return anything, try to print nicely
        try:
            print(json.dumps(result, indent=2))
        except TypeError:
            print(result)  # Print raw if not JSON serializable
        logger.info(f"Custom workflow '{workflow_name}' execution finished.")
    except json.JSONDecodeError:
        logger.error("Invalid JSON provided for initial input.")
        raise typer.Exit(code=1)
    except (
        KeyError,
        FileNotFoundError,
        AttributeError,
        ImportError,
        PermissionError,
        TypeError,
    ) as setup_err:
        logger.error(
            f"Error setting up or executing custom workflow '{workflow_name}': {setup_err}"
        )
        raise typer.Exit(code=1)
    except RuntimeError as exec_err:  # Error within the workflow itself
        logger.error(
            f"Error during custom workflow '{workflow_name}' execution: {exec_err}"
        )
        # Optionally print the error details if needed
        # print(f"Error details: {exec_err}", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during custom workflow '{workflow_name}' execution: {e}",
            exc_info=True,
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
