import typer
from pathlib import Path
import json
import shutil
import importlib.resources

app = typer.Typer()

logger = typer.echo # Use typer.echo for CLI output

def copy_packaged_example(packaged_path_str: str, user_project_path: Path, filename: str):
    """Helper to copy a packaged example file to the user's project."""
    try:
        # Access the packaged file using importlib.resources
        # Assuming 'aurite_agents.packaged' is the base for packaged resources
        source_file_path = importlib.resources.files("aurite_agents.packaged").joinpath(packaged_path_str)

        if source_file_path.is_file():
            destination_path = user_project_path / filename
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file_path, destination_path)
            logger(f"  Copied example: {filename} to {destination_path.parent.name}/")
        else:
            logger(f"  Warning: Packaged example not found at {packaged_path_str}")
    except Exception as e:
        logger(f"  Warning: Could not copy example {filename}: {e}")


@app.command()
def init(
    project_directory_name: str = typer.Argument(
        ..., help="The name of the new project directory to create."
    )
):
    """
    Initializes a new Aurite Agents project with a default structure and configuration.
    """
    project_path = Path(project_directory_name)

    if project_path.exists():
        logger(f"Error: Directory '{project_path}' already exists. Please choose a different name or remove the existing directory.")
        raise typer.Exit(code=1)

    try:
        logger(f"Initializing new Aurite Agents project at: ./{project_path}")

        # 1. Create the main project directory
        project_path.mkdir(parents=True)
        logger(f"Created project directory: {project_path}")

        # 2. Create a default project configuration file (e.g., aurite_config.json)
        default_project_config_name = "aurite_config.json"
        project_config_content = {
            "name": project_path.name,
            "description": f"A new Aurite Agents project: {project_path.name}",
            "clients": [],
            "llms": [],
            "agents": [],
            "simple_workflows": [],
            "custom_workflows": [],
        }
        project_config_file_path = project_path / default_project_config_name
        with open(project_config_file_path, "w") as f:
            json.dump(project_config_content, f, indent=4)
        logger(f"Created main project configuration: {default_project_config_name}")

        # 3. Create recommended subdirectories
        subdirectories_to_create = [
            project_path / "config" / "agents",
            project_path / "config" / "llms",
            project_path / "config" / "clients",
            project_path / "config" / "workflows",
            project_path / "config" / "custom_workflows",
            project_path / "mcp_servers",
            project_path / "custom_workflow_src",
        ]
        for subdir in subdirectories_to_create:
            subdir.mkdir(parents=True, exist_ok=True)
        logger("Created standard subdirectories: config/*, mcp_servers/, custom_workflow_src/")

        # 4. Optionally, copy basic example files
        logger("Copying example configuration files...")
        copy_packaged_example(
            "component_configs/llms/default_llms.json",
            project_path / "config" / "llms",
            "default_llms.json"
        )
        copy_packaged_example(
            "component_configs/clients/default_clients.json",
            project_path / "config" / "clients",
            "example_clients.json" # Renaming for user project
        )
        copy_packaged_example(
            "component_configs/agents/default_agents.json",
            project_path / "config" / "agents",
            "example_agent.json" # Renaming for user project
        )
        # Create an empty __init__.py in custom_workflow_src to make it a package
        (project_path / "custom_workflow_src" / "__init__.py").touch()


        logger(f"\nProject '{project_path.name}' initialized successfully!")
        logger(f"\nNext steps:")
        logger(f"1. Navigate into your project: cd {project_path.name}")
        logger(f"2. Set the PROJECT_CONFIG_PATH environment variable to '{default_project_config_name}' (or its absolute path).")
        logger(f"   For example: export PROJECT_CONFIG_PATH=$(pwd)/{default_project_config_name}")
        logger(f"3. Start defining your components in the 'config/' subdirectories.")
        logger(f"4. Place custom MCP server scripts in 'mcp_servers/' and custom workflow Python modules in 'custom_workflow_src/'.")

    except Exception as e:
        logger(f"Error during project initialization: {e}")
        # Attempt to clean up created directory if an error occurs
        if project_path.exists():
            try:
                shutil.rmtree(project_path)
                logger(f"Cleaned up partially created project directory: {project_path}")
            except Exception as cleanup_e:
                logger(f"Error during cleanup: {cleanup_e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
