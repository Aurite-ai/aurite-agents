"""
Main orchestration logic for the Aurite Studio command.

This module handles starting both the API server and React frontend
concurrently with unified logging and graceful shutdown.

Now supports both development mode (React dev server) and production mode (static assets).
"""

import asyncio
import logging
import os
import platform
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

# Removed direct import to avoid circular dependency
# from ..api.api import start as start_api_server
from .static_server import get_static_assets_info, is_static_assets_available
from .utils import (
    build_frontend_packages,
    check_build_artifacts,
    check_frontend_dependencies,
    check_port_availability,
    check_system_dependencies,
    get_server_config_for_studio,
    install_frontend_dependencies,
    is_api_server_running,
    is_port_in_use_by_other_service,
    rebuild_fresh_frontend,
    validate_frontend_structure,
)

logger = logging.getLogger(__name__)
console = Console()


def safe_decode_line(line_bytes: bytes) -> str:
    """
    Safely decode a line of bytes using multiple encoding attempts.

    This function tries multiple encodings to handle cases where subprocess
    output contains special characters (like degree symbols) that may not
    be valid UTF-8.

    Args:
        line_bytes: Raw bytes from subprocess output

    Returns:
        Decoded string, with problematic characters replaced if necessary
    """
    # List of encodings to try, in order of preference
    encodings = ["utf-8", "windows-1252", "latin-1"]

    for encoding in encodings:
        try:
            return line_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    # Final fallback: decode with error replacement
    # This will show � for any problematic characters but won't crash
    try:
        decoded = line_bytes.decode("utf-8", errors="replace")
        logger.debug(f"Used error replacement for line decoding: {repr(line_bytes[:50])}")
        return decoded
    except Exception as e:
        # Absolute last resort - return a safe representation
        logger.warning(f"Complete decoding failure for line: {e}")
        return f"<binary data: {len(line_bytes)} bytes>"


# Global variables for process management
api_process: Optional[asyncio.subprocess.Process] = None
frontend_process: Optional[asyncio.subprocess.Process] = None
shutdown_event = asyncio.Event()


async def start_studio(rebuild_fresh: bool = False):
    """
    Main entry point for the aurite studio command.

    This function orchestrates the entire studio startup process:
    1. Detects if static assets are available (production mode) or development mode
    2. For production mode: starts only API server with static assets
    3. For development mode: validates dependencies, prepares frontend, starts both servers
    4. Manages concurrent execution with graceful shutdown

    Args:
        rebuild_fresh: If True, performs a fresh rebuild of frontend packages
    """
    console.print(
        Panel.fit(
            "[bold blue]Aurite Studio[/bold blue]\nStarting integrated development environment...", border_style="blue"
        )
    )

    # Phase 1: Mode Detection
    console.print("\n[bold yellow]Phase 1:[/bold yellow] Detecting studio mode...")

    # Check if static assets are available (production mode)
    if is_static_assets_available():
        static_info = get_static_assets_info()
        console.print(
            f"[bold green]✓[/bold green] Static assets detected ({static_info['files']} files, {static_info['size_mb']} MB)"
        )
        console.print("[bold blue]Running in PRODUCTION mode[/bold blue] - serving pre-built static assets")
        return await start_studio_production_mode()
    else:
        console.print("[bold yellow]Static assets not found[/bold yellow]")
        console.print("[bold blue]Running in DEVELOPMENT mode[/bold blue] - using React dev server")
        return await start_studio_development_mode(rebuild_fresh)


