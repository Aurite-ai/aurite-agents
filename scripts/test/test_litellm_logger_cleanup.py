#!/usr/bin/env python3
"""
Test script to verify that the LiteLLMClient properly cleans up its logger when deleted.
"""

import logging
import os
import sys

# Add the src directory to the path so we can import aurite modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.models.config.components import LLMConfig


def test_logger_cleanup():
    """Test that the logger is properly cleaned up when LiteLLMClient is deleted."""
    print("Testing LiteLLMClient logger cleanup...")

    # Create a test LLM config
    config = LLMConfig(
        name="test_llm_config", provider="openai", model="gpt-3.5-turbo", temperature=0.7, max_tokens=100
    )

    # Create the client
    client = LiteLLMClient(config)

    # Get reference to the logger
    litellm_logger = client.litellm_logger
    original_handler_count = len(litellm_logger.handlers)
    original_level = litellm_logger.level

    print("Initial logger state:")
    print(f"  - Handler count: {original_handler_count}")
    print(f"  - Log level: {original_level}")

    # Delete the client (this should trigger __del__)
    del client

    # Check the logger state after deletion
    final_handler_count = len(litellm_logger.handlers)
    final_level = litellm_logger.level

    print("Final logger state:")
    print(f"  - Handler count: {final_handler_count}")
    print(f"  - Log level: {final_level}")

    # Verify cleanup occurred
    if final_handler_count == 0 and final_level == logging.CRITICAL:
        print("✅ Logger cleanup successful!")
        return True
    else:
        print("❌ Logger cleanup failed!")
        return False


def test_multiple_clients():
    """Test that multiple clients don't interfere with each other's cleanup."""
    print("\nTesting multiple LiteLLMClient instances...")

    config = LLMConfig(
        name="test_llm_config", provider="openai", model="gpt-3.5-turbo", temperature=0.7, max_tokens=100
    )

    # Create multiple clients
    client1 = LiteLLMClient(config)
    client2 = LiteLLMClient(config)

    # They should share the same logger instance (same name)
    assert client1.litellm_logger is client2.litellm_logger, "Clients should share the same logger"

    shared_logger = client1.litellm_logger
    print(f"Shared logger handler count: {len(shared_logger.handlers)}")

    # Delete first client
    del client1

    # Logger should still be functional for the second client
    print(f"After deleting client1, handler count: {len(shared_logger.handlers)}")

    # Delete second client
    del client2

    # Now logger should be cleaned up
    print(f"After deleting client2, handler count: {len(shared_logger.handlers)}")
    print(f"Final log level: {shared_logger.level}")

    if len(shared_logger.handlers) == 0 and shared_logger.level == logging.CRITICAL:
        print("✅ Multiple client cleanup successful!")
        return True
    else:
        print("❌ Multiple client cleanup failed!")
        return False


if __name__ == "__main__":
    success1 = test_logger_cleanup()
    success2 = test_multiple_clients()

    if success1 and success2:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
