"""
API routes for managing projects (loading, creating, etc.).
"""

import logging
from pathlib import Path
from typing import List, Optional  # Added for list_files and optional description

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

# Import dependencies (adjust relative paths as needed)
from ...dependencies import get_api_key, get_host_manager
from ....host_manager import HostManager
from ....config.config_models import ProjectConfig  # For response model
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


# TODO: Add /new_project endpoint in Step 3.3 (This comment seems outdated based on current plan)


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
