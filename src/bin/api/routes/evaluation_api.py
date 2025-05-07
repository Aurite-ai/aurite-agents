import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.config import PROJECT_ROOT_DIR
# Import shared dependencies (relative to parent of routes)
from ...dependencies import get_api_key, get_host_manager
from ....host_manager import HostManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/evaluation",
    tags=["Evaluation Management"],  # Tag for OpenAPI docs
    dependencies=[Depends(get_api_key)],  # Apply auth to all routes in this router
)


# --- Request/Response Models ---

class ExecuteCustomWorkflowResponse(BaseModel):
    workflow_name: str
    status: str  # e.g., "completed", "failed"
    result: Optional[Any] = None  # Allow flexible output
    error: Optional[str] = None

class PromptValidationFileRequest(BaseModel):
    config_file: str
    
class PromptValidationSimpleRequest(BaseModel):
    agent_name: str
    user_input: str
    testing_prompt: str

# --- Execution Endpoints ---

@router.post(
    "/prompt_validation/file",
    response_model=ExecuteCustomWorkflowResponse,
)
async def execute_prompt_validation_file(
    request_body: PromptValidationFileRequest,
    manager: HostManager = Depends(get_host_manager),
):
    """Executes the prompt validation workflow from a config file."""
    logger.info("Received request to execute prompt validation workflow")
    result = await manager.execution.run_custom_workflow(
        workflow_name="Prompt Validation Workflow",
        initial_input={"config_path": PROJECT_ROOT_DIR / f"config/testing/{request_body.config_file}"},
    )
    logger.info("Prompt Validation Workflow executed successfully via manager.")
    if isinstance(result, dict) and result.get("status") == "failed":
        logger.error(
            f"Prompt Validation Workflow execution failed (reported by facade): {result.get('error')}"
        )
        return ExecuteCustomWorkflowResponse(
            workflow_name="Prompt Validation Workflow",
            status="failed",
            error=result.get("error", "Unknown execution error"),
        )
    else:
        return ExecuteCustomWorkflowResponse(
            workflow_name="Prompt Validation Workflow", status="completed", result=result
        )
        
@router.post(
    "/prompt_validation/simple",
    response_model=ExecuteCustomWorkflowResponse,
)
async def execute_prompt_validation_simple(
    request_body: PromptValidationSimpleRequest,
    manager: HostManager = Depends(get_host_manager),
):
    """Executes the prompt validation workflow with simplified input."""
    logger.info("Received request to execute prompt validation workflow")
    result = await manager.execution.run_custom_workflow(
        workflow_name="Prompt Validation Workflow",
        initial_input={
            "agent_name": request_body.agent_name, 
            "user_input": request_body.user_input,
            "testing_prompt": request_body.testing_prompt,
        },
    )
    logger.info("Prompt Validation Workflow executed successfully via manager.")
    if isinstance(result, dict) and result.get("status") == "failed":
        logger.error(
            f"Prompt Validation Workflow execution failed (reported by facade): {result.get('error')}"
        )
        return ExecuteCustomWorkflowResponse(
            workflow_name="Prompt Validation Workflow",
            status="failed",
            error=result.get("error", "Unknown execution error"),
        )
    else:
        return ExecuteCustomWorkflowResponse(
            workflow_name="Prompt Validation Workflow", status="completed", result=result
        )
