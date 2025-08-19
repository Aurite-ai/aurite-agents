import os
import sys
import threading
import time
from pprint import pprint

import requests

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


# --- Test Configuration ---
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"  # Use the key from .env
HEADERS = {"X-API-Key": API_KEY}
TEST_COMPONENT_NAME = "db_api_test_llm"
TEST_COMPONENT_CONFIG = {
    "name": TEST_COMPONENT_NAME,
    "type": "llm",
    "provider": "api_test_provider",
    "model": "api_test_model",
    "temperature": 0.6,
}


def run_api_server():
    """Runs the FastAPI server in a separate thread."""
    os.environ["AURITE_ENABLE_DB"] = "true"
    # We need to import this after setting the env var
    from uvicorn import run

    run("aurite.bin.api.api:app", host="0.0.0.0", port=8000, log_level="info")


def run_api_test():
    """
    Tests the API endpoints for CRUD operations in DB mode.
    """
    print("--- Starting DB API Test ---")

    # --- 1. Start API Server ---
    print("\n--- Starting API Server in DB mode ---")
    server_thread = threading.Thread(target=run_api_server, daemon=True)
    server_thread.start()
    time.sleep(5)  # Give the server time to start

    try:
        # --- Cleanup ---
        print("\n--- Cleaning up previous test data ---")
        response = requests.delete(f"{BASE_URL}/config/components/llm/{TEST_COMPONENT_NAME}", headers=HEADERS)
        if response.status_code == 200:
            print(f"Component '{TEST_COMPONENT_NAME}' deleted.")
        else:
            print(f"Component '{TEST_COMPONENT_NAME}' not found, continuing.")

        # --- 2. Create Operation ---
        print("\n--- Testing CREATE operation via API ---")
        create_payload = {
            "name": TEST_COMPONENT_NAME,
            "config": TEST_COMPONENT_CONFIG,
        }
        response = requests.post(f"{BASE_URL}/config/components/llm", json=create_payload, headers=HEADERS)
        assert response.status_code == 200, f"Create failed: {response.text}"
        create_data = response.json()
        print("Component created successfully via API.")
        pprint(create_data["component"])
        assert create_data["component"]["name"] == TEST_COMPONENT_NAME

        # --- 3. Read Operation ---
        print("\n--- Testing READ operation via API ---")
        response = requests.get(f"{BASE_URL}/config/components/llm/{TEST_COMPONENT_NAME}", headers=HEADERS)
        assert response.status_code == 200, f"Read failed: {response.text}"
        read_data = response.json()
        print("Component read successfully via API.")
        pprint(read_data)
        assert read_data["provider"] == "api_test_provider"

        # --- 4. Update Operation ---
        print("\n--- Testing UPDATE operation via API ---")
        update_payload = {"config": read_data.copy()}
        update_payload["config"]["temperature"] = 1.0
        response = requests.put(
            f"{BASE_URL}/config/components/llm/{TEST_COMPONENT_NAME}", json=update_payload, headers=HEADERS
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        print("Component updated successfully via API.")

        # Verify the update
        response = requests.get(f"{BASE_URL}/config/components/llm/{TEST_COMPONENT_NAME}", headers=HEADERS)
        assert response.status_code == 200
        updated_data = response.json()
        assert updated_data["temperature"] == 1.0
        print("Update verified successfully.")
        pprint(updated_data)

        # --- 5. Delete Operation ---
        print("\n--- Testing DELETE operation via API ---")
        response = requests.delete(f"{BASE_URL}/config/components/llm/{TEST_COMPONENT_NAME}", headers=HEADERS)
        assert response.status_code == 200, f"Delete failed: {response.text}"
        print("Component deleted successfully via API.")

        # Verify the deletion
        response = requests.get(f"{BASE_URL}/config/components/llm/{TEST_COMPONENT_NAME}", headers=HEADERS)
        assert response.status_code == 404, "Delete verification failed: component still exists"
        print("Delete verified successfully.")

        print("\n--- DB API Test Completed Successfully ---")

    finally:
        # The server is a daemon thread, so it will shut down automatically
        print("\n--- Test finished ---")


if __name__ == "__main__":
    run_api_test()
