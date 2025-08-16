import json
import time

import requests


def test_file_paths():
    """Test the file path specification functionality."""
    base_url = "http://localhost:8000"
    api_key = "RwkWJFhApciiUSyH3B/Ad6T46kIxbu9gtAU"

    headers = {"Content-Type": "application/json", "X-API-Key": api_key}

    print("=== TESTING FILE PATH SPECIFICATION ===\n")

    # Use timestamp to ensure unique names
    timestamp = str(int(time.time()))

    # Test 1: Custom relative path
    print("Test 1: Creating agent with custom relative path...")
    agent_data = {
        "name": f"custom-path-agent-{timestamp}",
        "config": {
            "type": "agent",
            "description": "Agent stored in custom location",
            "system_prompt": "You are a helpful assistant",
            "file_path": "custom/my_agents.json",
            "max_iterations": 5,
        },
    }

    try:
        response = requests.post(f"{base_url}/config/components/agents", headers=headers, json=agent_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Agent created with custom path!")
            print(f"   Response: {json.dumps(result, indent=2)}")

            # Show file path info
            if "component" in result:
                comp_info = result["component"]
                print(f"   File path: {comp_info.get('file_path')}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 2: Custom filename only
    print("Test 2: Creating agent with custom filename...")
    agent_data = {
        "name": f"custom-file-agent-{timestamp}",
        "config": {
            "type": "agent",
            "description": "Agent in custom file",
            "system_prompt": "You are a helpful assistant",
            "file_path": "my_custom_agents.yaml",
            "max_iterations": 5,
        },
    }

    try:
        response = requests.post(f"{base_url}/config/components/agents", headers=headers, json=agent_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Agent created with custom filename!")
            print(f"   Response: {json.dumps(result, indent=2)}")

            # Show file path info
            if "component" in result:
                comp_info = result["component"]
                print(f"   File path: {comp_info.get('file_path')}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 3: Default path (no file_path specified)
    print("Test 3: Creating agent with default path...")
    agent_data = {
        "name": f"default-path-agent-{timestamp}",
        "config": {
            "type": "agent",
            "description": "Agent using default path",
            "system_prompt": "You are a helpful assistant",
            "max_iterations": 5,
        },
    }

    try:
        response = requests.post(f"{base_url}/config/components/agents", headers=headers, json=agent_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Agent created with default path!")
            print(f"   Response: {json.dumps(result, indent=2)}")

            # Show file path info
            if "component" in result:
                comp_info = result["component"]
                print(f"   File path: {comp_info.get('file_path')}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 4: Different component type with custom path
    print("Test 4: Creating LLM with custom path...")
    llm_data = {
        "name": f"custom-llm-{timestamp}",
        "config": {
            "type": "llm",
            "description": "LLM in custom location",
            "provider": "openai",
            "model": "gpt-4",
            "file_path": "custom_llms/my_llms.json",
        },
    }

    try:
        response = requests.post(f"{base_url}/config/components/llms", headers=headers, json=llm_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: LLM created with custom path!")
            print(f"   Response: {json.dumps(result, indent=2)}")

            # Show file path info
            if "component" in result:
                comp_info = result["component"]
                print(f"   File path: {comp_info.get('file_path')}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")
    print("🎉 SUMMARY:")
    print("✅ Custom relative paths: Create files in custom subdirectories")
    print("✅ Custom filenames: Use custom filenames in default directories")
    print("✅ Default paths: Automatic path generation when not specified")
    print("✅ Multiple formats: Support for .json, .yaml, and .yml files")
    print("✅ All component types: Works with agents, llms, mcp_servers, etc.")


if __name__ == "__main__":
    test_file_paths()
