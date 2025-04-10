"""
Redis Stream Worker for the Aurite Agent Framework.

Listens to a Redis stream for tasks (register/execute components)
and processes them using the HostManager.
"""

import asyncio
import logging
import json
import signal
import sys  # Added import
from functools import lru_cache
from typing import Optional  # Added import

import redis.asyncio as redis
from pydantic import ValidationError

# Adjust imports for new location (src/bin -> src)
from ..host_manager import HostManager
from ..config import ServerConfig
from ..host.models import ClientConfig, AgentConfig, WorkflowConfig
from ..config import PROJECT_ROOT_DIR  # For resolving client paths

# Configure logging
logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(name)s - %(message)s",
)
logger = logging.getLogger("aurite_worker")


# --- Configuration Loading ---
# Duplicated from api.py/cli.py - consider refactoring later
@lru_cache()
def get_server_config() -> ServerConfig:
    """Loads server configuration using pydantic-settings."""
    try:
        config = ServerConfig()
        logger.info("Server configuration loaded successfully.")
        logging.getLogger().setLevel(config.LOG_LEVEL.upper())
        logger.setLevel(config.LOG_LEVEL.upper())
        return config
    except ValidationError as e:
        logger.error(f"!!! Failed to load server configuration: {e}")
        raise RuntimeError(f"Server configuration error: {e}") from e


# --- Global State ---
shutdown_event = asyncio.Event()


# --- Signal Handling ---
def _handle_signal(sig, frame):
    logger.info(f"Received signal {sig}, initiating shutdown...")
    shutdown_event.set()


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


# --- Worker Logic ---


async def process_message(manager: HostManager, message_id: bytes, message_data: dict):
    """Processes a single message received from the Redis stream."""
    try:
        logger.info(f"Processing message ID: {message_id.decode()}")
        logger.debug(f"Message data: {message_data}")

        action = message_data.get("action")
        component_type = message_data.get("component_type")
        data = message_data.get("data")  # Config for register, params for execute

        if not action or not component_type or not data:
            logger.error(
                "Invalid message format: missing action, component_type, or data."
            )
            return  # Acknowledge? Or move to dead-letter queue? For now, just log and skip.

        # --- Registration Actions ---
        if action == "register":
            if component_type == "client":
                # Resolve server_path relative to project root
                raw_server_path = data.get("server_path")
                if raw_server_path:
                    resolved_path = (PROJECT_ROOT_DIR / raw_server_path).resolve()
                    data["server_path"] = resolved_path
                else:
                    logger.error("Client config data missing 'server_path'.")
                    return
                config = ClientConfig(**data)
                await manager.register_client(config)
                logger.info(f"Registered client: {config.client_id}")
            elif component_type == "agent":
                config = AgentConfig(**data)
                await manager.register_agent(config)
                logger.info(f"Registered agent: {config.name}")
            elif component_type == "workflow":
                config = WorkflowConfig(**data)
                await manager.register_workflow(config)
                logger.info(f"Registered workflow: {config.name}")
            else:
                logger.error(
                    f"Unsupported component_type for register action: {component_type}"
                )

        # --- Execution Actions ---
        elif action == "execute":
            name = data.get("name")
            if not name:
                logger.error("Missing 'name' in data for execute action.")
                return

            if component_type == "agent":
                user_message = data.get("user_message")
                if (
                    user_message is None
                ):  # Check for None explicitly, empty string might be valid
                    logger.error("Missing 'user_message' in data for execute agent.")
                    return
                result = await manager.execute_agent(name, user_message)
                logger.info(
                    f"Executed agent '{name}'. Result status (if applicable): {result.get('status', 'N/A')}"
                )
                # Optionally publish result back to Redis
            elif component_type == "workflow":
                initial_message = data.get("initial_user_message")
                if initial_message is None:
                    logger.error(
                        "Missing 'initial_user_message' in data for execute workflow."
                    )
                    return
                result = await manager.execute_workflow(name, initial_message)
                logger.info(
                    f"Executed workflow '{name}'. Status: {result.get('status')}"
                )
                # Optionally publish result back to Redis
            elif component_type == "custom_workflow":
                initial_input = data.get("initial_input")
                if initial_input is None:
                    logger.error(
                        "Missing 'initial_input' in data for execute custom_workflow."
                    )
                    return
                result = await manager.execute_custom_workflow(name, initial_input)
                logger.info(f"Executed custom workflow '{name}'.")
                # Optionally publish result back to Redis
            else:
                logger.error(
                    f"Unsupported component_type for execute action: {component_type}"
                )
        else:
            logger.error(f"Unsupported action: {action}")

    except (ValidationError, KeyError, TypeError) as e:
        logger.error(
            f"Data validation/parsing error for message {message_id.decode()}: {e}"
        )
    except ValueError as e:  # Catches duplicates, missing refs from HostManager
        logger.error(f"Processing error for message {message_id.decode()}: {e}")
    except FileNotFoundError as e:  # For client/custom workflow paths
        logger.error(
            f"File not found during processing message {message_id.decode()}: {e}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error processing message {message_id.decode()}: {e}",
            exc_info=True,
        )
    # Consider adding XACK here if using consumer groups, or XDEL if not.


