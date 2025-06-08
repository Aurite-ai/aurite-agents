"""
Centralized logging configuration for the Aurite framework.
Uses colorlog to provide colored output for different log levels and logger names.
"""

import logging
import colorlog

DEFAULT_LOG_FORMAT = (
    "%(log_color)s%(levelname)-8s%(reset)s "
    # "%(asctime)s "  # Timestamp removed for brevity
    "[%(name)s] "  # Removed name_log_color
    "%(message)s"  # Removed message_log_color
)

DEFAULT_LOG_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",  # Default INFO color
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}

# LAYER_SPECIFIC_INFO_COLORS and LayerSpecificInfoFormatter are removed for simplification.


def setup_logging(level=logging.INFO, formatter_class=colorlog.ColoredFormatter):
    """
    Sets up colored logging for the application.

    This function configures the root logger with a ColoredFormatter.
    It removes any existing handlers on the root logger to prevent duplicate logs
    if basicConfig or this function has been called before.

    Args:
        level: The logging level to set for the root logger (e.g., logging.INFO).
        formatter_class: The formatter class to use. Defaults to colorlog.ColoredFormatter.
    """
    handler = colorlog.StreamHandler()

    # Instantiate the formatter
    formatter = formatter_class(
        fmt=DEFAULT_LOG_FORMAT,
        reset=True,
        log_colors=DEFAULT_LOG_COLORS,
        # secondary_log_colors removed as we are simplifying
        style="%",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()

    # Remove existing handlers from the root logger
    # This is important to prevent duplicate messages if basicConfig was called
    # or if this function is called multiple times.
    if root_logger.hasHandlers():
        for h in root_logger.handlers[:]:  # Iterate over a copy
            root_logger.removeHandler(h)
            h.close()  # Close the handler

    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Optionally, set levels for specific noisy loggers if needed
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("mcp.client.streamable_http").setLevel(logging.WARNING)
    # logging.getLogger('anyio').setLevel(logging.WARNING)

    # Ensure aurite package loggers also respect this level if they were configured before
    logging.getLogger("aurite").setLevel(level)


if __name__ == "__main__":
    # Example usage:
    setup_logging(level=logging.DEBUG)

    logging.debug("This is a debug message from logging_config.")
    logging.info("This is an info message from logging_config.")
    logging.warning("This is a warning message from logging_config.")
    logging.error("This is an error message from logging_config.")
    logging.critical("This is a critical message from logging_config.")

    # Example of how module-specific loggers would look
    logger_host_manager = logging.getLogger("aurite.host_manager")
    logger_host_manager.info("Info from host_manager.")

    logger_facade = logging.getLogger("aurite.execution.facade")
    logger_facade.info("Info from facade.")

    logger_agent = logging.getLogger("aurite.agents.some_agent_module")
    logger_agent.info("Info from an agent module.")
    logger_agent.debug("Debug from an agent module.")

    logger_main_script = logging.getLogger("__main__")
    logger_main_script.info("Info from a __main__ script.")
