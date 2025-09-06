#!/usr/bin/env python3
"""
Test script to verify that the type checking issues in execution_routes.py are resolved.
This tests the fixes for:
1. AgentConfig instantiation with potentially None config
2. LLMConfig instantiation with potentially None config
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from unittest.mock import MagicMock, patch

from aurite.lib.config.config_manager import ConfigManager
from aurite.lib.models.config.components import AgentConfig, LLMConfig
from aurite.utils.errors import ConfigurationError


def test_agent_config_with_none_handling():
    """Test that AgentConfig handles None config properly."""
    # Mock config manager
    config_manager = MagicMock(spec=ConfigManager)

    # Test case 1: config_manager returns None
    config_manager.get_config.return_value = None

    # This should raise ConfigurationError
    try:
        from aurite.bin.api.routes.execution_routes import _validate_agent

        _validate_agent("test_agent", config_manager)
        raise AssertionError("Should have raised ConfigurationError")
    except ConfigurationError as e:
        assert "Agent Config for test_agent not found" in str(e)
        print("✓ Correctly handles None agent config")

    # Test case 2: config_manager returns valid dict
    config_manager.get_config.side_effect = [
        # First call for agent config
        {"name": "test_agent", "type": "agent", "llm_config_id": "test_llm"},
        # Second call for llm config
        {"name": "test_llm", "type": "llm", "provider": "openai", "model": "gpt-4o"},
    ]

    # Mock LiteLLMClient to avoid actual validation
    with patch("aurite.bin.api.routes.execution_routes.LiteLLMClient") as mock_llm:
        mock_llm_instance = MagicMock()
        mock_llm_instance.validate.return_value = True
        mock_llm.return_value = mock_llm_instance

        try:
            from aurite.bin.api.routes.execution_routes import _validate_agent

            _validate_agent("test_agent", config_manager)
            print("✓ Successfully validates with proper configs")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            raise AssertionError(f"Should not have raised error: {e}") from e


def test_llm_config_with_none_handling():
    """Test that LLMConfig handles None config properly."""
    # Mock config manager
    config_manager = MagicMock(spec=ConfigManager)

    # Test case: llm_config is None
    config_manager.get_config.side_effect = [
        # First call for agent config
        {"name": "test_agent", "type": "agent", "llm_config_id": "missing_llm"},
        # Second call for llm config returns None
        None,
    ]

    try:
        from aurite.bin.api.routes.execution_routes import _validate_agent

        _validate_agent("test_agent", config_manager)
        raise AssertionError("Should have raised ConfigurationError")
    except ConfigurationError as e:
        assert "missing_llm was not found" in str(e)
        print("✓ Correctly handles None LLM config")


def test_direct_instantiation():
    """Test direct instantiation of configs to ensure typing is correct."""
    # Test AgentConfig
    agent_config = AgentConfig(name="test_agent", type="agent", llm_config_id="test_llm")
    assert agent_config.name == "test_agent"
    print("✓ AgentConfig instantiation works correctly")

    # Test LLMConfig
    llm_config = LLMConfig(name="test_llm", type="llm", provider="openai", model="gpt-4o")
    assert llm_config.name == "test_llm"
    assert llm_config.api_key_env_var is None  # Should default to None
    print("✓ LLMConfig instantiation works correctly")


if __name__ == "__main__":
    print("Testing execution_routes.py type checking fixes...")
    print("-" * 50)

    # Run all tests
    test_agent_config_with_none_handling()
    test_llm_config_with_none_handling()
    test_direct_instantiation()

    print("-" * 50)
    print("All tests passed! The type checking issues in execution_routes.py are fixed.")
    print("\nThe fixes ensure:")
    print("  1. Proper None checking before unpacking configs")
    print("  2. Clear variable naming to avoid type confusion")
    print("  3. Explicit error messages when configs are missing")
