from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Security

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


@router.get("/", response_model=List[str])
async def list_component_types(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    List all available component types.
    """
    return list(config_manager.get_all_configs().keys())


@router.get("/{component_type}", response_model=List[Dict[str, Any]])
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


@router.get("/{component_type}/{component_id}", response_model=Dict[str, Any])
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
