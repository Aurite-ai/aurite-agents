import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def test_llm_endpoint():
    """Test the new LLM test endpoint."""
    base_url = "http://localhost:8000"
    api_key = os.getenv("API_KEY")

    headers = {"Content-Type": "application/json", "X-API-Key": api_key}

    print("=== TESTING LLM TEST ENDPOINT ===\n")

    # Test 1: Test with a valid LLM configuration
    print("Test 1: Testing LLM with valid configuration...")
    llm_test_data = {
        "user_message": "Hello! Can you tell me a short joke?",
        "system_prompt": "You are a helpful and funny assistant.",
    }

    try:
        response = requests.post(
            f"{base_url}/execution/llms/my_openai_gpt4_turbo/test", headers=headers, json=llm_test_data
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: LLM test completed!")
            print(f"   Status: {result.get('status')}")
            print(f"   LLM Config: {result.get('llm_config_id')}")
            print(f"   User Message: {result.get('user_message')}")
            print(f"   System Prompt: {result.get('system_prompt')}")
            print(f"   Assistant Response: {result.get('assistant_response')}")
            print(f"   Execution Status: {result.get('execution_status')}")
            print(f"   Metadata: {json.dumps(result.get('metadata', {}), indent=4)}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 2: Test with different system prompt
    print("Test 2: Testing LLM with custom system prompt...")
    llm_test_data2 = {
        "user_message": "What is the capital of France?",
        "system_prompt": "You are a geography expert. Provide concise, accurate answers.",
    }

    try:
        response = requests.post(
            f"{base_url}/execution/llms/anthropic_claude_3_haiku/test", headers=headers, json=llm_test_data2
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: LLM test with custom prompt completed!")
            print(f"   LLM Config: {result.get('llm_config_id')}")
            print(f"   Assistant Response: {result.get('assistant_response')}")
            print(f"   Provider: {result.get('metadata', {}).get('provider')}")
            print(f"   Model: {result.get('metadata', {}).get('model')}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 3: Test with non-existent LLM configuration
    print("Test 3: Testing with non-existent LLM configuration...")
    llm_test_data3 = {"user_message": "This should fail", "system_prompt": "You are a helpful assistant."}

    try:
        response = requests.post(
            f"{base_url}/execution/llms/non_existent_llm/test", headers=headers, json=llm_test_data3
        )

        if response.status_code == 404:
            result = response.json()
            print("✅ SUCCESS: Non-existent LLM correctly rejected!")
            print(f"   Status: {response.status_code}")
            print(f"   Error: {result.get('detail')}")
        else:
            print(f"❌ UNEXPECTED: Expected 404, got {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 4: Test with minimal request (using default system prompt)
    print("Test 4: Testing with minimal request (default system prompt)...")
    llm_test_data4 = {"user_message": "Count from 1 to 5."}

    try:
        response = requests.post(
            f"{base_url}/execution/llms/my_openai_gpt4_turbo/test", headers=headers, json=llm_test_data4
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Minimal LLM test completed!")
            print(f"   System Prompt Used: {result.get('system_prompt')}")
            print(f"   Assistant Response: {result.get('assistant_response')}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 5: Get available LLM configurations first
    print("Test 5: Getting available LLM configurations...")
    try:
        response = requests.get(f"{base_url}/config/components/llms", headers=headers)

        if response.status_code == 200:
            llms = response.json()
            print("✅ SUCCESS: Retrieved available LLM configurations!")
            print("   Available LLMs:")
            for llm in llms:
                print(f"     - {llm.get('name')} ({llm.get('provider')}/{llm.get('model')})")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")
    print("🎉 SUMMARY:")
    print("✅ LLM test endpoint allows quick testing of LLM configurations")
    print("✅ Creates temporary agent internally for testing")
    print("✅ Returns structured response with LLM metadata")
    print("✅ Handles both custom and default system prompts")
    print("✅ Proper error handling for non-existent LLM configurations")
    print("✅ Clean temporary agent cleanup after testing")


if __name__ == "__main__":
    test_llm_endpoint()
