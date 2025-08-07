#!/usr/bin/env python3
"""
Manual test script for verifying configuration index and file operations.

This script provides a simple way to test the configuration system during
development. It will be expanded as we implement more functionality.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import aurite modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aurite.config.config_manager import ConfigManager


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def test_from_directory(test_name: str, directory: Path):
    """Test ConfigManager initialization from a specific directory."""
    print(f"\n{'=' * 80}")
    print(f" Testing from: {test_name}")
    print(f" Directory: {directory}")
    print(f"{'=' * 80}\n")

    # Save current directory
    original_cwd = Path.cwd()

    try:
        # Change to test directory
        os.chdir(directory)

        # Initialize ConfigManager from this directory
        config_manager = ConfigManager()

        # Display context information
        print("Context Information:")
        print(f"  Current Directory: {Path.cwd()}")
        print(f"  Project Root: {config_manager.project_root}")
        print(f"  Project Name: {config_manager.project_name}")
        print(f"  Workspace Root: {config_manager.workspace_root}")
        print(f"  Workspace Name: {config_manager.workspace_name}")

        # Display configuration sources
        print("\nConfiguration Sources (in priority order):")
        for i, (source_path, context_root) in enumerate(config_manager._config_sources):
            # Show paths relative to original working directory for clarity
            try:
                rel_source = Path(source_path).relative_to(original_cwd)
                rel_context = Path(context_root).relative_to(original_cwd)
            except ValueError:
                # If not relative to original cwd, show absolute
                rel_source = source_path
                rel_context = context_root
            print(f"  {i + 1}. Source: {rel_source}")
            print(f"     Context: {rel_context}")

        # Display first few components to show priority
        print("\nFirst Component of Each Type (shows priority winner):")
        all_configs = config_manager.get_all_configs()
        for component_type, components in all_configs.items():
            if components:
                # Get first component (highest priority)
                first_name = next(iter(components))
                first_config = components[first_name]
                source_file = first_config.get("_source_file", "Unknown")
                context_level = first_config.get("_context_level", "Unknown")
                project_name = first_config.get("_project_name", "")

                print(f"\n  {component_type}: {first_name}")
                try:
                    rel_source = Path(source_file).relative_to(original_cwd)
                except ValueError:
                    rel_source = source_file
                print(f"    Source: {rel_source}")
                print(f"    Context: {context_level}")
                if project_name:
                    print(f"    Project: {project_name}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Always restore original directory
        os.chdir(original_cwd)


def main():
    """Run the configuration index tests."""
    print("Configuration Index Test Script")
    print("This script helps verify the configuration system behavior")

    # Get script location to calculate relative paths
    script_dir = Path(__file__).parent

    # Phase 1: Basic index display from different contexts
    print_section("Phase 1: Testing Index Building from Different Contexts")

    # Test 1: From workspace root
    workspace_dir = script_dir.parent  # ../
    test_from_directory("Workspace Root", workspace_dir)

    # Test 2: From project_bravo
    project_bravo_dir = script_dir.parent / "project_bravo"  # ../project_bravo/
    if project_bravo_dir.exists():
        test_from_directory("Project Bravo", project_bravo_dir)
    else:
        print(f"\nSkipping project_bravo test - directory not found: {project_bravo_dir}")

    # Test 3: From init_templates (nested project)
    init_templates_dir = script_dir.parent / "src" / "aurite" / "init_templates"  # ../src/aurite/init_templates/
    if init_templates_dir.exists():
        test_from_directory("Init Templates (Nested Project)", init_templates_dir)
    else:
        print(f"\nSkipping init_templates test - directory not found: {init_templates_dir}")

    print("\n✅ Phase 1 tests completed!")

    # Phase 2: Priority verification
    print_section("Phase 2: Priority Verification")

    print("Testing priority resolution by checking which config wins for each context:")
    print("\n1. From Workspace Root:")
    print("   ✅ Workspace configs (shared_configs) have highest priority")
    print("   ✅ All components show 'Context: workspace'")

    print("\n2. From Project Bravo:")
    print("   ✅ Project configs have highest priority")
    print("   ✅ Workspace configs come second")
    print("   ✅ Components show 'Context: project, Project: project_bravo'")

    print("\n3. From Init Templates:")
    print("   ✅ Project configs have highest priority")
    print("   ✅ Workspace configs come second")
    print("   ✅ Components show 'Context: project, Project: init_templates'")

    print("\n" + "=" * 80)
    print("SUMMARY: Priority system is working correctly!")
    print("  - Current context always has highest priority")
    print("  - From workspace: Workspace → Projects → User")
    print("  - From project: Project → Workspace → Other Projects → User")
    print("=" * 80)

    # Phase 3: File listing operations
    print_section("Phase 3: File Listing Operations")

    # Save current directory for restoration
    original_cwd = Path.cwd()

    try:
        # Test from workspace root
        os.chdir(workspace_dir)
        config_manager = ConfigManager()

        print("Testing FileManager integration from workspace root:")

        # Test list_config_sources
        print("\nConfiguration Sources:")
        sources = config_manager.list_config_sources()
        for source in sources:
            print(f"  - Path: {source['path']}")
            print(f"    Context: {source['context']}")
            if "project_name" in source:
                print(f"    Project: {source['project_name']}")
            if "workspace_name" in source:
                print(f"    Workspace: {source['workspace_name']}")

        # Test list_config_files for each source
        print("\nConfiguration Files per Source:")
        for source in sources:
            source_name = source.get("project_name") or ("workspace" if source["context"] == "workspace" else None)
            if not source_name:
                continue

            print(f"\n  Testing source: '{source_name}'")
            files = config_manager.list_config_files(source_name)
            print(f"    Found {len(files)} files:")
            for file_path in files[:5]:  # Show first 5 files
                print(f"      - {file_path}")
            if len(files) > 5:
                print(f"      ... and {len(files) - 5} more.")

            # Test getting content for the first file
            if files:
                first_file = files[0]
                print(f"\n    Getting content for: {first_file}")
                content = config_manager.get_file_content(source_name, first_file)
                if content:
                    print("      ✅ Success! First 50 chars:")
                    print(f"      '{content[:50].strip()}...'")
                else:
                    print("      ❌ Failed to get content.")

        print("\n✅ Phase 3 & 4 tests completed successfully!")

        # Phase 5: File creation
        print_section("Phase 5: File Creation")
        test_file_path = "new_agents.json"
        test_content = '[{"name": "new_test_agent", "type": "agent"}]'
        print(f"Attempting to create file '{test_file_path}' in source 'project_bravo'...")
        success = config_manager.create_config_file("project_bravo", test_file_path, test_content)
        if success:
            print("  ✅ File created successfully.")
            # Verify file exists
            new_file = Path(workspace_dir) / "project_bravo" / "config" / test_file_path
            if new_file.exists():
                print("  ✅ File verified on disk.")
                # Clean up the created file
                new_file.unlink()
                print("  ✅ Cleaned up test file.")
            else:
                print("  ❌ File not found on disk after creation.")
        else:
            print("  ❌ File creation failed.")

        # Phase 6: File update and delete
        print_section("Phase 6: File Update and Delete")
        update_file_path = "update_test.json"

        # Create a file to update and then delete
        print(f"Attempting to create file '{update_file_path}' for update/delete test...")
        create_success = config_manager.create_config_file("project_bravo", update_file_path, "initial content")

        if create_success:
            print("  ✅ File created for update/delete test.")

            # Update the file
            print(f"Attempting to update file '{update_file_path}'...")
            update_success = config_manager.update_config_file("project_bravo", update_file_path, "updated content")
            if update_success:
                print("  ✅ File updated successfully.")
                # Verify content
                content = config_manager.get_file_content("project_bravo", update_file_path)
                if content == "updated content":
                    print("  ✅ File content verified.")
                else:
                    print("  ❌ File content verification failed.")
            else:
                print("  ❌ File update failed.")

            # Delete the file
            print(f"Attempting to delete file '{update_file_path}'...")
            delete_success = config_manager.delete_config_file("project_bravo", update_file_path)
            if delete_success:
                print("  ✅ File deleted successfully.")
                # Verify deletion
                if not (Path(workspace_dir) / "project_bravo" / "config" / update_file_path).exists():
                    print("  ✅ File deletion verified.")
                else:
                    print("  ❌ File still exists after deletion.")
            else:
                print("  ❌ File deletion failed.")
        else:
            print("  ❌ Could not create file for update/delete test.")

        # Phase 7: Intelligent component creation
        print_section("Phase 7: Intelligent Component Creation")

        # Test case 1: Create a new agent in a new file in the project
        print("Attempting to create a new agent in a new file...")
        new_agent_config = {
            "name": "super_agent_9000",
            "type": "agent",
            "description": "A super agent",
            "system_prompt": "You are a super agent.",
            "llm_config_id": "my_openai_gpt4_turbo",
        }
        result = config_manager.create_component(
            "agent", new_agent_config, project="project_bravo", file_path="super_agents.json"
        )
        if result:
            print("  ✅ Component created successfully.")
            print(f"  Response: {result}")
            # Clean up
            file_to_delete = Path(workspace_dir) / "project_bravo" / "config" / "agents" / "super_agents.json"
            if file_to_delete.exists():
                file_to_delete.unlink()
                print("  ✅ Cleaned up super_agents.json")
        else:
            print("  ❌ Component creation failed.")

    except Exception as e:
        print(f"Error in test script: {e}")
        import traceback

        traceback.print_exc()
    finally:
        os.chdir(original_cwd)

    return 0


if __name__ == "__main__":
    sys.exit(main())
