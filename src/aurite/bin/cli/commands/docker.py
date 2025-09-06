import os
import socket
import subprocess
from pathlib import Path
from typing import Optional

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9
    from importlib_resources import files  # type: ignore

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
logger = console.print


# Docker helper functions
def _check_docker_installed() -> bool:
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            return False

        # Check if Docker daemon is running
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _check_port_available(port: int) -> bool:
    """Check if port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) != 0
    except Exception:
        return False


def _validate_project_directory(path: str) -> bool:
    """Check if directory is a valid Aurite project."""
    aurite_file = Path(path) / ".aurite"
    return aurite_file.exists()


def _find_env_file(project_path: str, env_file: Optional[str] = None) -> Optional[str]:
    """Find environment file, checking common locations."""
    if env_file and Path(env_file).exists():
        return env_file

    # Check common locations
    common_locations = [
        Path(project_path) / ".env",
        Path(".env"),
        Path(project_path) / ".env.example",
        Path(".env.example"),
    ]

    for location in common_locations:
        if location.exists():
            return str(location)

    return None


def _get_container_status(container_name: str) -> str:
    """Get the status of a Docker container."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return "not found"
    except Exception:
        return "error"


def _container_exists(container_name: str) -> bool:
    """Check if a container with the given name exists."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and container_name in result.stdout
    except Exception:
        return False


def _pull_image(image_name: str) -> bool:
    """Pull the latest Docker image."""
    try:
        logger(f"[bold blue]Pulling Docker image: {image_name}[/bold blue]")
        result = subprocess.run(["docker", "pull", image_name], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def docker_command(
    action: str = typer.Argument("run", help="Docker action: run, stop, logs, shell, status, pull, build, init"),
    project_path: str = typer.Option(".", "--project", "-p", help="Path to Aurite project directory"),
    container_name: str = typer.Option("aurite-server", "--name", "-n", help="Container name"),
    port: int = typer.Option(8000, "--port", help="Port to expose (default: 8000)"),
    env_file: Optional[str] = typer.Option(None, "--env-file", "-e", help="Path to environment file"),
    version_tag: str = typer.Option("latest", "--version", "-v", help="Docker image version"),
    detach: bool = typer.Option(True, "--detach/--no-detach", "-d/-D", help="Run in background"),
    pull: bool = typer.Option(False, "--pull", help="Pull latest image before running"),
    force: bool = typer.Option(False, "--force", "-f", help="Force action (e.g., remove existing container)"),
    build_tag: Optional[str] = typer.Option(
        None, "--build-tag", "-t", help="Tag for built image (e.g., my-project:latest)"
    ),
    push_after_build: bool = typer.Option(False, "--push", help="Push built image to registry after building"),
    regenerate: bool = typer.Option(False, "--regenerate", help="Regenerate Dockerfile.aurite and .dockerignore"),
    dockerfile: Optional[str] = typer.Option(
        None, "--dockerfile", help="Path to custom Dockerfile (build action only)"
    ),
):
    """
    Manage Aurite Docker containers.

    Actions:
      run     - Start a new container (mounts project as volume)
      stop    - Stop running container
      logs    - View container logs
      shell   - Open shell in container
      status  - Check container status
      pull    - Pull latest image
      build   - Build custom image with project embedded
      init    - Create Docker files without building

    Build Notes:
      The build and init actions create Dockerfile.aurite and .dockerignore files that
      are saved in your project directory for customization. Edit the USER CUSTOMIZATION
      SECTION in Dockerfile.aurite to add dependencies, then build.
      Use --regenerate to overwrite existing Docker files with fresh templates.
      Use --dockerfile to specify a custom Dockerfile path for the build action.
    """

    # Validate Docker installation
    if not _check_docker_installed():
        logger("[bold red]✗ Docker is not installed or not running[/bold red]")
        logger("Please install Docker and ensure the Docker daemon is running.")
        raise typer.Exit(code=1)

    image_name = f"aurite/aurite-agents:{version_tag}"

    if action == "run":
        # Pre-flight checks
        logger("[bold green]🐳 Starting Aurite Docker container...[/bold green]")

        # Check if project directory is valid
        if not _validate_project_directory(project_path):
            logger(f"[bold yellow]⚠ Warning:[/bold yellow] No .aurite file found in {project_path}")
            if not typer.confirm("Continue anyway?"):
                raise typer.Exit()
        else:
            logger(f"[bold green]✓[/bold green] Found Aurite project at {project_path}")

        # Find environment file
        found_env_file = _find_env_file(project_path, env_file)
        if found_env_file:
            logger(f"[bold green]✓[/bold green] Using environment file: {found_env_file}")
        else:
            logger("[bold yellow]⚠ Warning:[/bold yellow] No .env file found")
            if not typer.confirm("Continue without environment file?"):
                raise typer.Exit()

        # Check port availability
        if not _check_port_available(port):
            logger(f"[bold red]✗ Port {port} is already in use[/bold red]")
            raise typer.Exit(code=1)
        else:
            logger(f"[bold green]✓[/bold green] Port {port} is available")

        # Check if container already exists
        if _container_exists(container_name):
            if force:
                logger(f"[bold yellow]Removing existing container: {container_name}[/bold yellow]")
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            else:
                logger(f"[bold red]✗ Container '{container_name}' already exists[/bold red]")
                logger("Use --force to remove existing container or choose a different name with --name")
                raise typer.Exit(code=1)

        # Pull image if requested or if image doesn't exist locally
        should_pull = pull
        if not should_pull:
            # Check if image exists locally
            try:
                result = subprocess.run(["docker", "image", "inspect", image_name], capture_output=True, text=True)
                if result.returncode != 0:
                    logger(f"[bold blue]Image not found locally, pulling: {image_name}[/bold blue]")
                    should_pull = True
            except Exception:
                should_pull = True

        if should_pull:
            if not _pull_image(image_name):
                logger(f"[bold red]✗ Failed to pull image: {image_name}[/bold red]")
                raise typer.Exit(code=1)

        # Build Docker command
        cmd = [
            "docker",
            "run",
            "--name",
            container_name,
            "-v",
            f"{os.path.abspath(project_path)}:/app/project",
            "-p",
            f"{port}:8000",
        ]

        if detach:
            cmd.append("-d")
        else:
            cmd.extend(["-it"])

        cmd.append("--rm")

        if found_env_file:
            cmd.extend(["--env-file", found_env_file])

        cmd.append(image_name)

        # Run container
        logger(f"[bold blue]→ Starting container '{container_name}'...[/bold blue]")
        try:
            result = subprocess.run(cmd, capture_output=detach, text=True)
            if result.returncode == 0:
                if detach:
                    logger("[bold green]✓ Container started successfully![/bold green]")

                    # Create info panel
                    info_table = Table.grid(padding=(0, 2))
                    info_table.add_column(style="bold cyan")
                    info_table.add_column()

                    info_table.add_row("API Server:", f"http://localhost:{port}")
                    info_table.add_row("Health Check:", f"http://localhost:{port}/health")
                    info_table.add_row("API Docs:", f"http://localhost:{port}/api-docs")
                    info_table.add_row("Container:", container_name)

                    panel = Panel(info_table, title="🚀 Aurite Container Running", border_style="green")
                    console.print(panel)

                    logger("\n[bold cyan]Management commands:[/bold cyan]")
                    logger(f"  View logs: [bold]aurite docker logs --name {container_name}[/bold]")
                    logger(f"  Stop container: [bold]aurite docker stop --name {container_name}[/bold]")
                    logger(f"  Open shell: [bold]aurite docker shell --name {container_name}[/bold]")
            else:
                logger("[bold red]✗ Failed to start container[/bold red]")
                if result.stderr:
                    logger(f"Error: {result.stderr}")
                raise typer.Exit(code=1)
        except KeyboardInterrupt:
            logger("\n[bold yellow]Container startup interrupted[/bold yellow]")
            raise typer.Exit() from None

    elif action == "stop":
        logger(f"[bold yellow]Stopping container: {container_name}[/bold yellow]")
        result = subprocess.run(["docker", "stop", container_name], capture_output=True, text=True)
        if result.returncode == 0:
            logger("[bold green]✓ Container stopped successfully[/bold green]")
        else:
            logger(f"[bold red]✗ Failed to stop container: {result.stderr}[/bold red]")
            raise typer.Exit(code=1)

    elif action == "logs":
        logger(f"[bold blue]Showing logs for container: {container_name}[/bold blue]")
        try:
            subprocess.run(["docker", "logs", "-f", container_name])
        except KeyboardInterrupt:
            logger("\n[bold yellow]Log viewing interrupted[/bold yellow]")

    elif action == "shell":
        logger(f"[bold blue]Opening shell in container: {container_name}[/bold blue]")
        try:
            subprocess.run(["docker", "exec", "-it", container_name, "/bin/bash"])
        except subprocess.CalledProcessError:
            # Try with sh if bash is not available
            subprocess.run(["docker", "exec", "-it", container_name, "/bin/sh"])

    elif action == "status":
        status = _get_container_status(container_name)

        status_table = Table.grid(padding=(0, 2))
        status_table.add_column(style="bold cyan")
        status_table.add_column()

        status_table.add_row("Container:", container_name)
        status_table.add_row("Status:", status)

        if "Up" in status:
            status_table.add_row("Health:", f"http://localhost:{port}/health")
            panel_style = "green"
            title = "🟢 Container Status"
        elif status == "not found":
            panel_style = "red"
            title = "🔴 Container Status"
        else:
            panel_style = "yellow"
            title = "🟡 Container Status"

        panel = Panel(status_table, title=title, border_style=panel_style)
        console.print(panel)

    elif action == "pull":
        if not _pull_image(image_name):
            logger(f"[bold red]✗ Failed to pull image: {image_name}[/bold red]")
            raise typer.Exit(code=1)
        else:
            logger(f"[bold green]✓ Successfully pulled: {image_name}[/bold green]")

    elif action == "init":
        # Initialize Docker files without building
        logger("[bold green]📝 Initializing Docker files for Aurite project...[/bold green]")

        # Validate project directory
        if not _validate_project_directory(project_path):
            logger(f"[bold yellow]⚠ Warning:[/bold yellow] No .aurite file found in {project_path}")
            if not typer.confirm("Continue anyway?"):
                raise typer.Exit()
        else:
            logger(f"[bold green]✓[/bold green] Found Aurite project at {project_path}")

        # Load templates from docker_templates directory
        templates_dir = files("aurite.bin.cli.docker_templates")

        # Load Dockerfile template and substitute version_tag
        dockerfile_template = (templates_dir / "Dockerfile.aurite.template").read_text()
        dockerfile_content = dockerfile_template.replace("version_tag=latest", f"version_tag={version_tag}")

        # Load .dockerignore template
        dockerignore_content = (templates_dir / "dockerignore.template").read_text()

        dockerfile_path = Path(project_path) / "Dockerfile.aurite"
        dockerignore_path = Path(project_path) / ".dockerignore"

        # Check if files exist and handle accordingly
        dockerfile_exists = dockerfile_path.exists()
        dockerignore_exists = dockerignore_path.exists()

        # Track if any files were created/modified
        files_created = False

        # Handle Dockerfile.aurite
        if dockerfile_exists and not regenerate:
            logger("[bold yellow]Dockerfile.aurite already exists[/bold yellow]")
            logger("  To regenerate, use --regenerate flag")
        else:
            if dockerfile_exists and regenerate:
                logger("[bold yellow]Regenerating Dockerfile.aurite (existing file will be overwritten)[/bold yellow]")

            # Write Dockerfile
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile_content)

            logger("[bold green]✓ Created Dockerfile.aurite[/bold green]")
            logger("  [cyan]This file has been saved for your customization.[/cyan]")
            logger("  [cyan]Edit the USER CUSTOMIZATION SECTION to add dependencies.[/cyan]")
            files_created = True

        # Handle .dockerignore
        if dockerignore_exists and not regenerate:
            logger("[bold yellow].dockerignore already exists[/bold yellow]")
        else:
            if dockerignore_exists and regenerate:
                # Backup existing .dockerignore before overwriting
                dockerignore_backup_path = Path(project_path) / ".dockerignore.backup"
                dockerignore_path.rename(dockerignore_backup_path)
                logger("[bold yellow]Backed up existing .dockerignore to .dockerignore.backup[/bold yellow]")

            # Write .dockerignore
            with open(dockerignore_path, "w") as f:
                f.write(dockerignore_content)

            logger("[bold green]✓ Created .dockerignore[/bold green]")
            files_created = True

        # Show summary and next steps
        if files_created:
            logger("\n[bold cyan]Docker files initialized successfully![/bold cyan]")
            logger("\n[bold]Next steps:[/bold]")
            logger("  1. Review and customize [bold]Dockerfile.aurite[/bold]")
            logger("  2. Add any custom dependencies in the USER CUSTOMIZATION SECTION")
            logger("  3. Run [bold]aurite docker build[/bold] to build your image")
        else:
            logger("\n[bold yellow]All Docker files already exist.[/bold yellow]")
            logger("Use [bold]--regenerate[/bold] flag to overwrite with fresh templates.")

    elif action == "build":
        # Build custom image with project embedded
        logger("[bold green]🔨 Building custom Aurite image with project embedded...[/bold green]")

        # Validate project directory
        if not _validate_project_directory(project_path):
            logger(f"[bold red]✗ No .aurite file found in {project_path}[/bold red]")
            logger("Please run this command from an Aurite project directory.")
            raise typer.Exit(code=1)
        else:
            logger(f"[bold green]✓[/bold green] Found Aurite project at {project_path}")

        # Determine build tag
        if not build_tag:
            project_name = Path(project_path).resolve().name
            build_tag = f"{project_name.lower()}:latest"
            logger(f"[bold blue]Using auto-generated tag: {build_tag}[/bold blue]")

        # Handle custom Dockerfile or auto-generated one
        if dockerfile:
            # Use custom Dockerfile path
            dockerfile_path = Path(dockerfile)
            if not dockerfile_path.exists():
                logger(f"[bold red]✗ Custom Dockerfile not found: {dockerfile}[/bold red]")
                raise typer.Exit(code=1)
            logger(f"[bold blue]Using custom Dockerfile: {dockerfile}[/bold blue]")

            # Still handle .dockerignore
            dockerignore_path = Path(project_path) / ".dockerignore"
            dockerignore_exists = dockerignore_path.exists()

            if not dockerignore_exists:
                # Load .dockerignore template
                templates_dir = files("aurite.bin.cli.docker_templates")
                dockerignore_content = (templates_dir / "dockerignore.template").read_text()

                # Write .dockerignore
                with open(dockerignore_path, "w") as f:
                    f.write(dockerignore_content)
                logger("[bold green]✓ Created .dockerignore[/bold green]")
            else:
                logger("[bold blue]Using existing .dockerignore[/bold blue]")
        else:
            # Use auto-generated Dockerfile.aurite
            # Load templates from docker_templates directory
            templates_dir = files("aurite.bin.cli.docker_templates")

            # Load Dockerfile template and substitute version_tag
            dockerfile_template = (templates_dir / "Dockerfile.aurite.template").read_text()
            dockerfile_content = dockerfile_template.replace("version_tag=latest", f"version_tag={version_tag}")

            # Load .dockerignore template
            dockerignore_content = (templates_dir / "dockerignore.template").read_text()

            dockerfile_path = Path(project_path) / "Dockerfile.aurite"
            dockerignore_path = Path(project_path) / ".dockerignore"

            # Check if files exist and handle accordingly
            dockerfile_exists = dockerfile_path.exists()
            dockerignore_exists = dockerignore_path.exists()

            # Handle Dockerfile.aurite
            if dockerfile_exists and not regenerate:
                logger("[bold blue]Using existing Dockerfile.aurite[/bold blue]")
                logger("  To regenerate, use --regenerate flag")
            else:
                if dockerfile_exists and regenerate:
                    logger(
                        "[bold yellow]Regenerating Dockerfile.aurite (existing file will be overwritten)[/bold yellow]"
                    )

                # Write Dockerfile
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)

                logger("[bold green]✓ Created Dockerfile.aurite[/bold green]")
                logger("  [cyan]This file has been saved for your customization.[/cyan]")
                logger("  [cyan]Edit the USER CUSTOMIZATION SECTION to add dependencies.[/cyan]")

            # Handle .dockerignore
            if dockerignore_exists and not regenerate:
                logger("[bold blue]Using existing .dockerignore[/bold blue]")
            else:
                if dockerignore_exists and regenerate:
                    # Backup existing .dockerignore before overwriting
                    dockerignore_backup_path = Path(project_path) / ".dockerignore.backup"
                    dockerignore_path.rename(dockerignore_backup_path)
                    logger("[bold yellow]Backed up existing .dockerignore to .dockerignore.backup[/bold yellow]")

                # Write .dockerignore
                with open(dockerignore_path, "w") as f:
                    f.write(dockerignore_content)

                logger("[bold green]✓ Created .dockerignore[/bold green]")

        # For build action, continue with the build process
        try:
            # Pull base image first
            logger(f"[bold blue]Ensuring base image is available: {image_name}[/bold blue]")
            if not _pull_image(image_name):
                logger(f"[bold red]✗ Failed to pull base image: {image_name}[/bold red]")
                raise typer.Exit(code=1)

            # Build the image (Docker automatically uses .dockerignore)
            build_cmd = ["docker", "build", "-f", str(dockerfile_path), "-t", build_tag, project_path]

            logger(f"[bold blue]Building image: {build_tag}[/bold blue]")
            result = subprocess.run(build_cmd, capture_output=False, text=True)

            if result.returncode == 0:
                logger(f"[bold green]✓ Successfully built image: {build_tag}[/bold green]")

                # Show build summary
                build_table = Table.grid(padding=(0, 2))
                build_table.add_column(style="bold cyan")
                build_table.add_column()

                build_table.add_row("Built Image:", build_tag)
                build_table.add_row("Base Image:", image_name)
                build_table.add_row("Project Path:", project_path)

                panel = Panel(build_table, title="🔨 Build Complete", border_style="green")
                console.print(panel)

                # Push if requested
                if push_after_build:
                    logger(f"[bold blue]Pushing image to registry: {build_tag}[/bold blue]")
                    push_result = subprocess.run(["docker", "push", build_tag], capture_output=True, text=True)
                    if push_result.returncode == 0:
                        logger(f"[bold green]✓ Successfully pushed: {build_tag}[/bold green]")
                    else:
                        logger(f"[bold red]✗ Failed to push image: {push_result.stderr}[/bold red]")

                logger("\n[bold cyan]Usage examples:[/bold cyan]")
                logger(f"  Run your custom image: [bold]docker run -p 8000:8000 --env-file .env {build_tag}[/bold]")
                logger(f"  Push to registry: [bold]docker push {build_tag}[/bold]")

                # Provide guidance on customization
                if not dockerfile_exists or regenerate:
                    logger("\n[bold cyan]Customization:[/bold cyan]")
                    logger("  Edit [bold]Dockerfile.aurite[/bold] to add custom dependencies")
                    logger("  Then run [bold]aurite docker build[/bold] again to rebuild with changes")

            else:
                logger("[bold red]✗ Failed to build image[/bold red]")
                raise typer.Exit(code=1)

        except Exception as e:
            logger(f"[bold red]✗ Build failed: {e}[/bold red]")
            raise typer.Exit(code=1) from e

    else:
        logger(f"[bold red]Unknown action: {action}[/bold red]")
        logger("Available actions: run, stop, logs, shell, status, pull, build, init")
        raise typer.Exit(code=1)
