from __future__ import annotations

from dotenv import load_dotenv  # Add this import
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Callable, Optional  # Added List

from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse  # Add JSONResponse

# Adjust imports for new location (src/bin -> src)
from ...host_manager import (
    Aurite,
)  # Corrected relative import (up two levels from src/bin/api)

# Ensure host models are imported correctly (up two levels from src/bin/api)
# Import the new routers (relative to current file's directory)
from .routes import (
    config_routes,
    components_routes,
    evaluation_api,  # evaluation_api is not being renamed as per plan
    project_routes,
)

# Import shared dependencies (relative to parent directory - src/bin)
from ..dependencies import (  # Corrected relative import (up one level from src/bin/api)
    PROJECT_ROOT,
    get_api_key,
    get_host_manager,
    get_server_config,  # Re-import ServerConfig if needed locally, or remove if only used in dependencies.py
)


# Removed CustomWorkflowManager import

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file at the very beginning
load_dotenv()  # Add this call


# --- Configuration Dependency, Security Dependency, Aurite Dependency (Moved to dependencies.py) ---


# --- FastAPI Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle FastAPI lifecycle events: initialize Aurite on startup, shutdown on exit."""
    manager_instance: Optional[Aurite] = None
    try:
        logger.info("Starting FastAPI server and initializing Aurite...")
        # Load server config
        server_config = get_server_config()
        if not server_config:
            raise RuntimeError(
                "Server configuration could not be loaded. Aborting startup."
            )

        # Instantiate Aurite
        # Ensure Aurite path is correct relative to project root if needed
        # Assuming Aurite itself handles path resolution correctly based on CWD or PROJECT_ROOT
        manager_instance = Aurite(config_path=server_config.PROJECT_CONFIG_PATH)

        # Initialize Aurite (loads configs, initializes MCPHost)
        await manager_instance.initialize()
        logger.debug("Aurite initialized successfully.")

        # Store manager instance in app state
        app.state.host_manager = manager_instance

        yield  # Server runs here

    except Exception as e:
        logger.error(
            f"Error during Aurite initialization or server startup: {e}",
            exc_info=True,
        )
        # Ensure manager (and its host) is cleaned up if initialization partially succeeded
        if manager_instance:
            try:
                await manager_instance.shutdown()
            except Exception as shutdown_e:
                logger.error(
                    f"Error during manager shutdown after startup failure: {shutdown_e}"
                )
        raise  # Re-raise the original exception to prevent server from starting improperly
    finally:
        # Shutdown Aurite on application exit
        final_manager_instance = getattr(app.state, "host_manager", None)
        if final_manager_instance:
            logger.info("Shutting down Aurite...")
            try:
                await final_manager_instance.shutdown()
                logger.debug("Aurite shutdown complete.")
            except Exception as e:
                logger.error(f"Error during Aurite shutdown: {e}")
        else:
            logger.info("Aurite was not initialized or already shut down.")

        # Clear manager from state
        if hasattr(app.state, "host_manager"):
            del app.state.host_manager
        logger.info("FastAPI server shutdown sequence complete.")


# Create FastAPI app
app = FastAPI(
    title="Aurite MCP",
    description="API for managing MCPHost and workflows",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Health Check Endpoint ---
# Define simple routes directly on app first
@app.get("/health", status_code=200)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


# --- Application Endpoints ---
@app.get("/status")
async def get_status(
    # Use Security instead of Depends for the API key
    api_key: str = Security(get_api_key),
    manager: Aurite = Depends(get_host_manager),
):
    """Endpoint to check the status of the Aurite and its underlying MCPHost."""
    # The get_host_manager dependency ensures the manager and host are initialized
    # We can add more detailed status checks later if needed (e.g., check manager.host)
    return {"status": "initialized", "manager_status": "active"}


# Include the routers
app.include_router(config_routes.router)
app.include_router(components_routes.router)
app.include_router(evaluation_api.router)  # evaluation_api is not being renamed
app.include_router(project_routes.router)

# --- Custom Exception Handlers ---
# Define handlers before endpoints that might raise these exceptions


# Handler for KeyErrors (typically indicates resource not found)
@app.exception_handler(KeyError)
async def key_error_exception_handler(request: Request, exc: KeyError):
    logger.warning(
        f"Resource not found (KeyError): {exc} for request {request.url.path}"
    )
    # Extract the key name if possible from the exception args
    detail = f"Resource not found: {str(exc)}"
    return JSONResponse(
        status_code=404,
        content={"detail": detail},
    )


# Handler for ValueErrors (can indicate bad input, conflicts, or bad state)
@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    detail = f"Invalid request or state: {str(exc)}"
    status_code = 400  # Default to Bad Request

    # Check for specific error messages to set more specific status codes
    exc_str = str(exc).lower()
    if "already registered" in exc_str:
        status_code = 409  # Conflict
        logger.warning(
            f"Conflict during registration: {exc} for request {request.url.path}"
        )
    elif "Aurite is not initialized" in exc_str:
        status_code = 503  # Service Unavailable
        logger.error(
            f"Service unavailable (Aurite not init): {exc} for request {request.url.path}"
        )
    elif "not found for agent" in exc_str or "not found for workflow" in exc_str:
        status_code = (
            400  # Bad request because config references non-existent component
        )
        logger.warning(
            f"Configuration error (invalid reference): {exc} for request {request.url.path}"
        )
    else:
        logger.warning(f"ValueError encountered: {exc} for request {request.url.path}")

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


# Handler for FileNotFoundError (e.g., custom workflow module, client server path)
@app.exception_handler(FileNotFoundError)
async def file_not_found_error_handler(request: Request, exc: FileNotFoundError):
    logger.error(f"Required file not found: {exc} for request {request.url.path}")
    return JSONResponse(
        status_code=404,  # Treat as Not Found, could argue 500 if it's internal config
        content={"detail": f"Required file not found: {str(exc)}"},
    )


# Handler for setup/import errors related to custom workflows
@app.exception_handler(AttributeError)
@app.exception_handler(ImportError)
@app.exception_handler(PermissionError)
@app.exception_handler(TypeError)
async def custom_workflow_setup_error_handler(request: Request, exc: Exception):
    # Check if the request path involves custom_workflows to be more specific
    # This is a basic check; more robust checking might involve inspecting the exception origin
    is_custom_workflow_path = "/custom_workflows/" in request.url.path
    error_type = type(exc).__name__

    if is_custom_workflow_path:
        logger.error(
            f"Error setting up custom workflow ({error_type}): {exc} for request {request.url.path}",
            exc_info=True,
        )
        detail = f"Error setting up custom workflow: {error_type}: {str(exc)}"
        status_code = 500  # Internal server error during setup
    else:
        # If it's not a custom workflow path, treat as a generic internal error
        logger.error(
            f"Internal server error ({error_type}): {exc} for request {request.url.path}",
            exc_info=True,
        )
        detail = f"Internal server error: {error_type}: {str(exc)}"
        status_code = 500

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


# Handler for RuntimeErrors (e.g., during custom workflow execution, config loading)
@app.exception_handler(RuntimeError)
async def runtime_error_exception_handler(request: Request, exc: RuntimeError):
    logger.error(
        f"Runtime error encountered: {exc} for request {request.url.path}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,  # Internal Server Error
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# Generic fallback handler for any other exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc} for request {request.url.path}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"An unexpected internal server error occurred: {type(exc).__name__}"
        },
    )


