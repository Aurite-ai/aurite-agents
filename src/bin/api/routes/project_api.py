"""
API routes for managing projects (loading, creating, etc.).
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

# Import dependencies (adjust relative paths as needed)
from ...dependencies import get_api_key, get_host_manager
from ....host_manager import HostManager

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


# TODO: Add /new_project endpoint in Step 3.3
