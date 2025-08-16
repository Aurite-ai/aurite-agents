import os
import sys
from pprint import pprint

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aurite.lib.config import ConfigManager


def run_crud_test():
    """
    Tests CRUD operations for components using the ConfigManager in DB mode.
    """
    print("--- Starting DB CRUD Test ---")

    # --- 1. Setup: Ensure DB mode is enabled ---
    os.environ["AURITE_ENABLE_DB"] = "true"
    print(f"AURITE_ENABLE_DB is set to: {os.getenv('AURITE_ENABLE_DB')}")

    # --- 2. Initialization ---
    print("\n--- Initializing ConfigManager in DB mode ---")
    config_manager = ConfigManager()
    print("ConfigManager initialized.")

    # --- 3. Create Operation ---
    print("\n--- Testing CREATE operation ---")
    test_component_name = "db_crud_test_llm"
    test_component_config = {
        "name": test_component_name,
        "type": "llm",
        "provider": "test_provider",
        "model": "test_model",
        "temperature": 0.5,
    }
    print(f"Creating component: '{test_component_name}'")
    create_response = config_manager.create_component("llm", test_component_config)
    assert create_response is not None, "Create operation failed"
    print("Component created successfully.")
    pprint(create_response.component)

    # --- 4. Read Operation ---
    print("\n--- Testing READ operation ---")
    print(f"Reading component: '{test_component_name}'")
    read_config = config_manager.get_config("llm", test_component_name)
    assert read_config is not None, "Read operation failed: component not found"
    assert read_config["provider"] == "test_provider", "Read data mismatch"
    print("Component read successfully.")
    pprint(read_config)

    # --- 5. Update Operation ---
    print("\n--- Testing UPDATE operation ---")
    updated_config_data = read_config.copy()
    updated_config_data["temperature"] = 0.9
    print(f"Updating component: '{test_component_name}' with new temperature")
    update_success = config_manager.update_component("llm", test_component_name, updated_config_data)
    assert update_success, "Update operation failed"
    print("Component updated successfully.")

    # Verify the update
    reread_config = config_manager.get_config("llm", test_component_name)
    assert reread_config is not None, "Failed to re-read component after update"
    assert reread_config["temperature"] == 0.9, "Update verification failed"
    print("Update verified successfully.")
    pprint(reread_config)

    # --- 6. Delete Operation ---
    print("\n--- Testing DELETE operation ---")
    print(f"Deleting component: '{test_component_name}'")
    delete_success = config_manager.delete_config("llm", test_component_name)
    assert delete_success, "Delete operation failed"
    print("Component deleted successfully.")

    # Verify the deletion
    deleted_config = config_manager.get_config("llm", test_component_name)
    assert deleted_config is None, "Delete verification failed: component still exists"
    print("Delete verified successfully.")

    print("\n--- DB CRUD Test Completed Successfully ---")


if __name__ == "__main__":
    run_crud_test()
