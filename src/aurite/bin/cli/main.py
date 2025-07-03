import typer
from pathlib import Path
import shutil
import importlib.resources
from importlib.abc import Traversable
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


def copy_project_template(template_path: Traversable, project_path: Path):
    """
    Copies the entire project template from the 'packaged' directory,
    excluding specified files/directories.
    """
    excluded_items = {"__init__.py", "__pycache__", "static_ui", "testing"}

    for item in template_path.iterdir():
        if item.name in excluded_items:
            continue

        destination = project_path / item.name
        try:
            if item.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
                logger(f"  Copied directory: {item.name}")
            elif item.is_file():
                shutil.copy2(item, destination)
                logger(f"  Copied file: {item.name}")
        except Exception as e:
            logger(f"  Warning: Could not copy {item.name}: {e}")


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

        # 2. Copy the entire project template from 'aurite.packaged'
        logger("Copying project template...")
        template_root = importlib.resources.files("aurite.packaged")
        copy_project_template(template_root, project_path)

        logger(f"\nProject '{project_path.name}' initialized successfully!")
        logger("\nNext steps:")
        logger(f"1. Navigate into your project: cd {project_path.name}")
        logger("2. Create and populate your .env file from .env.example.")
        logger(
            "3. Explore the `config` directory to see examples of how to define agents, LLMs, and tools."
        )
        logger(
            "4. Run the example project to see it in action: python run_example_project.py"
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
