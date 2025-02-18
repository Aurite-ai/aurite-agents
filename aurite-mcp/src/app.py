from __future__ import annotations

from collections.abc import Callable
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.routes import chat_router


logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
)


# Create FastAPI app
app = FastAPI(
    title="MCP Agent Server",
    description="API for MCP Agents",
    version="1.0.0",
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    """Log all HTTP requests."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Get client IP, handling proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_for.split(",")[0] if forwarded_for else request.client.host

    # Log the request details
    logger.info(
        f"[{request.method}] {request.url.path} - Status: {response.status_code} - " f"Duration: {duration:.3f}s - Client: {client_ip} - " f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
    )

    return response


# Add CORS middleware with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # FastAPI backend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
logger.info("Mounting chat router")
app.include_router(chat_router.router)

# Log all available routes for debugging
for route in app.routes:
    logger.info(f"Registered route: {route.path} [{','.join(route.methods)}]")


def start():
    """Start the FastAPI application with uvicorn."""
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8080,
        workers=1,
        log_level="info",
    )


if __name__ == "__main__":
    start()
