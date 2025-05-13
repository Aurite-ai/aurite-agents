"""
API routes for managing projects (loading, creating, viewing, editing, etc.).
"""

import logging
import json  # For loading/dumping JSON
from pathlib import Path
from typing import List, Optional, Any, Dict  # Added Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError  # Added ValidationError

# Import dependencies (adjust relative paths as needed)
from ...dependencies import get_api_key, get_host_manager
from ....host_manager import HostManager
from ....config.config_models import ProjectConfig  # For response model and validation
from ....config import PROJECT_ROOT_DIR  # For constructing paths

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
    manager: HostManager = Depends(get_host_manager),
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
    elif project_component_type == "simple_workflows":
        component_dict_attribute_name = "simple_workflows"
    elif project_component_type == "custom_workflows":
        component_dict_attribute_name = "custom_workflows"
    elif project_component_type == "llm_configs":
        component_dict_attribute_name = "llms"  # Corrected attribute name
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


@router.post("/change", status_code=status.HTTP_200_OK)
async def change_project(
    request: ChangeProjectRequest,
    manager: HostManager = Depends(get_host_manager),
):
    """
    Unloads the current project and loads a new one specified by the path.
    """
    logger.info(f"Received request to change project to: {request.project_config_path}")
    try:
        # Convert string path to Path object. Assume it might be relative to project root.
        # HostManager's change_project method should handle final resolution if needed.
        # For robustness, let's resolve it here relative to PROJECT_ROOT if not absolute.
        from src.config import PROJECT_ROOT_DIR  # Corrected import path

        new_path = Path(request.project_config_path)
        if not new_path.is_absolute():
            new_path = (PROJECT_ROOT_DIR / new_path).resolve()
            logger.debug(f"Resolved relative path to: {new_path}")

        if not new_path.is_file():
            logger.error(f"Project config file not found at resolved path: {new_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project configuration file not found: {new_path}",
            )

        await manager.change_project(new_path)
        active_project = manager.project_manager.get_active_project_config()
        project_name_for_response = active_project.name if active_project else "Unknown"
        return {
            "status": "success",
            "message": f"Successfully changed project to {project_name_for_response}",
            "current_project_path": str(manager.config_path),
        }
    except FileNotFoundError as e:
        logger.error(f"Project file not found during change_project: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project configuration file not found: {str(e)}",
        )
    except (RuntimeError, ValueError) as e:
        # Catch errors from HostManager's unload/initialize process
        logger.error(f"Error changing project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change project: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error changing project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.post(
    "/create_file", response_model=ProjectConfig, status_code=status.HTTP_201_CREATED
)
async def create_project_file(
    request: CreateProjectFileRequest,
    manager: HostManager = Depends(get_host_manager),
):
    """
    Creates a new project JSON file with minimal content (name and description).
    The file will be created in the 'config/projects/' directory.
    """
    logger.info(f"Request to create project file: {request.filename}")
    if not request.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must end with .json.",
        )

    project_file_path = PROJECT_ROOT_DIR / "config" / "projects" / request.filename

    try:
        created_project_config = manager.project_manager.create_project_file(
            project_name=request.project_name,
            project_file_path=project_file_path,
            project_description=request.project_description,
            client_configs=[],  # Minimal project
            llm_configs=[],
            agent_configs=[],
            simple_workflow_configs=[],
            custom_workflow_configs=[],
            overwrite=False,  # Do not overwrite by default for POST
        )
        return created_project_config
    except FileExistsError:
        logger.warning(f"Project file {project_file_path} already exists.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project file {project_file_path} already exists. Use a different filename or update if applicable.",
        )
    except (
        TypeError,
        ValueError,
    ) as e:  # Catches Pydantic validation errors from create_project_file
        logger.error(f"Invalid data for creating project file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data for project file: {str(e)}",
        )
    except IOError as e:
        logger.error(
            f"Failed to write project file {project_file_path}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write project file: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error creating project file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.post("/load_components", status_code=status.HTTP_200_OK)
async def load_components_from_project_file(
    request: LoadComponentsRequest,
    manager: HostManager = Depends(get_host_manager),
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
        # HostManager's load_components_from_project handles path resolution
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
    # No HostManager needed here, can directly access filesystem
):
    """
    Lists all project JSON files in the 'config/projects/' directory.
    """
    logger.info("Request to list project files.")
    projects_dir = PROJECT_ROOT_DIR / "config" / "projects"
    if not projects_dir.is_dir():
        logger.warning(f"Projects directory not found: {projects_dir}")
        return []  # Return empty list if directory doesn't exist

    try:
        project_files = [
            f.name
            for f in projects_dir.iterdir()
            if f.is_file() and f.name.endswith(".json")
        ]
        logger.info(f"Found {len(project_files)} project files.")
        return project_files
    except Exception as e:
        logger.error(f"Error listing project files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list project files: {str(e)}",
        )


# --- Project File Content Endpoints (View & Edit) ---
@router.get("/get_active_project_config", response_model=ProjectConfig)
async def get_active_project_config(
    manager: HostManager = Depends(get_host_manager),
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
    if not filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must end with .json.",
        )

    projects_dir = PROJECT_ROOT_DIR / "config" / "projects"
    file_path = (projects_dir / filename).resolve()

    # Security check: ensure the path is within the projects directory
    if not str(file_path).startswith(str(projects_dir.resolve())):
        logger.error(
            f"Path traversal attempt or invalid filename for project file: {filename}. Resolved to {file_path}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project filename or path.",
        )

    if not file_path.is_file():
        logger.warning(f"Project file not found: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project file '{filename}' not found.",
        )

    try:
        with open(file_path, "r") as f:
            content = json.load(f)
        return content
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in project file {file_path}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project file '{filename}' contains invalid JSON.",
        )
    except Exception as e:
        logger.error(f"Error reading project file {file_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read project file: {str(e)}",
        )


