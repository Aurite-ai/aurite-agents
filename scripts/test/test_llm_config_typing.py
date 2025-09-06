#!/usr/bin/env python3
"""
Test script to verify LLMConfig can be instantiated without api_key_env_var.
This tests the fix for the type checking issue where api_key_env_var was
incorrectly being reported as required.
"""

from aurite.lib.models.config.components import LLMConfig


def test_llm_config_without_api_key_env_var():
    """Test that LLMConfig can be created without api_key_env_var."""
    # This should work without any type checking errors
    llm_config = LLMConfig(name="testing", type="llm", provider="openai", model="gpt-4o")

    assert llm_config.name == "testing"
    assert llm_config.type == "llm"
    assert llm_config.provider == "openai"
    assert llm_config.model == "gpt-4o"
    assert llm_config.api_key_env_var is None  # Should default to None

    print("✓ LLMConfig created successfully without api_key_env_var")
    return llm_config


def test_llm_config_with_api_key_env_var():
    """Test that LLMConfig can still be created with api_key_env_var."""
    llm_config = LLMConfig(
        name="testing_with_key", type="llm", provider="openai", model="gpt-4o", api_key_env_var="CUSTOM_OPENAI_KEY"
    )

    assert llm_config.api_key_env_var == "CUSTOM_OPENAI_KEY"

    print("✓ LLMConfig created successfully with api_key_env_var")
    return llm_config


def test_llm_config_with_other_optional_fields():
    """Test that other optional fields also work correctly."""
    llm_config = LLMConfig(
        name="full_config",
        type="llm",
        provider="openai",
        model="gpt-4o",
        temperature=0.7,
        max_tokens=2000,
        api_base="https://custom.openai.com",
    )

    assert llm_config.temperature == 0.7
    assert llm_config.max_tokens == 2000
    assert llm_config.api_base == "https://custom.openai.com"
    assert llm_config.api_key_env_var is None  # Still defaults to None

    print("✓ LLMConfig created successfully with other optional fields")
    return llm_config


if __name__ == "__main__":
    print("Testing LLMConfig type checking fix...")
    print("-" * 50)

    # Run all tests
    config1 = test_llm_config_without_api_key_env_var()
    config2 = test_llm_config_with_api_key_env_var()
    config3 = test_llm_config_with_other_optional_fields()

    print("-" * 50)
    print("All tests passed! The type checking issue is fixed.")
    print("\nYou can now use LLMConfig like this:")
    print('  llm = LLMConfig(name="testing", type="llm", provider="openai", model="gpt-4o")')
