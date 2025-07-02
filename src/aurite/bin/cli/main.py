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


def copy_packaged_example(packaged_path_str: str, user_project_path: Path):
    """Helper to copy a packaged example file or directory to the user's project."""
    try:
        # Access the packaged file or directory using importlib.resources
        # Assuming 'aurite.packaged' is the base for packaged resources
        source_path = importlib.resources.files("aurite.packaged").joinpath(packaged_path_str)

        if source_path.is_file():
            # If it's a file, copy it directly
            destination_path = user_project_path / source_path.name
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source_path), destination_path)
            logger(f"  Copied example file: {source_path.name} to {destination_path.parent.name}/")
        elif source_path.is_dir():
            # If it's a directory, copy the entire directory
            destination_path = user_project_path / source_path.name
            shutil.copytree(str(source_path), destination_path, dirs_exist_ok=True)
            logger(f"  Copied example directory: {source_path.name} to {user_project_path.name}/")
        else:
            logger(f"  Warning: Packaged example not found at {packaged_path_str}")
    except Exception as e:
        logger(f"  Warning: Could not copy example {packaged_path_str}: {e}")

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
        
        # 3. Create recommended subdirectories
        logger("Copying example config files...")
        copy_packaged_example(f"config/projects/{default_project_config_name}", project_path)
        copy_packaged_example("config", project_path)
        copy_packaged_example("mcp_servers", project_path)
        copy_packaged_example("custom_workflows", project_path)
        copy_packaged_example("run_example_project.py", project_path)
        copy_packaged_example(".env.example", project_path / "..")

        logger(f"\nProject '{project_path.name}' initialized successfully!")
        logger("\nNext steps:")
        logger(f"1. Navigate into your project: cd {project_path.name}")

        logger(
            "2. Ensure your environment has variables for the providers you will use (i.e. ANTHROPIC_API_KEY, OPENAI_API_KEY)"
        )
        logger("3. Start defining your components in the 'config/' subdirectories.")
        logger(
            "4. Place custom MCP server scripts in 'mcp_servers/' and custom workflow Python modules in 'custom_workflows/'."
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
