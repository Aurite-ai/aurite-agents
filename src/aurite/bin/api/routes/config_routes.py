from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Security

from ....lib.config.config_manager import ConfigManager
from ....lib.models import (
    ComponentCreate,
    ComponentCreateResponse,
    ComponentUpdate,
    FileCreateRequest,
    FileUpdateRequest,
    ProjectCreate,
    ProjectInfo,
    ProjectUpdate,
    WorkspaceInfo,
)
from ....lib.models.api.responses import ComponentCreateResponse
from ...dependencies import get_api_key, get_config_manager

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Configuration Manager"])

# Mapping from plural to singular forms for component types
PLURAL_TO_SINGULAR = {
    "agents": "agent",
    "llms": "llm",
    "mcp_servers": "mcp_server",
    "linear_workflows": "linear_workflow",
    "custom_workflows": "custom_workflow",
}


# Component CRUD Operations
@router.get("/components", response_model=List[str])
async def list_component_types(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    List all available component types.
    """
    return list(config_manager.get_all_configs().keys())


@router.get("/components/{component_type}", response_model=List[Dict[str, Any]])
async def list_components_by_type(
    component_type: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    List all available components of a specific type.
    Accepts both singular and plural forms (e.g., 'agent' or 'agents').
    """
    # Convert plural to singular if needed
    singular_type = PLURAL_TO_SINGULAR.get(component_type, component_type)
    return config_manager.list_configs(singular_type)


@router.get("/components/{component_type}/{component_id}", response_model=Dict[str, Any])
async def get_component_by_id(
    component_type: str,
    component_id: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Get a specific component by its type and ID.
    Accepts both singular and plural forms for component type (e.g., 'agent' or 'agents').
    """
    # Convert plural to singular if needed
    singular_type = PLURAL_TO_SINGULAR.get(component_type, component_type)
    config = config_manager.get_config(singular_type, component_id)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Component '{component_id}' of type '{component_type}' not found.",
        )
    return config


@router.post("/components/{component_type}", response_model=ComponentCreateResponse)
async def create_component(
    component_type: str,
    component_data: ComponentCreate,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Create a new component of the specified type.
    """
    # Convert plural to singular if needed
    singular_type = PLURAL_TO_SINGULAR.get(component_type, component_type)

    # Validate component type
    valid_types = list(config_manager.get_all_configs().keys())
    if singular_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid component type '{component_type}'. Valid types are: {', '.join(valid_types)}",
        )

    # Check if component already exists
    existing = config_manager.get_config(singular_type, component_data.name)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Component '{component_data.name}' of type '{component_type}' already exists.",
        )

    # Extract API routing parameters (these should not be saved in the component config)
    project = component_data.config.get("project")
    workspace = component_data.config.get("workspace", False)
    file_path = component_data.config.get("file_path")

    # Prepare the component config without API routing parameters
    component_config = component_data.config.copy()
    # Remove API routing parameters from the component config
    component_config.pop("project", None)
    component_config.pop("workspace", None)
    component_config.pop("file_path", None)

    # Add required fields
    component_config["type"] = singular_type
    component_config["name"] = component_data.name

    # Validate the component configuration before creating it
    is_valid, validation_errors = config_manager._validate_component_config(singular_type, component_config)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"Component configuration validation failed: {'; '.join(validation_errors)}",
        )

    result = config_manager.create_component(
        singular_type,
        component_config,
        project=project,
        workspace=workspace,
        file_path=file_path,
    )

    if not result:
        # Provide more helpful error messages based on context
        try:
            sources = config_manager.list_config_sources()
            [s for s in sources if s["context"] == "project"]

            if len(sources) == 0:
                detail = "No configuration sources found. Please ensure you're in a valid Aurite workspace or project."
            elif not config_manager.workspace_name and not config_manager.project_name:
                detail = "Not in a valid Aurite context. Please run 'aurite init' to set up a workspace or project."
            else:
                detail = f"Failed to create component '{component_data.name}'. Check logs for details."

        except Exception:
            detail = f"Failed to create component '{component_data.name}'."

        raise HTTPException(
            status_code=500,
            detail=detail,
        )

    return result


