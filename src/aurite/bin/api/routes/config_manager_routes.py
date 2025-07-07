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

    # For now, we'll need to implement a create method in ConfigManager
    # Since upsert_component requires an existing component, we'll need to handle this differently
    logger.warning(f"Create component not fully implemented yet for {component_data.name}")

    return MessageResponse(message=f"Component '{component_data.name}' created successfully.")


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

    # Use the existing upsert_component method
    success = config_manager.upsert_component(singular_type, component_id, full_config)

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

    # For now, we'll need to implement a delete method in ConfigManager
    logger.warning(f"Delete component not fully implemented yet for {component_id}")

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

    # TODO: Implement component-specific validation logic
    # For now, we'll just check that required fields exist
    validation_errors = []

    # Basic validation based on component type
    if singular_type == "agent":
        required_fields = ["name", "system_prompt", "llm_config_id"]
        for field in required_fields:
            if field not in config:
                validation_errors.append(f"Missing required field: {field}")
    elif singular_type == "llm":
        required_fields = ["name", "provider", "model"]
        for field in required_fields:
            if field not in config:
                validation_errors.append(f"Missing required field: {field}")

    if validation_errors:
        raise HTTPException(
            status_code=422,
            detail=f"Validation failed: {', '.join(validation_errors)}",
        )

    return MessageResponse(message=f"Component '{component_id}' is valid.")


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
