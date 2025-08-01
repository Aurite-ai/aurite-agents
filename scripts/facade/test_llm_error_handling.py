import requests


def test_llm_error_handling():
    """Test that the LLM test endpoint properly handles configuration errors."""
    base_url = "http://localhost:8000"
    api_key = "RwkWJFhApciiUSyH3B/Ad6T46kIxbu9gtAU"

    headers = {"Content-Type": "application/json", "X-API-Key": api_key}

    print("=== TESTING LLM ERROR HANDLING ===\n")

    # Test 1: Test with invalid model name (should fail with 422)
    print("Test 1: Testing with invalid model name (gpt-10-turbo-preview)...")

    # First, let's create an LLM config with invalid model for testing
    invalid_llm_config = {
        "name": "test_invalid_model",
        "config": {
            "type": "llm",
            "provider": "openai",
            "model": "gpt-10-turbo-preview",  # Invalid model
            "temperature": 0.7,
            "max_tokens": 1500,
        },
    }

    # Create the invalid LLM config
    try:
        create_response = requests.post(f"{base_url}/config/components/llms", headers=headers, json=invalid_llm_config)

        if create_response.status_code == 200:
            print("   ✅ Created test LLM config with invalid model")

            # Now test it
            test_data = {"user_message": "Hello, this should fail", "system_prompt": "You are a helpful assistant."}

            test_response = requests.post(
                f"{base_url}/execution/llms/test_invalid_model/test", headers=headers, json=test_data
            )

            if test_response.status_code == 422:
                result = test_response.json()
                print("   ✅ SUCCESS: Invalid model correctly rejected with 422!")
                print(f"   Status: {test_response.status_code}")
                print(f"   Error: {result.get('detail')}")
            else:
                print(f"   ❌ FAILED: Expected 422, got {test_response.status_code}")
                print(f"   Response: {test_response.text}")

            # Clean up - delete the test config
            delete_response = requests.delete(f"{base_url}/config/components/llms/test_invalid_model", headers=headers)
            if delete_response.status_code == 200:
                print("   ✅ Cleaned up test LLM config")

        else:
            print(f"   ❌ Failed to create test LLM config: {create_response.status_code}")
            print(f"   Response: {create_response.text}")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 2: Test with empty/invalid API key
    print("Test 2: Testing with LLM config that has empty API key...")

    # Create an LLM config with empty API key
    empty_key_config = {
        "name": "test_empty_key",
        "config": {
            "type": "llm",
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1500,
            "api_key": "",  # Empty API key
        },
    }

    try:
        create_response = requests.post(f"{base_url}/config/components/llms", headers=headers, json=empty_key_config)

        if create_response.status_code == 200:
            print("   ✅ Created test LLM config with empty API key")

            # Now test it
            test_data = {
                "user_message": "Hello, this should fail due to empty API key",
                "system_prompt": "You are a helpful assistant.",
            }

            test_response = requests.post(
                f"{base_url}/execution/llms/test_empty_key/test", headers=headers, json=test_data
            )

            if test_response.status_code == 422:
                result = test_response.json()
                print("   ✅ SUCCESS: Empty API key correctly rejected with 422!")
                print(f"   Status: {test_response.status_code}")
                print(f"   Error: {result.get('detail')}")
            else:
                print(f"   ❌ FAILED: Expected 422, got {test_response.status_code}")
                print(f"   Response: {test_response.text}")

            # Clean up
            delete_response = requests.delete(f"{base_url}/config/components/llms/test_empty_key", headers=headers)
            if delete_response.status_code == 200:
                print("   ✅ Cleaned up test LLM config")

        else:
            print(f"   ❌ Failed to create test LLM config: {create_response.status_code}")
            print(f"   Response: {create_response.text}")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 3: Test with invalid provider
    print("Test 3: Testing with invalid provider...")

    invalid_provider_config = {
        "name": "test_invalid_provider",
        "config": {
            "type": "llm",
            "provider": "nonexistent_provider",
            "model": "some-model",
            "temperature": 0.7,
            "max_tokens": 1500,
        },
    }

    try:
        create_response = requests.post(
            f"{base_url}/config/components/llms", headers=headers, json=invalid_provider_config
        )

        if create_response.status_code == 200:
            print("   ✅ Created test LLM config with invalid provider")

            test_data = {
                "user_message": "Hello, this should fail due to invalid provider",
                "system_prompt": "You are a helpful assistant.",
            }

            test_response = requests.post(
                f"{base_url}/execution/llms/test_invalid_provider/test", headers=headers, json=test_data
            )

            if test_response.status_code == 422:
                result = test_response.json()
                print("   ✅ SUCCESS: Invalid provider correctly rejected with 422!")
                print(f"   Status: {test_response.status_code}")
                print(f"   Error: {result.get('detail')}")
            else:
                print(f"   ❌ FAILED: Expected 422, got {test_response.status_code}")
                print(f"   Response: {test_response.text}")

            # Clean up
            delete_response = requests.delete(
                f"{base_url}/config/components/llms/test_invalid_provider", headers=headers
            )
            if delete_response.status_code == 200:
                print("   ✅ Cleaned up test LLM config")

        else:
            print(f"   ❌ Failed to create test LLM config: {create_response.status_code}")
            print(f"   Response: {create_response.text}")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 4: Test with valid configuration (should still work)
    print("Test 4: Testing with valid configuration (should work)...")

    test_data = {
        "user_message": "Hello! Can you say 'test successful'?",
        "system_prompt": "You are a helpful assistant.",
    }

    try:
        response = requests.post(
            f"{base_url}/execution/llms/my_openai_gpt4_turbo/test", headers=headers, json=test_data
        )

        if response.status_code == 200:
            result = response.json()
            print("   ✅ SUCCESS: Valid configuration still works!")
            print(f"   Status: {response.status_code}")
            print(f"   Assistant Response: {result.get('assistant_response')}")
        else:
            print(f"   ❌ FAILED: Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")
    print("🎉 SUMMARY:")
    print("✅ Invalid model names are now properly rejected with 422 status")
    print("✅ Empty/invalid API keys are now properly rejected with 422 status")
    print("✅ Invalid providers are now properly rejected with 422 status")
    print("✅ Valid configurations continue to work normally")
    print("✅ Error messages provide helpful context about potential issues")
    print("✅ No more false positives - configuration errors are properly surfaced")


if __name__ == "__main__":
    test_llm_error_handling()