# --- Removed old static file serving ---
# app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")
# @app.get("/")
# async def serve_index():
#     return FileResponse(PROJECT_ROOT / "static" / "index.html")
# --- End of removal ---

# --- Serve React Frontend Build ---
# Mount the assets directory generated by Vite build
if not (PROJECT_ROOT / "frontend/dist/assets").is_dir():
    logger.warn(
        "Frontend build assets directory not found. Ensure the frontend is built correctly."
    )
else:
    logger.info(
        f"Serving frontend assets from: {PROJECT_ROOT / 'frontend/dist/assets'}"
    )
    app.mount(
        "/assets",
        StaticFiles(directory=PROJECT_ROOT / "frontend/dist/assets"),
        name="frontend-assets",
    )

# --- Config File CRUD Endpoints (Moved to routes/config_api.py) ---


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    """Log all HTTP requests."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    client_ip = request.headers.get(
        "X-Forwarded-For", request.client.host if request.client else "Unknown"
    )

    logger.info(
        f"[{request.method}] {request.url.path} - Status: {response.status_code} - "
        f"Duration: {duration:.3f}s - Client: {client_ip} - "
        f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
    )

    return response


# Add CORS middleware
# Origins are loaded from ServerConfig
server_config_for_cors = get_server_config()
if server_config_for_cors is None:
    raise RuntimeError("Server configuration not found, cannot configure CORS.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config_for_cors.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health Check Endpoint (Moved earlier) ---


# Catch-all route to serve index.html for client-side routing
# IMPORTANT: This must come AFTER all other API routes
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_react_app(full_path: str):  # Parameter name doesn't matter much here
    # Check if the requested path looks like a file extension common in frontend builds
    # This is a basic check to avoid serving index.html for potential API-like paths
    # that weren't explicitly defined. Adjust extensions as needed.
    if "." in full_path and full_path.split(".")[-1] in [
        "js",
        "css",
        "html",
        "ico",
        "png",
        "jpg",
        "svg",
        "woff2",
        "woff",
        "ttf",
    ]:
        # If it looks like a file request that wasn't caught by /assets mount, return 404
        # This prevents serving index.html for potentially missing asset files.
        # Alternatively, you could try serving from PROJECT_ROOT / "frontend/dist" / full_path
        # but the /assets mount should handle most cases.
        raise HTTPException(status_code=404, detail="Static file not found in assets")

    # For all other paths, serve the main index.html file
    index_path = PROJECT_ROOT / "frontend/dist/index.html"
    if not index_path.is_file():
        logger.error(f"Frontend build index.html not found at: {index_path}")
        raise HTTPException(status_code=500, detail="Frontend build not found.")
    return FileResponse(index_path)


# --- End Serve React Frontend Build ---


def start():
    """Start the FastAPI application with uvicorn, using loaded configuration."""
    # Load config to get server settings
    # Note: This runs get_server_config() again, but @lru_cache makes it fast
    config = get_server_config()

    if config:
        logger.info(
            f"Starting Uvicorn server on {config.HOST}:{config.PORT} with {config.WORKERS} worker(s)..."
        )

        # IF ENV = "development", set reload=True
        # This is typically set in the environment or config file
        reload_mode = (
            os.getenv("ENV") != "production"
        )  # Default to True if not in production

        # Update the app path for uvicorn to point to the new location
        uvicorn.run(
            "aurite.bin.api.api:app",  # Updated path
            host=config.HOST,
            port=config.PORT,
            workers=config.WORKERS,
            log_level=config.LOG_LEVEL.lower(),  # Uvicorn expects lowercase log level
            reload=reload_mode,  # Typically False for production/running directly
        )
    else:
        logger.critical("Server configuration could not be loaded. Aborting startup.")
        raise RuntimeError(
            "Server configuration could not be loaded. Aborting startup."
        )


if __name__ == "__main__":
    start()