@router.put("/components/{component_type}/{component_id}", response_model=Dict[str, Any])
async def update_component(
    component_type: str,
    component_id: str,
    component_data: ComponentUpdate,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Update an existing component.
    """
    # Convert plural to singular if needed
    singular_type = PLURAL_TO_SINGULAR.get(component_type, component_type)

    # Check if component exists
    existing = config_manager.get_config(singular_type, component_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Component '{component_id}' of type '{component_type}' not found.",
        )

    # Prepare the full config with name preserved
    full_config = component_data.config.copy()
    full_config["name"] = component_id

    # Use the existing update_component method
    success = config_manager.update_component(singular_type, component_id, full_config)

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update component '{component_id}'.",
        )

    return {"message": f"Component '{component_id}' updated successfully."}


@router.delete("/components/{component_type}/{component_id}", response_model=Dict[str, Any])
async def delete_component(
    component_type: str,
    component_id: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Delete a component.
    """
    # Convert plural to singular if needed
    singular_type = PLURAL_TO_SINGULAR.get(component_type, component_type)

    # Check if component exists
    existing = config_manager.get_config(singular_type, component_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Component '{component_id}' of type '{component_type}' not found.",
        )

    # Use the delete_config method
    success = config_manager.delete_config(singular_type, component_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete component '{component_id}'.",
        )

    return {"message": f"Component '{component_id}' deleted successfully."}


@router.post("/components/{component_type}/{component_id}/validate", response_model=Dict[str, Any])
async def validate_component(
    component_type: str,
    component_id: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Validate a component's configuration.
    """
    # Convert plural to singular if needed
    singular_type = PLURAL_TO_SINGULAR.get(component_type, component_type)

    # Get the component
    config = config_manager.get_config(singular_type, component_id)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Component '{component_id}' of type '{component_type}' not found.",
        )

    is_valid, errors = config_manager.validate_component(singular_type, component_id)

    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"Validation failed: {', '.join(errors)}",
        )

    return {"message": f"Component '{component_id}' is valid."}


# File Operations
@router.get("/sources", response_model=List[Dict[str, Any]])
async def list_config_sources(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    List all configuration source directories with context information.

    Returns a list of configuration source directories in priority order,
    including their context (project/workspace/user) and associated names.
    """
    return config_manager.list_config_sources()


@router.get("/files/{source_name}", response_model=List[str])
async def list_config_files_by_source(
    source_name: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    List all configuration files for a specific source.

    Returns a list of relative file paths for the given source.
    """
    files = config_manager.list_config_files(source_name)
    if not files and source_name not in [
        s["project_name"] or s.get("workspace_name", "") for s in config_manager.list_config_sources()
    ]:
        # Check if the source itself exists to differentiate empty source from invalid source
        sources = config_manager.list_config_sources()
        source_names = [
            s.get("project_name") or ("workspace" if s["context"] == "workspace" else None) for s in sources
        ]
        if source_name not in source_names:
            raise HTTPException(
                status_code=404,
                detail=f"Source '{source_name}' not found.",
            )
    return files


@router.get("/files/{source_name}/{file_path:path}", response_model=str)
async def get_file_content(
    source_name: str,
    file_path: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Get the content of a specific configuration file.
    """
    content = config_manager.get_file_content(source_name, file_path)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_path}' not found in source '{source_name}'.",
        )
    return content


@router.post("/files", response_model=Dict[str, Any])
async def create_config_file(
    request: FileCreateRequest,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Create a new configuration file.
    """
    success = config_manager.create_config_file(request.source_name, request.relative_path, request.content)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create file '{request.relative_path}' in source '{request.source_name}'.",
        )
    return {"message": "File created successfully."}


@router.put("/files/{source_name}/{file_path:path}", response_model=Dict[str, Any])
async def update_config_file(
    source_name: str,
    file_path: str,
    request: FileUpdateRequest,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Update an existing configuration file.
    """
    success = config_manager.update_config_file(source_name, file_path, request.content)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update file '{file_path}' in source '{source_name}'.",
        )
    return {"message": "File updated successfully."}


@router.delete("/files/{source_name}/{file_path:path}", response_model=Dict[str, Any])
async def delete_config_file(
    source_name: str,
    file_path: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Delete an existing configuration file.
    """
    success = config_manager.delete_config_file(source_name, file_path)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete file '{file_path}' in source '{source_name}'.",
        )
    return {"message": "File deleted successfully."}


@router.post("/validate", response_model=List[Dict[str, Any]])
async def validate_all_components(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Validate all components in the system.
    """
    errors = config_manager.validate_all_components()
    if errors:
        raise HTTPException(
            status_code=422,
            detail=errors,
        )
    return []


# Configuration Management Operations
@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_configs(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Force refresh all configurations from disk.
    This will reload all configuration files and rebuild the component index.
    """
    try:
        config_manager.refresh()
        return {"message": "Configurations refreshed successfully."}
    except Exception as e:
        logger.error(f"Failed to refresh configurations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh configurations: {str(e)}",
        ) from e


# Project Management Operations
@router.get("/projects", response_model=List[ProjectInfo])
async def list_projects(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    List all projects in the current workspace.
    """
    projects = config_manager.list_projects()
    return [ProjectInfo(**project) for project in projects]


@router.post("/projects", response_model=Dict[str, Any])
async def create_project(
    project_data: ProjectCreate,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Create a new project in the current workspace.
    """
    success = config_manager.create_project(project_data.name, project_data.description)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project '{project_data.name}'.",
        )

    # Refresh to include the new project
    config_manager.refresh()

    return {"message": f"Project '{project_data.name}' created successfully."}


@router.get("/projects/active", response_model=Optional[ProjectInfo])
async def get_active_project(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Get information about the currently active project.
    """
    project = config_manager.get_active_project()
    if project:
        return ProjectInfo(**project)
    return None


@router.get("/projects/{name}", response_model=ProjectInfo)
async def get_project(
    name: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Get information about a specific project.
    """
    project = config_manager.get_project_info(name)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{name}' not found.",
        )
    return ProjectInfo(**project)


@router.put("/projects/{name}", response_model=Dict[str, Any])
async def update_project(
    name: str,
    project_data: ProjectUpdate,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Update a project's configuration.
    """
    updates = {}
    if project_data.description is not None:
        updates["description"] = project_data.description
    if project_data.include_configs is not None:
        updates["include_configs"] = project_data.include_configs
    if project_data.new_name is not None:
        updates["new_name"] = project_data.new_name

    success = config_manager.update_project(name, updates)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update project '{name}'.",
        )

    # Refresh if renamed
    if project_data.new_name:
        config_manager.refresh()

    return {"message": f"Project '{name}' updated successfully."}


@router.delete("/projects/{name}", response_model=Dict[str, Any])
async def delete_project(
    name: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Delete a project from the workspace.
    """
    success, error_message = config_manager.delete_project(name)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=error_message or f"Failed to delete project '{name}'.",
        )

    # Refresh to remove the project from index
    config_manager.refresh()

    return {"message": f"Project '{name}' deleted successfully."}


# Workspace Management Operations
@router.get("/workspaces", response_model=List[WorkspaceInfo])
async def list_workspaces(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    List workspace information (currently supports single workspace).
    """
    workspace = config_manager.get_workspace_info()
    if workspace:
        return [WorkspaceInfo(**workspace)]
    return []


@router.get("/workspaces/active", response_model=Optional[WorkspaceInfo])
async def get_active_workspace(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Get information about the currently active workspace.
    """
    workspace = config_manager.get_workspace_info()
    if workspace:
        return WorkspaceInfo(**workspace)
    return None
