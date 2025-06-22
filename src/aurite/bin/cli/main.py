import typer
from pathlib import Path
import shutil
import importlib.resources
from .studio_server import start_studio_server  # Added import

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
            shutil.copy2(str(source_file_path), destination_path)
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
            project_path / "config" / "mcp_servers",
            project_path / "config" / "workflows",
            project_path / "config" / "custom_workflows",
            project_path / "config" / "testing",
            project_path / "example_mcp_servers",
            project_path / "example_custom_workflows",
        ]
        for subdir in subdirectories_to_create:
            subdir.mkdir(parents=True, exist_ok=True)
        logger(
            "Created standard subdirectories: config/, example_mcp_servers/, example_custom_workflows/"
        )

        # 4. Optionally, copy basic example files
        logger("Copying example configuration files...")
        copy_packaged_example(
            "component_configs/llms/example_llms.json",
            project_path / "config" / "llms",
            "llms.json",
        )
        copy_packaged_example(
            "component_configs/mcp_servers/example_mcp_servers.json",
            project_path / "config" / "mcp_servers",
            "example_mcp_servers.json",
        )
        copy_packaged_example(
            "component_configs/agents/example_agents.json",
            project_path / "config" / "agents",
            "agents.json",  # Renaming for user project
        )

        copy_packaged_example(
            "component_configs/custom_workflows/example_custom_workflow.json",
            project_path / "config" / "custom_workflows",
            "custom_workflows.json",
        )
        # Copy the __init__.py to make the custom workflows directory a package
        copy_packaged_example(
            "example_custom_workflows/__init__.py",
            project_path / "example_custom_workflows",
            "__init__.py",
        )

        copy_packaged_example(
            "testing/planning_agent_multiple.json",
            project_path / "config" / "testing",
            "planning_agent_test.json",  # Renaming for user project
        )
        logger("Copying example workflow and MCP server...")
        copy_packaged_example(
            "example_custom_workflows/example_workflow.py",  # Corrected source path
            project_path / "example_custom_workflows",  # Corrected destination path
            "example_workflow.py",
        )
        copy_packaged_example(
            "example_mcp_servers/weather_mcp_server.py",
            project_path / "example_mcp_servers",
            "weather_mcp_server.py",
        )

        copy_packaged_example(
            "example_mcp_servers/planning_server.py",
            project_path / "example_mcp_servers",
            "planning_server.py",
        )

        copy_packaged_example(
            "run_test_project.py", project_path, "run_example_project.py"
        )

        # Create .env.example file
        env_example_content = (
            "OPENAI_API_KEY=\n" "SMITHERY_API_KEY=\n" "SMITHERY_PROFILE_ID=\n" "API_KEY=my_custom_key\n" "PROJECT_CONFIG_PATH=aurite_config.json\n"
        )
        env_example_path = project_path / ".." / ".env.example"
        env_example_path.write_text(env_example_content)
        logger("  Created example environment file: .env.example")

        logger(f"\nProject '{project_path.name}' initialized successfully!")
        logger("\nNext steps:")
        logger(f"1. Navigate into your project: cd {project_path.name}")

        logger(
            "2. Ensure your environment has variables for the providers you will use (i.e. ANTHROPIC_API_KEY, OPENAI_API_KEY)"
        )
        logger("3. Start defining your components in the 'config/' subdirectories.")
        logger(
            "4. Place custom MCP server scripts in 'example_mcp_servers/' and custom workflow Python modules in 'example_custom_workflows/'."
        )
        logger(
            "5. Pathing for component configs, custom workflow sources, and MCP server scripts is relative to"
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
