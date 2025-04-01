from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json

from src.host.host import MCPHost
from src.host.config import HostConfig, ClientConfig, RootConfig
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

# Global MCPHost instance
mcp_host: MCPHost = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle FastAPI lifecycle events (startup and shutdown processes)."""
    global mcp_host
    try:
        logger.info("Starting FastAPI server...")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        if mcp_host:
            logger.info("Shutting down MCPHost...")
            await mcp_host.shutdown()
        logger.info("FastAPI server shutdown complete.")


# Create FastAPI app
app = FastAPI(
    title="Aurite MCP",
    description="API for managing MCPHost and workflows",
    version="1.0.0",
    lifespan=lifespan,
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    """Log all HTTP requests."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)

    logger.info(
        f"[{request.method}] {request.url.path} - Status: {response.status_code} - "
        f"Duration: {duration:.3f}s - Client: {client_ip} - "
        f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
    )

    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request models
class InitializeRequest(BaseModel):
    config_path: str
    encryption_key: str = None


class PreparePromptRequest(BaseModel):
    prompt_name: str
    prompt_arguments: Dict[str, Any]
    client_id: str
    tool_names: Optional[List[str]] = None


class ExecutePromptRequest(BaseModel):
    prompt_name: str
    prompt_arguments: Dict[str, Any]
    client_id: str
    user_message: str
    tool_names: Optional[List[str]] = None
    model: str = "claude-3-opus-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7
    anthropic_api_key: Optional[str] = None


class RegisterWorkflowRequest(BaseModel):
    workflow_class: str
    name: Optional[str] = None
    kwargs: Dict[str, Any] = {}


class ExecuteWorkflowRequest(BaseModel):
    workflow_name: str
    input_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


@app.post("/initialize")
async def initialize_host(request: InitializeRequest):
    """Endpoint to initialize the MCPHost with a given configuration."""
    global mcp_host
    if mcp_host:
        raise HTTPException(status_code=400, detail="MCPHost is already initialized")

    try:
        with open(request.config_path, "r") as f:
            config_data = json.load(f)

        client_configs = [
            ClientConfig(
                client_id=agent["client_id"],
                server_path=Path(agent["server_path"]),
                roots=[
                    RootConfig(
                        uri=root["uri"],
                        name=root["name"],
                        capabilities=root["capabilities"],
                    )
                    for root in agent["roots"]
                ],
                capabilities=agent["capabilities"],
                timeout=agent.get("timeout", 10.0),
                routing_weight=agent.get("routing_weight", 1.0),
            )
            for agent in config_data["agents"]
        ]

        config = HostConfig(clients=client_configs)
        mcp_host = MCPHost(config=config, encryption_key=request.encryption_key)
        await mcp_host.initialize()

        for workflow in config_data.get("workflows", []):
            try:
                module_path, class_name = workflow["path"].replace("/", ".").rsplit(".", 1)
                workflow_module = __import__(module_path, fromlist=[class_name])
                workflow_class = getattr(workflow_module, class_name)
                await mcp_host.register_workflow(
                    workflow_class=workflow_class,
                    name=workflow.get("name"),
                    **workflow.get("args", {}),
                )
                logger.info(f"Registered workflow: {workflow.get('name') or workflow['class']}")
            except Exception as e:
                logger.error(f"Failed to register workflow {workflow.get('name') or workflow['class']}: {e}")
                raise

        return {"message": "MCPHost initialized successfully"}
    except Exception as e:
        logger.error(f"Failed to initialize MCPHost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Endpoint to check the status of the MCPHost."""
    global mcp_host
    return {"status": "initialized" if mcp_host else "not_initialized"}


@app.post("/prepare_prompt")
async def prepare_prompt(request: PreparePromptRequest):
    """Endpoint to prepare a prompt with associated tools."""
    global mcp_host
    if not mcp_host:
        raise HTTPException(status_code=400, detail="MCPHost is not initialized")

    try:
        result = await mcp_host.prepare_prompt_with_tools(
            prompt_name=request.prompt_name,
            prompt_arguments=request.prompt_arguments,
            client_id=request.client_id,
            tool_names=request.tool_names,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to prepare prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute_prompt")
async def execute_prompt(request: ExecutePromptRequest):
    """Endpoint to execute a prompt with associated tools."""
    global mcp_host
    if not mcp_host:
        raise HTTPException(status_code=400, detail="MCPHost is not initialized")

    try:
        result = await mcp_host.execute_prompt_with_tools(
            prompt_name=request.prompt_name,
            prompt_arguments=request.prompt_arguments,
            client_id=request.client_id,
            user_message=request.user_message,
            tool_names=request.tool_names,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            anthropic_api_key=request.anthropic_api_key,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to execute prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/register_workflow")
async def register_workflow(request: RegisterWorkflowRequest):
    """Endpoint to register a workflow with the MCPHost."""
    global mcp_host
    if not mcp_host:
        raise HTTPException(status_code=400, detail="MCPHost is not initialized")

    try:
        workflow_name = await mcp_host.register_workflow(
            workflow_class=request.workflow_class,
            name=request.name,
            **request.kwargs,
        )
        return {"workflow_name": workflow_name}
    except Exception as e:
        logger.error(f"Failed to register workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute_workflow")
async def execute_workflow(request: ExecuteWorkflowRequest):
    """Endpoint to execute a registered workflow."""
    global mcp_host
    if not mcp_host:
        raise HTTPException(status_code=400, detail="MCPHost is not initialized")

    try:
        result = await mcp_host.execute_workflow(
            workflow_name=request.workflow_name,
            input_data=request.input_data,
            metadata=request.metadata,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def start():
    """Start the FastAPI application with uvicorn."""
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        log_level="info",
    )


if __name__ == "__main__":
    start()