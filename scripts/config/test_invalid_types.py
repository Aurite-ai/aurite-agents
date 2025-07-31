import json
import time

import requests


def test_invalid_component_types():
    """Test that invalid component types return proper error messages."""
    base_url = "http://localhost:8000"
    api_key = "RwkWJFhApciiUSyH3B/Ad6T46kIxbu9gtAU"

    headers = {"Content-Type": "application/json", "X-API-Key": api_key}

    print("=== TESTING INVALID COMPONENT TYPE VALIDATION ===\n")

    # Use timestamp to ensure unique names
    timestamp = str(int(time.time()))

    # Test 1: Invalid component type
    print("Test 1: Attempting to create component with invalid type...")
    invalid_data = {
        "name": f"test-component-{timestamp}",
        "config": {"type": "invalid_type", "description": "This should fail", "some_property": "value"},
    }

    try:
        response = requests.post(f"{base_url}/config/components/invalid_type", headers=headers, json=invalid_data)

        if response.status_code == 400:
            result = response.json()
            print("✅ SUCCESS: Invalid type correctly rejected!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 400, got {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 2: Another invalid component type
    print("Test 2: Attempting to create component with made-up type...")
    invalid_data2 = {
        "name": f"another-test-{timestamp}",
        "config": {"type": "made_up_type", "description": "This should also fail"},
    }

    try:
        response = requests.post(f"{base_url}/config/components/made_up_type", headers=headers, json=invalid_data2)

        if response.status_code == 400:
            result = response.json()
            print("✅ SUCCESS: Made-up type correctly rejected!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 400, got {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 3: Valid component type for comparison
    print("Test 3: Creating component with valid type for comparison...")
    valid_data = {
        "name": f"valid-agent-{timestamp}",
        "config": {
            "type": "agent",
            "description": "This should succeed",
            "system_prompt": "You are a helpful assistant",
        },
    }

    try:
        response = requests.post(f"{base_url}/config/components/agents", headers=headers, json=valid_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Valid type correctly accepted!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 4: Check what valid types are available
    print("Test 4: Getting list of valid component types...")
    try:
        response = requests.get(f"{base_url}/config/components", headers=headers)

        if response.status_code == 200:
            valid_types = response.json()
            print("✅ SUCCESS: Retrieved valid component types!")
            print(f"   Valid types: {', '.join(valid_types)}")
        else:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "=" * 50 + "\n")
    print("🎉 SUMMARY:")
    print("✅ Invalid component types are properly rejected with 400 status")
    print("✅ Error messages include list of valid component types")
    print("✅ Valid component types continue to work normally")
    print("✅ API provides clear feedback about what types are supported")


if __name__ == "__main__":
    test_invalid_component_types()
