from __future__ import annotations

import logging
from typing import Dict, List, Any

from fastapi import APIRouter, Depends, Security

from ....config.config_manager import ConfigManager
from ...dependencies import get_api_key, get_config_manager

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/components", response_model=Dict[str, List[Dict[str, Any]]])
async def list_all_components(
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    List all available components, grouped by type.
    """
    all_components = {}
    for component_type in config_manager._component_index.keys():
        all_components[component_type] = config_manager.list_configs(component_type)
    return all_components
