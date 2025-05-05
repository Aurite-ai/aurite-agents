import logging
import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

# Import dependencies from the new location (relative to parent of routes' parent)
from ...dependencies import get_api_key, PROJECT_ROOT

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/configs", # Prefix for all routes in this router
    tags=["Config Management"], # Tag for OpenAPI docs
    # dependencies=[Depends(get_api_key)] # Apply auth to all routes in this router
)

# --- Config File CRUD Logic ---

# Define allowed component types and their base directories relative to PROJECT_ROOT
CONFIG_DIRS = {
    "agents": Path("config/agents"),
    "clients": Path("config/clients"),
    "workflows": Path("config/workflows"),
}

# Helper function for security - ensure path is within allowed config dirs
# Moved from api.py
def get_validated_config_path(component_type: str, filename: str | None = None) -> Path:
    if component_type not in CONFIG_DIRS:
        raise HTTPException(status_code=400, detail="Invalid component type specified.")

    base_dir = PROJECT_ROOT / CONFIG_DIRS[component_type]

    # Create directory if it doesn't exist (for listing/creation)
    base_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        # Validate filename
        if ".." in filename or "/" in filename or "\\" in filename:
             raise HTTPException(status_code=400, detail="Invalid filename.")
        if not filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Filename must end with .json")

        full_path = (base_dir / filename).resolve()

        # Security check
        if not str(full_path).startswith(str(base_dir.resolve())):
             raise HTTPException(status_code=400, detail="Invalid path specified.")
        return full_path
    else:
        return base_dir.resolve()


@router.get("/{component_type}", response_model=List[str], dependencies=[Depends(get_api_key)])
async def list_config_files(
    component_type: str,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level if preferred
):
    """Lists available JSON configuration files for a given component type."""
    logger.info(f"Request received to list configs for type: {component_type}")
    try:
        config_dir = get_validated_config_path(component_type)
        logger.debug(f"Listing files in validated directory: {config_dir}")

        if not config_dir.is_dir():
             logger.warning(f"Config directory not found for type '{component_type}' at {config_dir}")
             return []

        json_files = [f.name for f in config_dir.iterdir() if f.is_file() and f.suffix == '.json']
        logger.info(f"Found {len(json_files)} config files for type '{component_type}'")
        return json_files
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error listing config files for type '{component_type}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list configuration files: {str(e)}")


@router.get("/{component_type}/{filename}", dependencies=[Depends(get_api_key)])
async def get_config_file(
    component_type: str,
    filename: str,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level if preferred
):
    """Gets the content of a specific JSON configuration file."""
    logger.info(f"Request received to get config file: {component_type}/{filename}")
    try:
        file_path = get_validated_config_path(component_type, filename)
        logger.debug(f"Reading content from validated path: {file_path}")

        if not file_path.is_file():
            logger.warning(f"Config file not found at path: {file_path}")
            raise HTTPException(status_code=404, detail="Configuration file not found.")

        content = file_path.read_text()
        try:
            json_content = json.loads(content)
            return json_content
        except json.JSONDecodeError as json_err:
             logger.error(f"Error decoding JSON from file {file_path}: {json_err}")
             raise HTTPException(status_code=500, detail=f"Failed to parse file content as JSON: {str(json_err)}")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error reading config file '{component_type}/{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read configuration file: {str(e)}")

# Add POST, PUT, DELETE endpoints here later...