async def worker_loop(config: ServerConfig, manager: HostManager):
    """Main worker loop connecting to Redis and processing messages."""
    redis_url = f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"
    logger.info(f"Connecting to Redis at {redis_url}...")
    try:
        redis_client = await redis.from_url(redis_url)
        await redis_client.ping()
        logger.info("Redis connection successful.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
        return  # Cannot proceed without Redis

    stream_name = config.REDIS_STREAM_NAME
    last_id = "$"  # Start reading from the end of the stream

    logger.info(f"Worker started. Listening to stream '{stream_name}'...")

    while not shutdown_event.is_set():
        try:
            # Use XREAD with BLOCK 0 for indefinite blocking wait
            response = await redis_client.xread({stream_name: last_id}, block=0)

            if response:
                # response is List[Tuple[bytes, List[Tuple[bytes, Dict[bytes, bytes]]]]]
                # We only listen to one stream, so take the first element
                _stream, messages = response[0]
                for message_id, message_fields_raw in messages:
                    try:
                        # Decode message fields from bytes to string
                        message_fields = {
                            k.decode("utf-8"): v.decode("utf-8")
                            for k, v in message_fields_raw.items()
                        }

                        # Assuming the actual task data is in a field named 'task_data' (or similar) as JSON string
                        task_data_json = message_fields.get("task_data")
                        if not task_data_json:
                            logger.warning(
                                f"Message {message_id.decode()} missing 'task_data' field."
                            )
                            last_id = (
                                message_id  # Update last_id even if message is bad
                            )
                            continue

                        task_data = json.loads(task_data_json)
                        await process_message(manager, message_id, task_data)

                    except json.JSONDecodeError:
                        logger.error(
                            f"Failed to decode JSON from message {message_id.decode()}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error processing fields for message {message_id.decode()}: {e}",
                            exc_info=True,
                        )
                    finally:
                        # Update last_id to process next message
                        last_id = message_id
            # If response is empty, it means the block timeout occurred (if not 0) or connection issue
            # With block=0, it should only return when there's data or an error

        except asyncio.CancelledError:
            logger.info("Worker loop cancelled.")
            break
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}. Attempting to reconnect...")
            await asyncio.sleep(5)  # Wait before retrying connection/read
            # Reset redis_client? The library might handle reconnects. Check docs.
            # For simplicity now, we just log and retry the loop.
            try:
                await redis_client.ping()  # Check connection
            except Exception:
                logger.error("Reconnect attempt failed.")
                # Consider more robust reconnect logic or exiting
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
            await asyncio.sleep(5)  # Avoid tight loop on unexpected errors

    logger.info("Worker loop finished.")
    # Close Redis connection
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed.")


async def main():
    """Main entry point for the worker."""
    # Load configuration
    try:
        config = get_server_config()
    except RuntimeError:
        sys.exit(1)  # Exit if config fails

    # Initialize HostManager
    manager: Optional[HostManager] = None
    try:
        logger.info(
            f"Initializing HostManager with config: {config.HOST_CONFIG_PATH}..."
        )
        manager = HostManager(config_path=config.HOST_CONFIG_PATH)
        await manager.initialize()
        logger.info("HostManager initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize HostManager: {e}", exc_info=True)
        sys.exit(1)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, _handle_signal, signal.SIGINT, None)
    loop.add_signal_handler(signal.SIGTERM, _handle_signal, signal.SIGTERM, None)

    # Start the worker loop
    worker_task = asyncio.create_task(worker_loop(config, manager))

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Cancel the worker task and wait for it to finish
    logger.info("Cancelling worker task...")
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Worker task successfully cancelled.")

    # Shutdown HostManager
    if manager:
        await _shutdown_manager(manager)  # Reuse shutdown helper

    logger.info("Worker shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, exiting.")


# Synchronous wrapper function for the entry point
def start():
    """Synchronous entry point for the console script."""
    logger.info("Starting worker via console script...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received during startup/runtime, exiting.")
    except Exception as e:
        logger.critical(f"Worker failed to start or crashed: {e}", exc_info=True)
        sys.exit(1)  # Exit with error code if startup fails
