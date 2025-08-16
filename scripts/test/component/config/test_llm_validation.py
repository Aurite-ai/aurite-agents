import os
import time

import requests
from dotenv import load_dotenv


def test_llm_validation():
    """Test that component configurations are properly validated using Pydantic models."""
    load_dotenv()

    base_url = "http://localhost:8000"
    api_key = os.getenv("API_KEY")

    headers = {"Content-Type": "application/json", "X-API-Key": api_key}

    print("=== TESTING LLM CONFIGURATION VALIDATION ===\n")

    # Use timestamp to ensure unique names
    timestamp = str(int(time.time()))

    test_llm_name = f"test-llm-{timestamp}"
    test_agent_name = f"test-agent-{timestamp}"

    print("Creating test llm config and test agent...")
    llm_config = {
        "name": test_llm_name,
        "config": {
            "provider": "anthropic",
            "model": "claude-3-haiku-20240307",
            "temperature": 0.5,
            "max_tokens": 2048,
            "default_system_prompt": "You are a helpful AI assistant by Anthropic.",
            "api_key_env_var": "ANTHROPIC_API_KEY",
        },
    }

    try:
        response = requests.post(f"{base_url}/config/components/llms", headers=headers, json=llm_config)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Valid llm configuration accepted!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    agent_config = {
        "name": test_agent_name,
        "config": {
            "type": "agent",
            "description": "Test Agent",
            "system_prompt": "You are a helpful assistant",
            "llm_config_id": test_llm_name,
        },
    }

    try:
        response = requests.post(f"{base_url}/config/components/agents", headers=headers, json=agent_config)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Valid agent configuration accepted!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    print("Getting llm config... (expecting validated_at to be None)")

    try:
        response = requests.get(f"{base_url}/config/components/llms/{test_llm_name}", headers=headers)

        if response.status_code == 200:
            result = response.json()
            if not result.get("validated_at"):
                print("✅ SUCCESS: validated_at is None!")
                # print(f"   Response: {json.dumps(result, indent=2)}")
            else:
                print(f"❌ UNEXPECTED: Expected validated_at to be None, got {result.get('validated_at')}")
                # print(f"   Response: {response.text}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Running agent, this should validate the llm")

    body = {"user_message": "Hello"}

    try:
        response = requests.post(f"{base_url}/execution/agents/{test_agent_name}/run", headers=headers, json=body)

        if response.status_code == 200:
            print("✅ SUCCESS: Agent ran successfully!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Getting llm config... (expecting validated_at to be defined)")

    try:
        response = requests.get(f"{base_url}/config/components/llms/{test_llm_name}", headers=headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("validated_at"):
                print(f"✅ SUCCESS: validated_at is {result.get('validated_at')}!")
                # print(f"   Response: {json.dumps(result, indent=2)}")
            else:
                print("❌ UNEXPECTED: validated_at is None")
                # print(f"   Response: {response.text}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Updating llm config, this should invalidate the llm")

    llm_config["config"]["max_tokens"] = 1024

    try:
        response = requests.put(f"{base_url}/config/components/llm/{test_llm_name}", headers=headers, json=llm_config)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Valid llm configuration accepted!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Getting llm config... (expecting validated_at to be None)")

    try:
        response = requests.get(f"{base_url}/config/components/llms/{test_llm_name}", headers=headers)

        if response.status_code == 200:
            result = response.json()
            if not result.get("validated_at"):
                print("✅ SUCCESS: validated_at is None!")
                # print(f"   Response: {json.dumps(result, indent=2)}")
            else:
                print(f"❌ UNEXPECTED: Expected validated_at to be None, got {result.get('validated_at')}")
                # print(f"   Response: {response.text}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Streaming agent, this should validate the llm")

    body = {"user_message": "Hello"}

    try:
        response = requests.post(f"{base_url}/execution/agents/{test_agent_name}/stream", headers=headers, json=body)

        if response.status_code == 200:
            print("✅ SUCCESS: Agent ran successfully!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Getting llm config... (expecting validated_at to be defined)")

    try:
        response = requests.get(f"{base_url}/config/components/llms/{test_llm_name}", headers=headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("validated_at"):
                print(f"✅ SUCCESS: validated_at is {result.get('validated_at')}!")
                # print(f"   Response: {json.dumps(result, indent=2)}")
            else:
                print("❌ UNEXPECTED: validated_at is None")
                # print(f"   Response: {response.text}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Updating llm config, this should invalidate the llm")

    llm_config["config"]["max_tokens"] = 512

    try:
        response = requests.put(f"{base_url}/config/components/llm/{test_llm_name}", headers=headers, json=llm_config)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Valid llm configuration accepted!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Getting llm config... (expecting validated_at to be None)")

    try:
        response = requests.get(f"{base_url}/config/components/llms/{test_llm_name}", headers=headers)

        if response.status_code == 200:
            result = response.json()
            if not result.get("validated_at"):
                print("✅ SUCCESS: validated_at is None!")
                # print(f"   Response: {json.dumps(result, indent=2)}")
            else:
                print(f"❌ UNEXPECTED: Expected validated_at to be None, got {result.get('validated_at')}")
                # print(f"   Response: {response.text}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Running the test llm endpoint")

    body = {"user_message": "Hello"}

    try:
        response = requests.post(f"{base_url}/execution/llms/{test_llm_name}/test", headers=headers)

        if response.status_code == 200:
            print("✅ SUCCESS: Test llm ran successfully!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("Getting llm config... (expecting validated_at to be defined)")

    try:
        response = requests.get(f"{base_url}/config/components/llms/{test_llm_name}", headers=headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("validated_at"):
                print(f"✅ SUCCESS: validated_at is {result.get('validated_at')}!")
                # print(f"   Response: {json.dumps(result, indent=2)}")
            else:
                print("❌ UNEXPECTED: validated_at is None")
                # print(f"   Response: {response.text}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    print("Deleting created components...")
    try:
        response = requests.delete(
            f"{base_url}/config/components/llm/{test_llm_name}", headers=headers, json=llm_config
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: llm deleted!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    try:
        response = requests.delete(
            f"{base_url}/config/components/agent/{test_agent_name}", headers=headers, json=llm_config
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: agent deleted!")
            # print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            # print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    test_llm_validation()
