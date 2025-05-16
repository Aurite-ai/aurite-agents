"""
API routes for managing projects (loading, creating, viewing, editing, etc.).
"""

import logging
from pathlib import Path
from typing import List, Optional, Any, Dict  # Added Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field  # Added ValidationError

# Import dependencies (adjust relative paths as needed)
from ...dependencies import get_api_key, get_host_manager
from ....host_manager import Aurite
from ....config.config_models import ProjectConfig  # For response model and validation

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["Project Management"],
    dependencies=[Depends(get_api_key)],
)


# --- Request Models ---


class ChangeProjectRequest(BaseModel):
    """Request model for changing the active project."""

    project_config_path: str = Field(
        ...,
        description="Absolute path or path relative to project root for the project config JSON file.",
        examples=[
            "/path/to/your/project/config/projects/my_project.json",
            "config/projects/default.json",
        ],
    )


class CreateProjectFileRequest(BaseModel):
    """Request model for creating a new project file."""

    filename: str = Field(
        ...,
        description="Filename for the new project (e.g., 'my_new_project.json'). Must end with .json.",
        examples=["my_new_project.json"],
    )
    project_name: str = Field(
        ...,
        description="The name of the project.",
        examples=["My New Awesome Project"],
    )
    project_description: Optional[str] = Field(
        None,
        description="Optional description for the project.",
        examples=["A project to do awesome things."],
    )


class LoadComponentsRequest(BaseModel):
    """Request model for loading components from a project file."""

    project_config_path: str = Field(
        ...,
        description="Path relative to project root for the project config JSON file to load components from.",
        examples=["config/projects/another_project.json"],
    )


# --- Endpoints ---


@router.get(
    "/active/component/{project_component_type}/{component_name}", response_model=Any
)
async def get_active_project_component_config(
    project_component_type: str,
    component_name: str,
    manager: Aurite = Depends(get_host_manager),
):
    """
    Retrieves the full configuration of a specific component
    from the currently active project configuration.
    """
    logger.info(
        f"Request to get component '{component_name}' of type '{project_component_type}' from active project."
    )
    active_project = manager.project_manager.get_active_project_config()

    if not active_project:
        logger.warning("No active project loaded.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active project loaded.",
        )

    # Determine the correct attribute on the active_project object
    # These should match the keys in your ProjectConfig Pydantic model
    # (e.g., active_project.agents, active_project.simple_workflows)
    # The frontend will pass "agents", "simple_workflows", "custom_workflows", "llm_configs"

    component_dict_attribute_name: Optional[str] = None
    if project_component_type == "agents":
        component_dict_attribute_name = (
            "agents"  # Assuming ProjectConfig has active_project.agents
        )
    elif project_component_type == "simple_workflows": # this code made more sense when the names were different I'll refactor at some point
        component_dict_attribute_name = "simple_workflows"
    elif project_component_type == "custom_workflows":
        component_dict_attribute_name = "custom_workflows"
    elif project_component_type == "llms":
        component_dict_attribute_name = "llms"
    elif project_component_type == "clients":
        component_dict_attribute_name = "clients"
    else:
        logger.warning(
            f"Invalid project_component_type specified in path: {project_component_type}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component type '{project_component_type}' for active project lookup.",
        )

    if not hasattr(active_project, component_dict_attribute_name):
        logger.error(
            f"Active project config object does not have attribute '{component_dict_attribute_name}' for type '{project_component_type}'."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server configuration error for project component type '{project_component_type}'.",
        )

    component_config_dict: Optional[Dict[str, Any]] = getattr(
        active_project, component_dict_attribute_name
    )

    if component_config_dict is None or component_name not in component_config_dict:
        logger.warning(
            f"Component '{component_name}' of type '{project_component_type}' (attr: {component_dict_attribute_name}) not found in active project."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component '{component_name}' of type '{project_component_type}' not found in active project.",
        )

    component_config = component_config_dict[component_name]
    logger.info(
        f"Successfully retrieved component '{component_name}' of type '{project_component_type}' from active project."
    )
    # component_config is already a Pydantic model instance (e.g., WorkflowConfig).
    # FastAPI will automatically call .model_dump() for the response.
    return component_config


# @router.post("/change", status_code=status.HTTP_200_OK)
# async def change_project(
#     request: ChangeProjectRequest,
#     manager: Aurite = Depends(get_host_manager),
# ):
#     """
#     Unloads the current project and loads a new one specified by the path.
#     """
#     logger.info(f"Received request to change project to: {request.project_config_path}")
#     try:
#         # Convert string path to Path object. Assume it might be relative to project root.
#         # Aurite's change_project method should handle final resolution if needed.
#         # For robustness, let's resolve it here relative to PROJECT_ROOT if not absolute.
#         from aurite.config import PROJECT_ROOT_DIR  # Corrected import path

#         new_path = Path(request.project_config_path)
#         if not new_path.is_absolute():
#             new_path = (PROJECT_ROOT_DIR / new_path).resolve()
#             logger.debug(f"Resolved relative path to: {new_path}")

#         if not new_path.is_file():
#             logger.error(f"Project config file not found at resolved path: {new_path}")
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Project configuration file not found: {new_path}",
#             )

