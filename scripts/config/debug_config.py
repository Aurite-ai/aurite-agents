import sys
from pathlib import Path

from src.aurite.host_manager import Aurite

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def main():
    """
    Initializes the Aurite framework and prints debug information
    from the ConfigManager.
    """
    print("--- Running Debug Script ---")

    # Instantiate Aurite. It will use the current working directory to find the context.
    # We expect this script to be run from the workspace root.
    print(f"Current working directory: {Path.cwd()}")
    aurite_instance = Aurite()

    # Get the ConfigManager
    config_manager = aurite_instance.get_config_manager()

    print("\n--- Debug Information from ConfigManager ---")
    print(f"Project Root: {config_manager.project_root}")
    print(f"Workspace Root: {config_manager.workspace_root}")
    print(f"Project Name: {config_manager.project_name}")
    print(f"Workspace Name: {config_manager.workspace_name}")

    print("\n--- Config Sources ---")
    for source, context in config_manager._config_sources:
        print(f"  Source: {source}, Context: {context}")

    print("\n--- Component Index ---")
    # A more readable printout of the component index
    index = config_manager.get_all_configs()
    if not index:
        print("  Component index is empty.")
    for component_type, components in index.items():
        print(f"  Type: {component_type}")
        for component_id, config in components.items():
            source_file = config.get("_source_file", "N/A")
            context_level = config.get("_context_level", "N/A")
            project_name = config.get("_project_name", "N/A")
            workspace_name = config.get("_workspace_name", "N/A")
            print(f"    - ID: {component_id}")
            print(f"      Source File: {source_file}")
            print(f"      Context Level: {context_level}")
            print(f"      Project Name: {project_name}")
            print(f"      Workspace Name: {workspace_name}")


if __name__ == "__main__":
    main()