async def start_studio_production_mode():
    """
    Start Aurite Studio in production mode using static assets.
    Only starts the API server which serves both API and static files.
    """
    console.print("\n[bold yellow]Phase 2:[/bold yellow] Starting production server...")

    # Get server configuration
    server_config = get_server_config_for_studio()
    if not server_config:
        return False

    api_port = server_config.PORT

    # Check if API server is already running
    if is_api_server_running(api_port):
        console.print(f"[bold green]✓[/bold green] API server already running on port {api_port}")
        studio_url = f"http://localhost:{api_port}/studio"
        console.print(
            Panel.fit(
                f"[bold green]🚀 Aurite Studio is running![/bold green]\n\n"
                f"[bold]Studio UI:[/bold] {studio_url}\n"
                f"[bold]API Server:[/bold] http://localhost:{api_port}\n\n"
                f"[dim]Static assets are being served by the API server[/dim]\n"
                f"[dim]Press Ctrl+C to stop[/dim]",
                border_style="green",
                title="Production Mode",
            )
        )

        # Open browser
        try:
            webbrowser.open(studio_url)
            console.print(f"[dim]Opened {studio_url} in your default browser[/dim]")
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")

        # Wait for shutdown signal with immediate response
        setup_signal_handlers()
        try:
            await shutdown_event.wait()
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Received shutdown signal...[/bold yellow]")
        finally:
            # For external API server, we just need to exit cleanly
            console.print("[bold green]Aurite Studio shutdown complete[/bold green]")

        return True

    # Start API server with static assets
    console.print(f"[bold blue]Starting API server with static assets on port {api_port}...[/bold blue]")

    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()

    global api_process

    try:
        # Start API server
        api_task = asyncio.create_task(start_api_server_process(api_port))
        shutdown_task = asyncio.create_task(monitor_shutdown())

        # Wait a moment for server to start, then show success message
        await asyncio.sleep(2)

        studio_url = f"http://localhost:{api_port}/studio"
        console.print(
            Panel.fit(
                f"[bold green]🚀 Aurite Studio is running![/bold green]\n\n"
                f"[bold]Studio UI:[/bold] {studio_url}\n"
                f"[bold]API Server:[/bold] http://localhost:{api_port}\n\n"
                f"[dim]Static assets are being served by the API server[/dim]\n"
                f"[dim]Press Ctrl+C to stop[/dim]",
                border_style="green",
                title="Production Mode",
            )
        )

        # Open browser
        try:
            webbrowser.open(studio_url)
            console.print(f"[dim]Opened {studio_url} in your default browser[/dim]")
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")

        # Wait for shutdown or process completion
        done, pending = await asyncio.wait([api_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED)

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Received shutdown signal...[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error during server execution:[/bold red] {str(e)}")
        logger.error(f"Server execution error: {e}", exc_info=True)
    finally:
        await cleanup_processes()

    console.print("\n[bold green]Aurite Studio shutdown complete[/bold green]")
    return True


async def start_studio_development_mode(rebuild_fresh: bool = False):
    """
    Start Aurite Studio in development mode using React dev server.
    This is the original behavior with full dependency checking and frontend building.
    """
    # Phase 2: System validation
    console.print("\n[bold yellow]Phase 2:[/bold yellow] Validating system requirements...")

    # Check system dependencies
    deps_ok, deps_error = check_system_dependencies()
    if not deps_ok:
        console.print(f"[bold red]✗[/bold red] System dependencies check failed: {deps_error}")
        console.print("\n[bold blue]Installation Instructions:[/bold blue]")
        console.print("1. Install Node.js (>= 18.0.0): https://nodejs.org/")
        console.print("2. npm is included with Node.js")
        console.print("3. Verify installation: [code]node --version && npm --version[/code]")
        return False

    console.print("[bold green]✓[/bold green] Node.js and npm are available")

    # Validate frontend structure
    structure_ok, structure_error = validate_frontend_structure()
    if not structure_ok:
        console.print(f"[bold red]✗[/bold red] Frontend structure validation failed: {structure_error}")
        return False

    console.print("[bold green]✓[/bold green] Frontend structure is valid")

    # Phase 2: Frontend preparation
    console.print("\n[bold yellow]Phase 2:[/bold yellow] Preparing frontend...")

    # Handle fresh rebuild if requested
    if rebuild_fresh:
        console.print("[bold yellow]Fresh rebuild requested...[/bold yellow]")
        if not await rebuild_fresh_frontend():
            console.print("[bold red]✗[/bold red] Failed to perform fresh rebuild")
            return False
    else:
        # Normal preparation flow
        # Check and install frontend dependencies
        if not check_frontend_dependencies():
            console.print("[bold yellow]Frontend dependencies not found, installing...[/bold yellow]")
            if not await install_frontend_dependencies():
                console.print("[bold red]✗[/bold red] Failed to install frontend dependencies")
                return False
        else:
            console.print("[bold green]✓[/bold green] Frontend dependencies are installed")

        # Check and build frontend packages if needed
        if not check_build_artifacts():
            console.print("[bold yellow]Build artifacts not found, building packages...[/bold yellow]")
            if not await build_frontend_packages():
                console.print("[bold red]✗[/bold red] Failed to build frontend packages")
                return False
        else:
            console.print("[bold green]✓[/bold green] Frontend build artifacts are available")

    # Phase 3: Server startup
    console.print("\n[bold yellow]Phase 3:[/bold yellow] Starting servers...")

    # Get server configuration
    server_config = get_server_config_for_studio()
    if not server_config:
        return False

    api_port = server_config.PORT
    frontend_port = 3000

    # Check if API server is already running
    if is_api_server_running(api_port):
        console.print(f"[bold green]✓[/bold green] API server already running on port {api_port}")
        start_api = False
    elif is_port_in_use_by_other_service(api_port):
        console.print(f"[bold red]✗[/bold red] Port {api_port} is in use by another service")
        console.print(f"Please free up port {api_port} or stop the conflicting service")
        console.print("You can check what's using the port with: [code]lsof -i :{api_port}[/code]")
        return False
    else:
        console.print(f"[bold blue]Starting API server on port {api_port}...[/bold blue]")
        start_api = True

    # Check frontend port availability
    if not check_port_availability(frontend_port):
        console.print(f"[bold red]✗[/bold red] Port {frontend_port} is already in use")
        console.print("Please free up port 3000 or stop any running React development servers")
        return False

    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()

    # Start concurrent servers
    try:
        await start_concurrent_servers(start_api, api_port, frontend_port)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Received shutdown signal...[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error during server execution:[/bold red] {str(e)}")
        logger.error(f"Server execution error: {e}", exc_info=True)
    finally:
        await cleanup_processes()

    console.print("\n[bold green]Aurite Studio shutdown complete[/bold green]")
    return True


async def start_concurrent_servers(start_api: bool, api_port: int, frontend_port: int):
    """
    Start API and frontend servers concurrently.

    Args:
        start_api: Whether to start the API server
        api_port: Port for API server
        frontend_port: Port for frontend server
    """
    global api_process, frontend_process

    tasks = []

    # Start API server if needed
    if start_api:
        api_task = asyncio.create_task(start_api_server_process(api_port))
        tasks.append(api_task)

    # Start frontend server
    frontend_task = asyncio.create_task(start_frontend_server_process(frontend_port, api_port))
    tasks.append(frontend_task)

    # Add shutdown monitoring task
    shutdown_task = asyncio.create_task(monitor_shutdown())
    tasks.append(shutdown_task)

    # Display startup success message
    console.print(
        Panel.fit(
            f"[bold green]🚀 Aurite Studio is running![/bold green]\n\n"
            f"[bold]API Server:[/bold] http://localhost:{api_port}\n"
            f"[bold]Studio UI:[/bold] http://localhost:{frontend_port}\n\n"
            f"[dim]Press Ctrl+C to stop both servers[/dim]",
            border_style="green",
            title="Ready",
        )
    )

    # Wait for shutdown signal or process completion
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(f"Error in concurrent server execution: {e}", exc_info=True)
        raise


async def monitor_shutdown():
    """
    Monitor for shutdown event and handle immediate termination on Windows.
    """
    await shutdown_event.wait()

    # Immediate cleanup on Windows
    if platform.system() == "Windows":
        console.print("\n[bold yellow]Shutdown signal received, terminating processes...[/bold yellow]")
        await immediate_windows_cleanup()

    # For Unix systems, let the normal cleanup handle it
    return


async def immediate_windows_cleanup():
    """
    Immediate process termination for Windows to avoid hanging.
    """
    global api_process, frontend_process

    # Kill frontend process immediately using taskkill
    if frontend_process and frontend_process.returncode is None:
        try:
            console.print("[dim]Force terminating frontend server...[/dim]")

            # First try taskkill with process tree termination
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(frontend_process.pid)], check=False, capture_output=True, text=True
            )

            # Also kill any npm processes by name as backup
            subprocess.run(["taskkill", "/F", "/IM", "npm.cmd"], check=False, capture_output=True)

            subprocess.run(["taskkill", "/F", "/IM", "node.exe"], check=False, capture_output=True)

            # Force kill the process directly
            try:
                frontend_process.kill()
            except:
                pass

            # Wait for process to actually terminate
            try:
                await asyncio.wait_for(frontend_process.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

            # Ensure subprocess handles are properly closed
            try:
                if hasattr(frontend_process, "_transport") and frontend_process._transport:
                    frontend_process._transport.close()
            except Exception:
                pass

            console.print("[bold green]✓[/bold green] Frontend server terminated")
        except Exception as e:
            logger.error(f"Error force killing frontend process: {e}")
            try:
                frontend_process.kill()
                await asyncio.sleep(0.1)  # Brief wait for cleanup
            except:
                pass

    # Kill API process
    if api_process and api_process.returncode is None:
        try:
            console.print("[dim]Force terminating API server...[/dim]")
            api_process.kill()

            # Wait for process to actually terminate and close handles
            try:
                await asyncio.wait_for(api_process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass

            # Ensure subprocess handles are properly closed
            try:
                if hasattr(api_process, "_transport") and api_process._transport:
                    api_process._transport.close()
            except Exception:
                pass

            console.print("[bold green]✓[/bold green] API server terminated")
        except Exception as e:
            logger.error(f"Error force killing API process: {e}")

    console.print("[bold green]All servers terminated[/bold green]")

    # Give a moment for all cleanup to complete
    await asyncio.sleep(0.2)


async def start_api_server_process(port: int):
    """
    Start the API server as a subprocess with robust error handling.

    Args:
        port: Port for the API server
    """
    global api_process

    try:
        # Start API server using uvicorn directly to avoid circular imports
        api_process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "uvicorn",
            "aurite.bin.api.api:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--log-level",
            "info",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=os.environ.copy(),
        )

        # Stream API server output with prefix and robust error handling
        try:
            async for line in api_process.stdout:
                try:
                    line_str = safe_decode_line(line).strip()
                    if line_str:
                        console.print(f"[dim][API][/dim] {line_str}")
                except Exception as decode_error:
                    # Log the error but continue processing other lines
                    logger.debug(f"Error decoding API output line: {decode_error}")
                    # Show a safe representation of the problematic line
                    console.print(f"[dim][API][/dim] <output decoding error: {len(line)} bytes>")
                    continue
        except Exception as stream_error:
            logger.error(f"Error streaming API server output: {stream_error}")
            console.print("[bold yellow][API] Warning:[/bold yellow] Output streaming interrupted")

        # Wait for process completion
        await api_process.wait()

    except Exception as e:
        logger.error(f"API server process error: {e}", exc_info=True)
        console.print(f"[bold red][API] Error:[/bold red] {str(e)}")
    finally:
        # Ensure process cleanup
        if api_process and api_process.returncode is None:
            try:
                api_process.terminate()
            except Exception:
                pass


async def start_frontend_server_process(port: int, api_port: int = 8000):
    """
    Start the React frontend development server with robust error handling.

    Args:
        port: Port for the frontend server (should be 3000)
        api_port: Port for the API server (for development mode cross-port communication)
    """
    global frontend_process

    frontend_dir = Path.cwd() / "frontend"

    # On Windows, we need shell=True for subprocess calls
    is_windows = platform.system() == "Windows"

    try:
        # Start React development server
        if is_windows:
            # On Windows, use cmd /c to avoid batch job prompts
            frontend_process = await asyncio.create_subprocess_exec(
                "cmd",
                "/c",
                "npm run start",
                cwd=frontend_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={
                    **os.environ,
                    # "BROWSER": "none",  # Prevent auto-opening browser
                    "PORT": "3000",  # Explicitly set React dev server port
                    "REACT_APP_API_BASE_URL": f"http://localhost:{api_port}",  # Dynamic API port for dev mode
                },
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            # On Unix systems, use exec
            frontend_process = await asyncio.create_subprocess_exec(
                "npm",
                "run",
                "start",
                cwd=frontend_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={
                    **os.environ,
                    # "BROWSER": "none",  # Prevent auto-opening browser
                    "PORT": "3000",  # Explicitly set React dev server port
                    "REACT_APP_API_BASE_URL": f"http://localhost:{api_port}",  # Dynamic API port for dev mode
                },
            )

        # Stream frontend output with prefix and robust error handling
        try:
            async for line in frontend_process.stdout:
                try:
                    line_str = safe_decode_line(line).strip()
                    if line_str:
                        # Filter out some verbose webpack output
                        if not any(skip in line_str.lower() for skip in ["compiled successfully", "webpack compiled"]):
                            console.print(f"[dim][STUDIO][/dim] {line_str}")
                except Exception as decode_error:
                    # Log the error but continue processing other lines
                    logger.debug(f"Error decoding frontend output line: {decode_error}")
                    # Show a safe representation of the problematic line
                    console.print(f"[dim][STUDIO][/dim] <output decoding error: {len(line)} bytes>")
                    continue
        except Exception as stream_error:
            logger.error(f"Error streaming frontend server output: {stream_error}")
            console.print("[bold yellow][STUDIO] Warning:[/bold yellow] Output streaming interrupted")

        # Wait for process completion
        await frontend_process.wait()

    except Exception as e:
        logger.error(f"Frontend server process error: {e}", exc_info=True)
        console.print(f"[bold red][STUDIO] Error:[/bold red] {str(e)}")
    finally:
        # Ensure process cleanup
        if frontend_process and frontend_process.returncode is None:
            try:
                frontend_process.terminate()
            except Exception:
                pass


def setup_signal_handlers():
    """
    Setup signal handlers for graceful shutdown.
    """

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        console.print("\n[bold yellow]Shutting down servers...[/bold yellow]")
        shutdown_event.set()
        # Immediate response - don't wait for cleanup tasks

    # Handle SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def force_cleanup_on_signal():
    """
    Force cleanup when signal is received (Windows-specific).
    """
    global api_process, frontend_process

    # Give a brief moment for normal shutdown to start
    await asyncio.sleep(0.5)

    # If processes are still running, force terminate them
    if frontend_process and frontend_process.returncode is None:
        try:
            if platform.system() == "Windows":
                # Use taskkill immediately on Windows
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(frontend_process.pid)], check=False, capture_output=True
                )
            else:
                frontend_process.kill()
        except Exception as e:
            logger.error(f"Error force killing frontend process: {e}")

    if api_process and api_process.returncode is None:
        try:
            api_process.kill()
        except Exception as e:
            logger.error(f"Error force killing API process: {e}")


async def cleanup_processes():
    """
    Clean up running processes gracefully with Windows-specific handling.
    """
    global api_process, frontend_process

    console.print("[bold yellow]Shutting down servers...[/bold yellow]")

    is_windows = platform.system() == "Windows"

    # Terminate processes
    processes_to_cleanup = []

    if frontend_process and frontend_process.returncode is None:
        processes_to_cleanup.append(("Frontend", frontend_process))

    if api_process and api_process.returncode is None:
        processes_to_cleanup.append(("API", api_process))

    # Handle Windows and Unix differently
    if is_windows:
        await cleanup_processes_windows(processes_to_cleanup)
    else:
        await cleanup_processes_unix(processes_to_cleanup)


async def cleanup_processes_windows(processes_to_cleanup):
    """
    Windows-specific process cleanup using taskkill for process trees.
    """
    for name, process in processes_to_cleanup:
        try:
            if process.returncode is None:
                console.print(f"[dim]Terminating {name} server (Windows)...[/dim]")

                # For Windows, we need to kill the entire process tree
                # because npm creates child processes that don't respond to normal termination
                if name == "Frontend":
                    # Use taskkill to forcefully terminate the npm process tree
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(process.pid)], check=False, capture_output=True
                        )
                        console.print(f"[dim]Used taskkill to terminate {name} process tree[/dim]")
                    except Exception as e:
                        logger.error(f"Error using taskkill for {name}: {e}")
                        # Fallback to normal kill
                        process.kill()
                else:
                    # For API server, normal termination should work
                    process.terminate()

                # Wait briefly for process to exit
                try:
                    await asyncio.wait_for(process.wait(), timeout=3.0)
                    console.print(f"[bold green]✓[/bold green] {name} server terminated")
                except asyncio.TimeoutError:
                    # Force kill if still running
                    try:
                        process.kill()
                        await process.wait()
                        console.print(f"[dim]Force killed {name} server[/dim]")
                    except Exception as e:
                        logger.error(f"Error force killing {name}: {e}")

                # Ensure subprocess handles are properly closed
                try:
                    if hasattr(process, "stdout") and process.stdout:
                        process.stdout.close()
                    if hasattr(process, "stderr") and process.stderr:
                        process.stderr.close()
                    if hasattr(process, "stdin") and process.stdin:
                        process.stdin.close()
                except Exception:
                    # Ignore errors during handle cleanup
                    pass

        except Exception as e:
            logger.error(f"Error terminating {name} process on Windows: {e}")

    console.print("[bold green]✓[/bold green] All servers shut down")

    # Give a moment for all cleanup to complete
    await asyncio.sleep(0.1)


async def cleanup_processes_unix(processes_to_cleanup):
    """
    Unix-specific process cleanup with graceful shutdown.
    """
    # Send SIGTERM to all processes
    for name, process in processes_to_cleanup:
        try:
            process.terminate()
            console.print(f"[dim]Sent shutdown signal to {name} server[/dim]")
        except Exception as e:
            logger.error(f"Error terminating {name} process: {e}")

    # Wait for graceful shutdown with timeout
    if processes_to_cleanup:
        try:
            await asyncio.wait_for(
                asyncio.gather(*[process.wait() for _, process in processes_to_cleanup]), timeout=10.0
            )
            console.print("[bold green]✓[/bold green] All servers shut down gracefully")
        except asyncio.TimeoutError:
            console.print("[bold yellow]Timeout waiting for graceful shutdown, forcing termination...[/bold yellow]")

            # Force kill if graceful shutdown failed
            for name, process in processes_to_cleanup:
                try:
                    if process.returncode is None:
                        process.kill()
                        await process.wait()
                        console.print(f"[dim]Force terminated {name} server[/dim]")
                except Exception as e:
                    logger.error(f"Error force killing {name} process: {e}")
