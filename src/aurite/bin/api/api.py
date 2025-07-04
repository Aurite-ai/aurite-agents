from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Callable  # Added List

import uvicorn
from dotenv import load_dotenv  # Add this import
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse  # Add JSONResponse

# Adjust imports for new location (src/bin -> src)
from ...host_manager import (  # Corrected relative import (up two levels from src/bin/api)
    Aurite,
)
from ...errors import (
    ConfigurationError,
    AgentExecutionError,
    WorkflowExecutionError,
)

# Import shared dependencies (relative to parent directory - src/bin)
from ..dependencies import (
    get_server_config,  # Re-import ServerConfig if needed locally, or remove if only used in dependencies.py
)

# Ensure host models are imported correctly (up two levels from src/bin/api)
# Import the new routers (relative to current file's directory)
from .routes import mcp_host_routes, config_manager_routes, facade_routes

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
    logger.info("Initializing Aurite for FastAPI application...")
    aurite_instance = Aurite()
    # The __aenter__ will trigger the lazy initialization.
    await aurite_instance.__aenter__()
    app.state.aurite_instance = aurite_instance
    logger.info("Aurite initialized and ready.")

    yield  # Server runs here

    logger.info("Shutting down Aurite...")
    # The __aexit__ will handle the graceful shutdown.
    await aurite_instance.__aexit__(None, None, None)
    logger.info("Aurite shutdown complete.")


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
# All application endpoints are now defined in their respective router files.


# Include the new routers
app.include_router(mcp_host_routes.router, prefix="/host", tags=["MCP Host"])
app.include_router(
    config_manager_routes.router, prefix="/config", tags=["Configuration Manager"]
)
app.include_router(facade_routes.router, prefix="/execution", tags=["Execution Facade"])


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema, optionally loading from external file."""
    if app.openapi_schema:
        return app.openapi_schema

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
app.openapi = custom_openapi  # type: ignore[no-redef]


# --- Custom Exception Handlers ---
# Define handlers before endpoints that might raise these exceptions


# Handler for ConfigurationErrors
@app.exception_handler(ConfigurationError)
async def configuration_error_exception_handler(
    request: Request, exc: ConfigurationError
):
    logger.warning(f"Configuration error: {exc} for request {request.url.path}")
    return JSONResponse(
        status_code=404,  # Not Found, as the requested resource config is missing
        content={"detail": str(exc)},
    )


# Handler for AgentExecutionErrors
@app.exception_handler(AgentExecutionError)
async def agent_execution_error_exception_handler(
    request: Request, exc: AgentExecutionError
):
    logger.error(
        f"Agent execution error: {exc} for request {request.url.path}", exc_info=True
    )
    return JSONResponse(
        status_code=500,  # Internal Server Error
        content={"detail": f"Agent execution failed: {str(exc)}"},
    )


# Handler for WorkflowExecutionErrors
@app.exception_handler(WorkflowExecutionError)
async def workflow_execution_error_exception_handler(
    request: Request, exc: WorkflowExecutionError
):
    logger.error(
        f"Workflow execution error: {exc} for request {request.url.path}", exc_info=True
    )
    return JSONResponse(
        status_code=500,  # Internal Server Error
        content={"detail": f"Workflow execution failed: {str(exc)}"},
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
    # This is a placeholder for serving a frontend.
    # For now, it will return a 404 for any path not matching an API route.
    raise HTTPException(status_code=404, detail="Not Found")


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
