import typer
from pathlib import Path
import shutil
import importlib.resources
from .studio_server import start_studio_server # Added import

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main_callback():
    """
    Aurite CLI main entry point.
    Use 'aurite init --help' for information on initializing a project.
    """
    pass


logger = typer.echo  # Use typer.echo for CLI output


def copy_packaged_example(
    packaged_path_str: str, user_project_path: Path, filename: str
):
    """Helper to copy a packaged example file to the user's project."""
    try:
        # Access the packaged file using importlib.resources
        # Assuming 'aurite.packaged' is the base for packaged resources
        source_file_path = importlib.resources.files("aurite.packaged").joinpath(
            packaged_path_str
        )

        if source_file_path.is_file():
            destination_path = user_project_path / filename
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file_path, destination_path)
            logger(f"  Copied example: {filename} to {destination_path.parent.name}/")
        else:
            logger(f"  Warning: Packaged example not found at {packaged_path_str}")
    except Exception as e:
        logger(f"  Warning: Could not copy example {filename}: {e}")


@app.command("init")  # Explicitly name the command
def init(
    project_directory_name: str = typer.Argument(
        "aurite",
        help="The name of the new project directory to create. Defaults to 'aurite'.",
    ),
):
    """
    Initializes a new Aurite project with a default structure and configuration.
    If no directory name is provided, it defaults to 'aurite'.
    """
    project_path = Path(project_directory_name)

    if project_path.exists():
        logger(
            f"Error: Directory '{project_path.name}' already exists. Please choose a different name or remove the existing directory."
        )
        raise typer.Exit(code=1)

    try:
        logger(f"Initializing new Aurite Agents project at: ./{project_path}")

        # 1. Create the main project directory
        project_path.mkdir(parents=True)
        logger(f"Created project directory: {project_path}")

        default_project_config_name = "aurite_config.json"
        copy_packaged_example(
            "component_configs/projects/default_project.json",
            project_path,
            default_project_config_name,
        )

        # 3. Create recommended subdirectories
        subdirectories_to_create = [
            project_path / "config" / "agents",
            project_path / "config" / "llms",
            project_path / "config" / "clients",
            project_path / "config" / "workflows",
            project_path / "config" / "custom_workflows",
            project_path / "config" / "testing",
            project_path / "mcp_servers",
            project_path
            / "custom_workflows",  # Corrected from custom_workflows to custom_workflows
        ]
        for subdir in subdirectories_to_create:
            subdir.mkdir(parents=True, exist_ok=True)
        logger(
            "Created standard subdirectories: config/*, mcp_servers/, custom_workflows/"
        )

        # 4. Optionally, copy basic example files
        logger("Copying example configuration files...")
        copy_packaged_example(
            "component_configs/llms/default_llms.json",
            project_path / "config" / "llms",
            "llms.json",
        )
        copy_packaged_example(
            "component_configs/clients/default_clients.json",
            project_path / "config" / "clients",
            "clients.json",  # Renaming for user project
        )
        copy_packaged_example(
            "component_configs/agents/default_agents.json",
            project_path / "config" / "agents",
            "agents.json",  # Renaming for user project
        )

        copy_packaged_example(
            "component_configs/workflows/example_simple_workflow.json",
            project_path / "config" / "workflows",
            "simple_workflows.json",  # Renaming for user project
        )

        copy_packaged_example(
            "component_configs/custom_workflows/example_custom_workflow.json",
            project_path / "config" / "custom_workflows",
            "custom_workflows.json",
        )
        # Create an empty __init__.py in custom_workflows to make it a package
        (project_path / "custom_workflows" / "__init__.py").touch()  # Corrected path

        copy_packaged_example(
            "testing/planning_agent_multiple.json",
            project_path / "config" / "testing",
            "planning_agent_test.json",  # Renaming for user project
        )
        logger("Copying example workflow and MCP server...")
        copy_packaged_example(
            "example_custom_workflows/example_workflow.py",  # Corrected source path
            project_path / "custom_workflows",  # Corrected destination path
            "example_workflow.py",
        )
        copy_packaged_example(
            "example_mcp_servers/weather_mcp_server.py",
            project_path / "mcp_servers",
            "weather_mcp_server.py",
        )

        copy_packaged_example(
            "example_mcp_servers/planning_server.py",
            project_path / "mcp_servers",
            "planning_server.py",
        )

        copy_packaged_example(
            "run_test_project.py", project_path, "run_example_project.py"
        )

        logger(f"\nProject '{project_path.name}' initialized successfully!")
        logger("\nNext steps:")
        logger(f"1. Navigate into your project: cd {project_path.name}")
        logger(
            f"2. Set the PROJECT_CONFIG_PATH environment variable to '{default_project_config_name}' (or its absolute path)."
        )
        logger(
            f"   For example: export PROJECT_CONFIG_PATH=$(pwd)/{default_project_config_name}"
        )
        logger(
            "3. Ensure your environment has variables for the providers you will use (i.e. ANTHROPIC_API_KEY, OPENAI_API_KEY)"
        )
        logger("4. Start defining your components in the 'config/' subdirectories.")
        logger(
            "5. Place custom MCP server scripts in 'mcp_servers/' and custom workflow Python modules in 'custom_workflows/'."
        )  # Corrected path
        logger(
            "6. Pathing for component configs, custom workflow sources, and MCP server scripts is relative to"
        )
        logger(
            f"   the parent folder of your '{default_project_config_name}' file (i.e., ./{project_path.name}/)."
        )
        logger(
            f"   If integrating into an existing project where '{default_project_config_name}' is nested, or if placing"
        )
        logger(
            f"   custom workflows/MCP servers outside './{project_path.name}/', use '../' in your config paths to navigate correctly."
        )

    except Exception as e:
        logger(f"Error during project initialization: {e}")
        # Attempt to clean up created directory if an error occurs
        if project_path.exists():
            try:
                shutil.rmtree(project_path)
                logger(
                    f"Cleaned up partially created project directory: {project_path}"
                )
            except Exception as cleanup_e:
                logger(f"Error during cleanup: {cleanup_e}")
        raise typer.Exit(code=1)


@app.command("studio")
def studio(
    host: str = typer.Option("127.0.0.1", help="Host to bind the server to."),
    port: int = typer.Option(8080, help="Port to run the server on."),
):
    """
    Starts the Aurite Studio UI - a local web server for the frontend.
    """
    logger(f"Starting Aurite Studio UI at http://{host}:{port}")
    # The start_studio_server function itself has checks for frontend files
    start_studio_server(host=host, port=port)


if __name__ == "__main__":
    app()