class ProjectFileContent(BaseModel):
    content: Dict[str, Any]


@router.put("/file/{filename:path}", status_code=status.HTTP_200_OK)
async def update_project_file_content(
    filename: str,
    body: ProjectFileContent,
    manager: HostManager = Depends(get_host_manager),  # Added HostManager dependency
):
    """Updates the content of a specific project file."""
    logger.info(f"Request to update content of project file: {filename}")
    if not filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must end with .json.",
        )

    projects_dir = PROJECT_ROOT_DIR / "config" / "projects"
    file_path = (projects_dir / filename).resolve()

    if not str(file_path).startswith(str(projects_dir.resolve())):
        logger.error(
            f"Path traversal attempt or invalid filename for project file update: {filename}. Resolved to {file_path}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project filename or path.",
        )

    if not isinstance(body.content, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project file content must be a JSON object.",
        )

    try:
        # Validate the content by attempting to parse and resolve it using ProjectManager
        # This leverages the same logic as loading a project, ensuring all references and structures are valid.
        # _parse_and_resolve_project_data will raise ValueError or RuntimeError on failure.
        manager.project_manager._parse_and_resolve_project_data(body.content, filename)
        logger.debug(
            f"Project file content for {filename} validated successfully by ProjectManager's parsing logic."
        )
    except (
        ValueError,
        RuntimeError,
        ValidationError,
    ) as e:  # Catch errors from _parse_and_resolve_project_data or Pydantic
        logger.error(
            f"Validation failed for project file {filename} via ProjectManager parsing: {e}",
            exc_info=True,
        )
        # Provide a more generic error or try to extract useful info from 'e'
        error_detail = str(e)
        if isinstance(e, ValidationError):
            error_detail = f"Invalid project configuration structure: {e.errors()}"

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_detail,
        )
    except Exception as e:  # Catch any other unexpected error during validation
        logger.error(
            f"Unexpected error during validation of project file {filename} via ProjectManager: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during content validation: {str(e)}",
        )

    # If validation passed, proceed to save the original raw content to the file
    try:
        # Ensure the directory exists
        projects_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(body.content, f, indent=2)  # Save with pretty print
        logger.info(f"Successfully updated project file: {file_path}")
        return {
            "status": "success",
            "filename": filename,
            "message": "Project file updated successfully.",
        }
    except IOError as e:
        logger.error(f"Failed to write project file {file_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write project file: {str(e)}",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error updating project file {file_path}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )
