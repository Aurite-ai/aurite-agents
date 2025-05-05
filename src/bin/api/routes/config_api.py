import logging
import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel # Add this import

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
        # Removed explicit ".." check - rely on resolve() and startswith() check below for security.
        # Keep checks for explicit path separators within the filename itself.
        if "/" in filename or "\\" in filename:
             raise HTTPException(status_code=400, detail="Invalid filename (contains path separators).")
        if not filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Filename must end with .json.")

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


@router.get("/{component_type}/{filename:path}", dependencies=[Depends(get_api_key)])
async def get_config_file(
    component_type: str,
    filename: str, # filename will now contain the full path segment
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


# --- Pydantic Model for Upload ---
class ConfigContent(BaseModel):
    """Model for the JSON content being uploaded."""
    content: dict # Expecting a dictionary for the JSON content

@router.post("/{component_type}/{filename:path}", status_code=201, dependencies=[Depends(get_api_key)])
async def upload_config_file(
    component_type: str,
    filename: str, # filename will now contain the full path segment
    config_data: ConfigContent,
    # api_key: str = Depends(get_api_key), # Applied at router level
):
    """Creates or overwrites a specific JSON configuration file."""
    logger.info(f"Request received to upload config file: {component_type}/{filename}")
    try:
        file_path = get_validated_config_path(component_type, filename)
        logger.debug(f"Writing content to validated path: {file_path}")

        # Basic validation: Ensure filename matches expected pattern if needed
        # (get_validated_config_path already checks for .json and path traversal)

        # Check if file already exists (optional, could return 409 Conflict if needed)
        # if file_path.exists():
        #     logger.warning(f"Config file {file_path} already exists. Overwriting.")
            # raise HTTPException(status_code=409, detail="Configuration file already exists.")

        # Write the content (pretty-printed JSON)
        try:
            json_string = json.dumps(config_data.content, indent=4)
            file_path.write_text(json_string)
            logger.info(f"Successfully wrote config file: {file_path}")
            return {"status": "success", "filename": filename, "component_type": component_type}
        except TypeError as json_err:
            logger.error(f"Error serializing provided content to JSON for {file_path}: {json_err}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON content provided: {str(json_err)}")
        except IOError as io_err:
            logger.error(f"Error writing config file {file_path}: {io_err}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to write configuration file: {str(io_err)}")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error uploading config file '{component_type}/{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload configuration file: {str(e)}")


@router.put("/{component_type}/{filename:path}", status_code=200, dependencies=[Depends(get_api_key)])
async def update_config_file(
    component_type: str,
    filename: str,
    config_data: ConfigContent,
):
    """Updates an existing specific JSON configuration file."""
    logger.info(f"Request received to update config file: {component_type}/{filename}")
    try:
        file_path = get_validated_config_path(component_type, filename)
        logger.debug(f"Updating content at validated path: {file_path}")

        # Ensure the file exists before updating
        if not file_path.is_file():
            logger.warning(f"Config file not found for update at path: {file_path}")
            raise HTTPException(status_code=404, detail="Configuration file not found for update.")

        # Write the new content (pretty-printed JSON)
        try:
            json_string = json.dumps(config_data.content, indent=4)
            file_path.write_text(json_string)
            logger.info(f"Successfully updated config file: {file_path}")
            return {"status": "success", "filename": filename, "component_type": component_type}
        except TypeError as json_err:
            logger.error(f"Error serializing provided content to JSON for {file_path}: {json_err}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON content provided: {str(json_err)}")
        except IOError as io_err:
            logger.error(f"Error writing config file {file_path}: {io_err}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to write configuration file: {str(io_err)}")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error updating config file '{component_type}/{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update configuration file: {str(e)}")


@router.delete("/{component_type}/{filename:path}", status_code=200, dependencies=[Depends(get_api_key)])
async def delete_config_file(
    component_type: str,
    filename: str,
):
    """Deletes a specific JSON configuration file."""
    logger.info(f"Request received to delete config file: {component_type}/{filename}")
    try:
        file_path = get_validated_config_path(component_type, filename)
        logger.debug(f"Attempting to delete file at validated path: {file_path}")

        # Ensure the file exists before deleting
        if not file_path.is_file():
            logger.warning(f"Config file not found for deletion at path: {file_path}")
            raise HTTPException(status_code=404, detail="Configuration file not found for deletion.")

        # Delete the file
        try:
            file_path.unlink() # Use unlink() from pathlib
            logger.info(f"Successfully deleted config file: {file_path}")
            return {"status": "success", "filename": filename, "component_type": component_type, "message": "File deleted successfully."}
        except OSError as os_err:
            logger.error(f"Error deleting config file {file_path}: {os_err}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to delete configuration file: {str(os_err)}")

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (like 400 from validation, 404 from check)
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error deleting config file '{component_type}/{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete configuration file: {str(e)}")