#         await manager.change_project(new_path)
#         active_project = manager.project_manager.get_active_project_config()
#         project_name_for_response = active_project.name if active_project else "Unknown"
#         return {
#             "status": "success",
#             "message": f"Successfully changed project to {project_name_for_response}",
#             "current_project_path": str(manager.config_path),
#         }
#     except FileNotFoundError as e:
#         logger.error(f"Project file not found during change_project: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Project configuration file not found: {str(e)}",
#         )
#     except (RuntimeError, ValueError) as e:
#         # Catch errors from Aurite's unload/initialize process
#         logger.error(f"Error changing project: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to change project: {str(e)}",
#         )
#     except Exception as e:
#         logger.error(f"Unexpected error changing project: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An unexpected error occurred: {str(e)}",
#         )


@router.post(
    "/create_file", response_model=ProjectConfig, status_code=status.HTTP_201_CREATED
)
async def create_project_file(
    request: CreateProjectFileRequest,
    manager: Aurite = Depends(get_host_manager),
):
    """
    Creates a new project JSON file with minimal content (name and description).
    The file will be created in the 'config/projects/' directory.
    """
    logger.info(f"Request to create project file: {request.filename}")
    # This endpoint is temporarily disabled due to PROJECT_ROOT_DIR removal.
    # It needs refactoring to use current_project_root from ProjectManager for path construction.
    logger.warning(
        f"The POST /projects/create_file endpoint ({request.filename}) is temporarily non-functional "
        "and requires refactoring for the new path resolution model."
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint /projects/create_file temporarily unavailable, requires path refactoring.",
    )


@router.post("/load_components", status_code=status.HTTP_200_OK)
async def load_components_from_project_file(
    request: LoadComponentsRequest,
    manager: Aurite = Depends(get_host_manager),
):
    """
    Loads components from a specified project file into the active configuration.
    If no project is active, initializes the system with this project.
    Otherwise, components are added additively to the current project.
    """
    logger.info(
        f"Request to load components from project file: {request.project_config_path}"
    )
    try:
        # Aurite's load_components_from_project handles path resolution
        # relative to PROJECT_ROOT_DIR if the path is not absolute.
        await manager.load_components_from_project(Path(request.project_config_path))
        active_project_config = manager.project_manager.get_active_project_config()
        project_name = (
            active_project_config.name if active_project_config else "Unknown"
        )
        return {
            "status": "success",
            "message": f"Components from '{request.project_config_path}' loaded into project '{project_name}'.",
            "active_project_name": project_name,
        }
    except FileNotFoundError as e:
        logger.error(f"Project file not found for loading components: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project configuration file not found: {str(e)}",
        )
    except (RuntimeError, ValueError) as e:
        logger.error(f"Error loading components from project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,  # Or 500 depending on error nature
            detail=f"Failed to load components: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error loading components: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.get("/list_files", response_model=List[str])
async def list_project_files(
    # No Aurite needed here, can directly access filesystem
):
    """
    Lists all project JSON files in the 'config/projects/' directory.
    """
    logger.info("Request to list project files.")
    # This endpoint is temporarily disabled due to PROJECT_ROOT_DIR removal.
    # It needs refactoring for path construction using current_project_root.
    logger.warning(
        "The GET /projects/list_files endpoint is temporarily non-functional "
        "and requires refactoring for the new path resolution model."
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint /projects/list_files temporarily unavailable, requires path refactoring.",
    )


# --- Project File Content Endpoints (View & Edit) ---
@router.get("/get_active_project_config", response_model=ProjectConfig)
async def get_active_project_config(
    manager: Aurite = Depends(get_host_manager),
):
    """
    Retrieves the currently active project configuration.
    """
    logger.info("Request to get active project configuration.")
    active_project = manager.project_manager.get_active_project_config()

    if not active_project:
        logger.warning("No active project loaded.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active project loaded.",
        )

    return active_project

@router.get("/file/{filename:path}", response_model=Any)
async def get_project_file_content(filename: str):
    """Retrieves the raw JSON content of a specific project file."""
    logger.info(f"Request to get content of project file: {filename}")
    # This endpoint is temporarily disabled due to PROJECT_ROOT_DIR removal.
    # It needs refactoring for path construction using current_project_root.
    logger.warning(
        f"The GET /projects/file/{filename} endpoint is temporarily non-functional "
        "and requires refactoring for the new path resolution model."
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Endpoint /projects/file/{filename} temporarily unavailable, requires path refactoring.",
    )


class ProjectFileContent(BaseModel):
    content: Dict[str, Any]


@router.put("/file/{filename:path}", status_code=status.HTTP_200_OK)
async def update_project_file_content(
    filename: str,
    body: ProjectFileContent,
    manager: Aurite = Depends(get_host_manager),  # Added Aurite dependency
):
    """Updates the content of a specific project file."""
    logger.info(f"Request to update content of project file: {filename}")
    # This endpoint is temporarily disabled due to PROJECT_ROOT_DIR removal.
    # It needs refactoring for path construction using current_project_root.
    logger.warning(
        f"The PUT /projects/file/{filename} endpoint is temporarily non-functional "
        "and requires refactoring for the new path resolution model."
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Endpoint /projects/file/{filename} (update) temporarily unavailable, requires path refactoring.",
    )
