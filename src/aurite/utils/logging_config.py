"""
Centralized logging configuration for the Aurite framework.
Uses colorlog to provide colored output for different log levels and logger names.
"""

import logging
import os

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

# Global flag to track if logging has been disabled
_logging_disabled = False


def disable_all_logging():
    """Disable all logging globally."""
    global _logging_disabled
    _logging_disabled = True
    # Disable all logging by setting the root logger to CRITICAL+1
    logging.getLogger().setLevel(logging.CRITICAL + 1)
    # Also disable all existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


def setup_logging_if_needed(disable_logging: bool = False):
    """Setup logging configuration unless explicitly disabled."""
    global _logging_disabled

    if disable_logging or _logging_disabled:
        disable_all_logging()
        return

    # Only setup logging if it hasn't been disabled
    if not _logging_disabled:
        try:
            log_level_str = os.getenv("AURITE_LOG_LEVEL", "INFO").upper()
            numeric_level = getattr(logging, log_level_str, logging.INFO)
            setup_logging(level=numeric_level)
        except ImportError:
            logger = logging.getLogger(__name__)
            logger.warning("aurite.utils.logging_config not found. Colored logging will not be applied.")
            if not logging.getLogger().hasHandlers():
                log_level_str = os.getenv("AURITE_LOG_LEVEL", "INFO").upper()
                numeric_level = getattr(logging, log_level_str, logging.INFO)
                logging.basicConfig(level=numeric_level)


class SafeColoredFormatter(colorlog.ColoredFormatter):
    """
    A wrapper around ColoredFormatter that handles shutdown scenarios gracefully.

    During Python interpreter shutdown, modules can be garbage collected and become None,
    which can cause AttributeErrors. This formatter catches those errors and falls back
    to basic formatting.
    """

    def format(self, record):
        try:
            # Try to use the colorlog formatter normally
            return super().format(record)
        except (AttributeError, ImportError):
            # During shutdown, colorlog or its attributes might be None
            # Fall back to basic formatting without colors
            try:
                # Try basic formatting
                basic_format = "%(levelname)-8s [%(name)s] %(message)s"
                formatter = logging.Formatter(basic_format)
                return formatter.format(record)
            except Exception:
                # If even basic formatting fails, return the raw message
                return f"{record.levelname} [{record.name}] {record.getMessage()}"


def setup_logging(level=logging.INFO, formatter_class=None):
    """
    Sets up colored logging for the application.

    This function configures the root logger with a ColoredFormatter.
    It removes any existing handlers on the root logger to prevent duplicate logs
    if basicConfig or this function has been called before.

    Args:
        level: The logging level to set for the root logger (e.g., logging.INFO).
        formatter_class: The formatter class to use. Defaults to SafeColoredFormatter.
    """
    # Use SafeColoredFormatter by default to handle shutdown scenarios
    if formatter_class is None:
        formatter_class = SafeColoredFormatter
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
    logger_aurite = logging.getLogger("aurite.aurite")
    logger_aurite.info("Info from aurite.")

    logger_facade = logging.getLogger("aurite.execution.aurite_engine")
    logger_facade.info("Info from engine.")

    logger_agent = logging.getLogger("aurite.agents.some_agent_module")
    logger_agent.info("Info from an agent module.")
    logger_agent.debug("Debug from an agent module.")

    logger_main_script = logging.getLogger("__main__")
    logger_main_script.info("Info from a __main__ script.")
