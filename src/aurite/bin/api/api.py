from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Callable, Optional  # Added List

import uvicorn
import yaml
from dotenv import load_dotenv  # Add this import
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse  # Add JSONResponse
from fastapi.staticfiles import StaticFiles

# Adjust imports for new location (src/bin -> src)
from ...host_manager import (  # Corrected relative import (up two levels from src/bin/api)
    Aurite,
)

# Import shared dependencies (relative to parent directory - src/bin)
from ..dependencies import (
    get_server_config,  # Re-import ServerConfig if needed locally, or remove if only used in dependencies.py
)
from ..dependencies import (  # Corrected relative import (up one level from src/bin/api)
    PROJECT_ROOT,
    get_api_key,
    get_host_manager,
)

# Ensure host models are imported correctly (up two levels from src/bin/api)
# Import the new routers (relative to current file's directory)
from .routes import evaluation_api  # evaluation_api is not being renamed as per plan
from .routes import components_routes, config_routes, project_routes

# Removed CustomWorkflowManager import
# Hello
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
    title="Aurite Agents API",
    description="API for the Aurite Agents framework - a Python framework for building AI agents using the Model Context Protocol (MCP)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api-docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc UI
    openapi_url="/openapi.json",  # OpenAPI schema endpoint
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


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema, optionally loading from external file."""
    if app.openapi_schema:
        return app.openapi_schema

    # Try to load the detailed OpenAPI spec from file
    openapi_file = PROJECT_ROOT / "openapi.yaml"
    if openapi_file.exists():
        try:
            with open(openapi_file, "r") as f:
                openapi_schema = yaml.safe_load(f)
            logger.info(f"Loaded OpenAPI schema from {openapi_file}")

            # Update server URL based on current configuration
            server_config = get_server_config()
            if server_config:
                openapi_schema["servers"] = [
                    {
                        "url": f"http://{server_config.HOST}:{server_config.PORT}",
                        "description": "Current server",
                    }
                ]

            app.openapi_schema = openapi_schema
            return app.openapi_schema
        except Exception as e:
            logger.warning(f"Failed to load OpenAPI schema from file: {e}")

    # Fallback to auto-generated schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Let FastAPI auto-detect security from Security() dependencies
    # Testing if newer FastAPI versions can detect nested Security dependencies
    logger.info(
        "Using auto-generated OpenAPI schema with FastAPI's built-in security detection"
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Override the OpenAPI schema function
app.openapi = custom_openapi


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
    """
    Start the FastAPI application with uvicorn.
    In development, this function will re-exec uvicorn with --reload.
    In production, it runs the server directly.
    """
    # Load config to get server settings
    config = get_server_config()
    if not config:
        logger.critical("Server configuration could not be loaded. Aborting startup.")
        raise RuntimeError(
            "Server configuration could not be loaded. Aborting startup."
        )

    # Determine reload mode based on environment. Default to development mode.
    reload_mode = os.getenv("ENV", "development").lower() != "production"

    # In development (reload mode), it's more stable to hand off execution directly
    # to the uvicorn CLI. This avoids issues with the reloader in a programmatic context.
    if reload_mode:
        logger.info(
            f"Development mode detected. Starting Uvicorn with reload enabled on {config.HOST}:{config.PORT}..."
        )
        # Use os.execvp to replace the current process with uvicorn.
        # This is the recommended way to run with --reload from a script.
        args = [
            "uvicorn",
            "aurite.bin.api.api:app",
            "--host",
            config.HOST,
            "--port",
            str(config.PORT),
            "--log-level",
            config.LOG_LEVEL.lower(),
            "--reload",
        ]
        os.execvp("uvicorn", args)
    else:
        # In production, run uvicorn programmatically without the reloader.
        # This is suitable for running with multiple workers.
        logger.info(
            f"Production mode detected. Starting Uvicorn on {config.HOST}:{config.PORT} with {config.WORKERS} worker(s)..."
        )
        uvicorn.run(
            "aurite.bin.api.api:app",
            host=config.HOST,
            port=config.PORT,
            workers=config.WORKERS,
            log_level=config.LOG_LEVEL.lower(),
            reload=False,
        )


if __name__ == "__main__":
    start()
