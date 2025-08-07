"""
Main orchestration logic for the Aurite Studio command.

This module handles starting both the API server and React frontend
concurrently with unified logging and graceful shutdown.
"""

import asyncio
import logging
import os
import platform
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..api.api import start as start_api_server
from .utils import (
    build_frontend_packages,
    check_build_artifacts,
    check_frontend_dependencies,
    check_port_availability,
    check_system_dependencies,
    get_server_config_for_studio,
    handle_build_failure,
    install_frontend_dependencies,
    is_api_server_running,
    is_port_in_use_by_other_service,
    rebuild_fresh_frontend,
    validate_frontend_structure,
)

logger = logging.getLogger(__name__)
console = Console()

# Global variables for process management
api_process: Optional[asyncio.subprocess.Process] = None
frontend_process: Optional[asyncio.subprocess.Process] = None
shutdown_event = asyncio.Event()


async def start_studio(rebuild_fresh: bool = False):
    """
    Main entry point for the aurite studio command.
    
    This function orchestrates the entire studio startup process:
    1. Validates system dependencies and frontend structure
    2. Prepares frontend (dependencies and builds)
    3. Starts API server if not already running
    4. Starts React development server
    5. Manages concurrent execution with graceful shutdown
    
    Args:
        rebuild_fresh: If True, performs a fresh rebuild of frontend packages
    """
    console.print(Panel.fit(
        "[bold blue]Aurite Studio[/bold blue]\n"
        "Starting integrated development environment...",
        border_style="blue"
    ))
    
    # Phase 1: System validation
    console.print("\n[bold yellow]Phase 1:[/bold yellow] Validating system requirements...")
    
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
    frontend_task = asyncio.create_task(start_frontend_server_process(frontend_port))
    tasks.append(frontend_task)
    
    # Add shutdown monitoring task
    shutdown_task = asyncio.create_task(monitor_shutdown())
    tasks.append(shutdown_task)
    
    # Display startup success message
    console.print(Panel.fit(
        f"[bold green]🚀 Aurite Studio is running![/bold green]\n\n"
        f"[bold]API Server:[/bold] http://localhost:{api_port}\n"
        f"[bold]Studio UI:[/bold] http://localhost:{frontend_port}\n\n"
        f"[dim]Press Ctrl+C to stop both servers[/dim]",
        border_style="green",
        title="Ready"
    ))
    
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
            result = subprocess.run([
                "taskkill", "/F", "/T", "/PID", str(frontend_process.pid)
            ], check=False, capture_output=True, text=True)
            
            # Also kill any npm processes by name as backup
            subprocess.run([
                "taskkill", "/F", "/IM", "npm.cmd"
            ], check=False, capture_output=True)
            
            subprocess.run([
                "taskkill", "/F", "/IM", "node.exe"
            ], check=False, capture_output=True)
            
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
                if hasattr(frontend_process, '_transport') and frontend_process._transport:
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
                if hasattr(api_process, '_transport') and api_process._transport:
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
    Start the API server as a subprocess.
    
    Args:
        port: Port for the API server
    """
    global api_process
    
    try:
        # Start API server using the existing start function in a subprocess
        # We'll use the CLI command to ensure proper environment setup
        api_process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", "from aurite.bin.api.api import start; start()",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=os.environ.copy()
        )
        
        # Stream API server output with prefix
        async for line in api_process.stdout:
            line_str = line.decode().strip()
            if line_str:
                console.print(f"[dim][API][/dim] {line_str}")
        
        await api_process.wait()
        
    except Exception as e:
        logger.error(f"API server process error: {e}", exc_info=True)
        console.print(f"[bold red][API] Error:[/bold red] {str(e)}")


async def start_frontend_server_process(port: int):
    """
    Start the React frontend development server.
    
    Args:
        port: Port for the frontend server (should be 3000)
    """
    global frontend_process
    
    frontend_dir = Path.cwd() / "frontend"
    
    # On Windows, we need shell=True for subprocess calls
    is_windows = platform.system() == "Windows"
    
    try:
        # Start React development server
        if is_windows:
            # On Windows, use shell=True and pass command as string
            frontend_process = await asyncio.create_subprocess_shell(
                "npm run start",
                cwd=frontend_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={
                    **os.environ, 
                    # "BROWSER": "none",  # Prevent auto-opening browser
                    "PORT": "3000"      # Explicitly set React dev server port
                }
            )
        else:
            # On Unix systems, use exec
            frontend_process = await asyncio.create_subprocess_exec(
                "npm", "run", "start",
                cwd=frontend_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={
                    **os.environ, 
                    # "BROWSER": "none",  # Prevent auto-opening browser
                    "PORT": "3000"      # Explicitly set React dev server port
                }
            )
        
        # Stream frontend output with prefix
        async for line in frontend_process.stdout:
            line_str = line.decode().strip()
            if line_str:
                # Filter out some verbose webpack output
                if not any(skip in line_str.lower() for skip in ["compiled successfully", "webpack compiled"]):
                    console.print(f"[dim][STUDIO][/dim] {line_str}")
        
        await frontend_process.wait()
        
    except Exception as e:
        logger.error(f"Frontend server process error: {e}", exc_info=True)
        console.print(f"[bold red][STUDIO] Error:[/bold red] {str(e)}")


def setup_signal_handlers():
    """
    Setup signal handlers for graceful shutdown.
    """
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        shutdown_event.set()
        # On Windows, we need to be more aggressive about stopping processes
        if platform.system() == "Windows":
            asyncio.create_task(force_cleanup_on_signal())
    
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
                subprocess.run([
                    "taskkill", "/F", "/T", "/PID", str(frontend_process.pid)
                ], check=False, capture_output=True)
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
                        subprocess.run([
                            "taskkill", "/F", "/T", "/PID", str(process.pid)
                        ], check=False, capture_output=True)
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
                    if hasattr(process, 'stdout') and process.stdout:
                        process.stdout.close()
                    if hasattr(process, 'stderr') and process.stderr:
                        process.stderr.close()
                    if hasattr(process, 'stdin') and process.stdin:
                        process.stdin.close()
                except Exception as e:
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
                asyncio.gather(*[process.wait() for _, process in processes_to_cleanup]),
                timeout=10.0
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
