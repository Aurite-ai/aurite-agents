from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import logging
import json
from host import MCPHost
from host.config import HostConfig, ClientConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Global MCPHost instance
mcp_host: MCPHost = None

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

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event to initialize the MCPHost.
    """
    global mcp_host
    logger.info("Starting FastAPI server...")

@app.on_event("shutdown")
async def shutdown_event():
    """
    FastAPI shutdown event to clean up the MCPHost.
    """
    global mcp_host
    if mcp_host:
        logger.info("Shutting down MCPHost...")
        await mcp_host.shutdown()

@app.post("/initialize")
async def initialize_host(request: InitializeRequest):
    """
    Endpoint to initialize the MCPHost with a given configuration.
    """
    global mcp_host
    if mcp_host:
        raise HTTPException(status_code=400, detail="MCPHost is already initialized")

    try:
        # Load configuration from JSON file
        with open(request.config_path, "r") as f:
            config_data = json.load(f)

        # Parse agents into ClientConfigs
        client_configs = []
        for agent in config_data["agents"]:
            client_config = ClientConfig(
                client_id=agent["client_id"],
                server_path=agent["server_path"],
                roots=agent["roots"],
                capabilities=agent["capabilities"],
                timeout=agent["timeout"],
                routing_weight=agent["routing_weight"]
            )
            client_configs.append(client_config)

        # Initialize HostConfig with ClientConfigs
        config = HostConfig(clients=client_configs)

        # Initialize MCPHost
        mcp_host = MCPHost(config=config, encryption_key=request.encryption_key)
        await mcp_host.initialize()
        # Register workflows from configuration
        for workflow in config_data.get("workflows", []):
            try:
                # Dynamically import the workflow class
                module_path, class_name = workflow["path"].replace("/", ".").rsplit(".", 1)
                workflow_module = __import__(module_path, fromlist=[class_name])
                workflow_class = getattr(workflow_module, workflow["class"])

                # Register the workflow with the host
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
    """
    Endpoint to check the status of the MCPHost.
    """
    global mcp_host
    if not mcp_host:
        return {"status": "not_initialized"}
    return {"status": "initialized"}

@app.post("/prepare_prompt")
async def prepare_prompt(request: PreparePromptRequest):
    """
    Endpoint to prepare a prompt with associated tools.
    """
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
    """
    Endpoint to execute a prompt with associated tools.
    """
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
    """
    Endpoint to register a workflow with the MCPHost.
    """
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
    """
    Endpoint to execute a registered workflow.
    """
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