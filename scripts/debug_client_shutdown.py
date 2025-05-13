import anyio
import logging
from pathlib import Path

from src.host.host import MCPHost
from src.config.config_models import (
    HostConfig,
    ClientConfig,  # Added RootConfig as it's needed by ClientConfig
)

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def main():
    logger.info("Starting standalone MCPHost debug script.")

    # Define a path to the dummy server relative to the project root
    dummy_server_path = PROJECT_ROOT / "tests" / "fixtures" / "servers" / "dummy_unreg_mcp_server.py"
    logger.info(f"Using dummy server path: {dummy_server_path}")

    if not dummy_server_path.exists():
        logger.error(f"Dummy server script not found at {dummy_server_path}")
        return

    # Create a minimal host configuration using the structure from the provided file
    host_config = HostConfig(
        clients=[
            ClientConfig(
                client_id="dummy_client_1",
                server_path=dummy_server_path,
                roots=[],  # Provide an empty list for roots as it's required
                capabilities=[], # Provide an empty list for capabilities
                # Assuming default timeout, routing_weight, etc. are acceptable
            )
        ]
    )

    host = MCPHost(config=host_config)

    try:
        logger.info("Initializing MCPHost...")
        await host.initialize()
        logger.info("MCPHost initialized.")

        logger.info("Waiting for 5 seconds to let client run...")
        await anyio.sleep(5)
        logger.info("Wait finished.")

    except Exception as e:
        logger.error(f"Error during host operation: {e}", exc_info=True)
    finally:
        logger.info("Shutting down MCPHost...")
        await host.shutdown()
        logger.info("MCPHost shut down.")
        logger.info("Standalone MCPHost debug script finished.")


if __name__ == "__main__":
    # Set environment variable if needed for encryption key, or handle it in config
    # For this test, we rely on default behavior if not set (e.g., auto-generation)
    # os.environ["AURITE_MCP_ENCRYPTION_KEY"] = "test_key_for_debug_script"
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
    except Exception as e:
        logger.error(f"Unhandled error in script: {e}", exc_info=True)
