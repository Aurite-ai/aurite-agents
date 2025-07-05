#!/usr/bin/env python3
"""
Test script to verify that disable_logging parameter works correctly.
"""

import logging
from pathlib import Path

from aurite.host_manager import Aurite


def test_logging_enabled():
    """Test with logging enabled (default)."""
    print("=== Testing with logging ENABLED ===")

    # Create Aurite instance with default logging
    aurite = Aurite(start_dir=Path.cwd(), disable_logging=False)  # noqa: F841

    # Try to log something
    logger = logging.getLogger("test_logger")
    logger.info("This should appear - logging is enabled")

    print("Root logger level:", logging.getLogger().level)
    print("Root logger handlers:", logging.getLogger().handlers)
    print()


def test_logging_disabled():
    """Test with logging disabled."""
    print("=== Testing with logging DISABLED ===")

    # Create Aurite instance with logging disabled
    aurite = Aurite(start_dir=Path.cwd(), disable_logging=True)  # noqa: F841

    # Try to log something
    logger = logging.getLogger("test_logger")
    logger.info("This should NOT appear - logging is disabled")

    print("Root logger level:", logging.getLogger().level)
    print("Root logger handlers:", logging.getLogger().handlers)
    print()


if __name__ == "__main__":
    test_logging_enabled()
    test_logging_disabled()
