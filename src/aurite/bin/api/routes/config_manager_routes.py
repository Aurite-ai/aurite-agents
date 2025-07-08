from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field

from ....config.config_manager import ConfigManager
from ...dependencies import get_api_key, get_config_manager

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Mapping from plural to singular forms for component types
PLURAL_TO_SINGULAR = {
    "agents": "agent",
    "llms": "llm",
    "mcp_servers": "mcp_server",
    "simple_workflows": "simple_workflow",
    "custom_workflows": "custom_workflow",
}


# Request/Response Models
class ComponentCreate(BaseModel):
    """Request model for creating a new component"""

    name: str = Field(..., description="Unique name for the component")
    config: Dict[str, Any] = Field(..., description="Component configuration")


class ComponentUpdate(BaseModel):
    """Request model for updating an existing component"""

    config: Dict[str, Any] = Field(..., description="Updated component configuration")


class MessageResponse(BaseModel):
    """Standard message response"""

    message: str


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


@router.post("/components/{component_type}", response_model=MessageResponse)
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

    # Check if component already exists
    existing = config_manager.get_config(singular_type, component_data.name)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Component '{component_data.name}' of type '{component_type}' already exists.",
        )

    # Prepare the full config with type and name
    full_config = component_data.config.copy()
    full_config["type"] = singular_type
    full_config["name"] = component_data.name

    result = config_manager.create_component(
        singular_type,
        full_config,
        project=component_data.config.get("project"),
        workspace=component_data.config.get("workspace", False),
        file_path=component_data.config.get("file_path"),
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create component '{component_data.name}'.",
        )

    return result


@router.put("/components/{component_type}/{component_id}", response_model=MessageResponse)
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

    return MessageResponse(message=f"Component '{component_id}' updated successfully.")


@router.delete("/components/{component_type}/{component_id}", response_model=MessageResponse)
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

    return MessageResponse(message=f"Component '{component_id}' deleted successfully.")


@router.post("/components/{component_type}/{component_id}/validate", response_model=MessageResponse)
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

    return MessageResponse(message=f"Component '{component_id}' is valid.")


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


class FileCreateRequest(BaseModel):
    source_name: str
    relative_path: str
    content: str


@router.post("/files", response_model=MessageResponse)
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
    return MessageResponse(message="File created successfully.")


class FileUpdateRequest(BaseModel):
    content: str


@router.put("/files/{source_name}/{file_path:path}", response_model=MessageResponse)
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
    return MessageResponse(message="File updated successfully.")


@router.delete("/files/{source_name}/{file_path:path}", response_model=MessageResponse)
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
    return MessageResponse(message="File deleted successfully.")


# Configuration Management Operations
@router.post("/refresh", response_model=MessageResponse)
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
        return MessageResponse(message="Configurations refreshed successfully.")
    except Exception as e:
        logger.error(f"Failed to refresh configurations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh configurations: {str(e)}",
        ) from e
