import logging
from typing import List, Any, Union  # Added Any, Union
import json  # Added json
from pathlib import Path  # Added Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

# Import dependencies from the new location (relative to parent of routes' parent)
from ...dependencies import (
    get_api_key,
    get_component_manager,  # get_component_manager will still be used for other endpoints
)
from src.config.component_manager import (
    ComponentManager,  # Not directly used by get_config_file anymore, but by others
    COMPONENT_META,
    COMPONENT_TYPES_DIRS,  # Need this for directory lookup
)
from src.config import (
    PROJECT_ROOT_DIR,
)  # For path construction if needed, though COMPONENT_TYPES_DIRS is absolute

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/configs",  # Prefix for all routes in this router
    tags=["Config Management"],  # Tag for OpenAPI docs
    dependencies=[Depends(get_api_key)],  # Apply auth to all routes in this router
)

# --- Config File CRUD Logic ---

# CONFIG_DIRS and get_validated_config_path are no longer needed here,
# ComponentManager handles path logic.

# Mapping from API path component_type to ComponentManager's internal type keys
# This helps keep API paths user-friendly if they differ from internal keys.
# For now, they are mostly the same, but this provides a layer of abstraction.
API_TO_CM_TYPE_MAP = {
    "agents": "agents",
    "clients": "clients",
    "llm-configs": "llm_configs",
    "simple-workflows": "simple_workflows",
    "custom-workflows": "custom_workflows",
}


def _get_cm_component_type(api_component_type: str) -> str:
    """Validates and maps API component type to ComponentManager type key."""
    # This function remains relevant for other endpoints like list_config_files, create, update, delete

    # Handle aliases for workflow types
    if api_component_type == "custom_workflows":
        api_component_type_to_check = "custom-workflows"
    elif api_component_type == "simple_workflows":
        api_component_type_to_check = "simple-workflows"
    else:
        api_component_type_to_check = api_component_type

    cm_type = API_TO_CM_TYPE_MAP.get(api_component_type_to_check)
    if not cm_type:
        logger.warning(
            f"Invalid component type specified in API path: {api_component_type}"
        )
        # Show original API_TO_CM_TYPE_MAP keys in error for clarity on supported backend keys
        valid_keys = list(API_TO_CM_TYPE_MAP.keys())
        # Add underscore versions to the "valid types" message if they are common aliases
        if "simple-workflows" in valid_keys:
            valid_keys.append("simple_workflows")
        if "custom-workflows" in valid_keys:
            valid_keys.append("custom_workflows")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component type '{api_component_type}' specified. "
            f"Valid types are: {', '.join(sorted(list(set(valid_keys))))}",  # Show unique sorted list
        )
    return cm_type


def _extract_component_id(filename: str) -> str:
    """Extracts component ID from filename (removes .json suffix)."""
    # This function remains relevant for create, update, delete if they operate by ID derived from filename
    if not filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must end with .json.",
        )
    return filename[:-5]  # Remove .json


@router.get("/{component_type}", response_model=List[str])
async def list_config_files(
    component_type: str,
    cm: ComponentManager = Depends(get_component_manager),  # cm is used here
):
    """Lists available JSON configuration filenames for a given component type."""
    logger.info(f"Request received to list configs for API type: {component_type}")
    try:
        cm_component_type = _get_cm_component_type(component_type)
        # Assuming ComponentManager.list_component_files() still exists and works as before
        filenames = cm.list_component_files(cm_component_type)
        logger.info(
            f"Found {len(filenames)} config files for CM type '{cm_component_type}'"
        )
        return filenames
    except HTTPException as http_exc:  # Re-raise our own HTTPExceptions
        raise http_exc
    except Exception as e:
        logger.error(
            f"Error listing config files for API type '{component_type}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list configuration files: {str(e)}",
        )


@router.get(
    "/{component_type}/{filename:path}",
    response_model=Any,  # Changed response_model to Any
)
async def get_config_file(  # Removed cm: ComponentManager dependency for this specific endpoint
    component_type: str,
    filename: str,
    # cm: ComponentManager = Depends(get_component_manager), # No longer using CM to get parsed model by ID
):
    """Gets the raw parsed JSON content of a specific configuration file."""
    logger.info(
        f"Request received to get raw config file content: {component_type}/{filename}"
    )
    try:
        # Validate component_type and get the ComponentManager's internal type key
        # _get_cm_component_type can still be used for validation even if not using cm_component_type directly for CM lookup
        cm_component_type_validated = _get_cm_component_type(component_type)

        # Get the base directory for this component type
        # COMPONENT_TYPES_DIRS is imported from component_manager
        config_dir = COMPONENT_TYPES_DIRS.get(cm_component_type_validated)
        if not config_dir:
            # This case should ideally be caught by _get_cm_component_type if API_TO_CM_TYPE_MAP and COMPONENT_TYPES_DIRS are aligned
            logger.error(
                f"No directory configured for component type '{cm_component_type_validated}'. This is an internal configuration issue."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: Directory not configured for type '{component_type}'.",
            )

        file_path = (config_dir / filename).resolve()

        # Security check: ensure the resolved path is within the intended config directory
        if not str(file_path).startswith(str(config_dir.resolve())):
            logger.error(
                f"Path traversal attempt detected or invalid filename for {component_type}/{filename}. Resolved to {file_path}, expected under {config_dir.resolve()}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename or path.",
            )

        if not file_path.is_file():
            logger.warning(f"Configuration file not found at path: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration file '{filename}' not found.",
            )

        with open(file_path, "r") as f:
            raw_json_content = json.load(f)  # Parse JSON from file

        return raw_json_content  # Return the parsed Python object/list

    except json.JSONDecodeError:
        logger.error(
            f"Invalid JSON format in file {component_type}/{filename} at {file_path}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # Or 400 if client could upload malformed
            detail=f"File '{filename}' contains invalid JSON.",
        )
    except HTTPException as http_exc:  # Re-raise our own HTTPExceptions (like 404 or from _get_cm_component_type)
        raise http_exc
    except Exception as e:  # Catch other unexpected errors
        logger.error(
            f"Error reading config file '{component_type}/{filename}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read configuration file: {str(e)}",
        )


# --- Pydantic Model for Upload ---
class ConfigContent(BaseModel):
    """Model for the JSON content being uploaded."""

    content: Any  # Changed from dict to Any to allow arrays or objects initially


@router.post("/{component_type}/{filename:path}", status_code=status.HTTP_201_CREATED)
async def create_config_file(  # Renamed from upload_config_file for clarity (POST = create)
    component_type: str,
    filename: str,
    config_body: ConfigContent,  # Changed variable name from config_data
    cm: ComponentManager = Depends(get_component_manager),
):
    """
    Creates a new component JSON configuration file.
    If 'content' is a dictionary, it creates a single component file (named by its ID).
    If 'content' is a list, it saves all components in the list to the specified 'filename'.
    """
    logger.info(f"Request received to create config file: {component_type}/{filename}")
    try:
        cm_component_type = _get_cm_component_type(component_type)

        if isinstance(config_body.content, dict):
            # Handle single component creation
            component_id_from_path = _extract_component_id(
                filename
            )  # Used for logging/consistency check
            config_payload = config_body.content.copy()

            id_field_name = COMPONENT_META.get(cm_component_type, (None, None))[1]
            if not id_field_name:
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error: Unknown component ID field.",
                )

            # Ensure payload ID matches filename-derived ID if creating a single file by specific name
            # Note: cm.create_component_file internally saves as `internal_id.json`.
            # If filename in path is different, this might be slightly confusing.
            # For strict filename usage with single component, cm.save_components_to_file could be adapted or a new cm method.
            # For now, we align the payload ID with filename for clarity if it's a single object.
            if id_field_name not in config_payload:
                config_payload[id_field_name] = component_id_from_path
            elif config_payload[id_field_name] != component_id_from_path:
                logger.warning(
                    f"ID in payload ('{config_payload[id_field_name]}') for POST to '{filename}' "
                    f"differs from filename-derived ID ('{component_id_from_path}'). "
                    f"Using ID from payload for ComponentManager.create_component_file, which saves as '{config_payload[id_field_name]}.json'."
                )
                # No, cm.create_component_file will use the ID from payload to name the file.
                # The component_id_from_path (derived from {filename} in URL) is what the user *expects* the file to be named.
                # This part needs careful handling if filename from URL is the strict target.
                # For now, let cm.create_component_file handle it, which names file by internal ID.

            created_model = cm.create_component_file(
                cm_component_type, config_payload, overwrite=False
            )
            # The actual filename might be different from 'filename' in path if internal ID differs.
            actual_filename = f"{getattr(created_model, id_field_name)}.json"
            logger.info(
                f"Successfully created single component '{getattr(created_model, id_field_name)}' of type '{cm_component_type}' as {actual_filename}"
            )
            return created_model.model_dump(mode="json")

        elif isinstance(config_body.content, list):
            # Handle list of components creation, save to specified filename
            saved_models = cm.save_components_to_file(
                cm_component_type, config_body.content, filename, overwrite=False
            )
            logger.info(
                f"Successfully created/saved {len(saved_models)} components of type '{cm_component_type}' to file '{filename}'"
            )
            return [model.model_dump(mode="json") for model in saved_models]

        else:
            logger.error(
                f"POST /configs/{component_type}/{filename}: Received content is not a dictionary or a list. Found type: {type(config_body.content)}."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request body: 'content' must be a single JSON object or a list of JSON objects.",
            )

    except FileExistsError as fe_err:
        logger.warning(
            f"Config file {component_type}/{filename} already exists: {fe_err}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration file {filename} already exists. Use PUT to update.",
        )
    except (
        ValueError,
        ValidationError,
    ) as val_err:  # Catch CM's ValueError or Pydantic's ValidationError
        logger.error(
            f"Validation or value error for '{component_type}/{filename}': {val_err}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration data: {str(val_err)}",
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(
            f"Unexpected error creating config file '{component_type}/{filename}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create configuration file: {str(e)}",
        )


@router.put("/{component_type}/{filename:path}", status_code=status.HTTP_200_OK)
async def update_config_file(
    component_type: str,
    filename: str,
    config_body: ConfigContent,
    cm: ComponentManager = Depends(get_component_manager),
):
    """
    Updates an existing specific JSON configuration file.
    If 'content' is a dictionary, it updates/creates a single component file (named by its ID).
    If 'content' is a list, it overwrites the specified 'filename' with all components in the list.
    """
    logger.info(
        f"Request received to update/create config file: {component_type}/{filename}"
    )
    try:
        cm_component_type = _get_cm_component_type(component_type)

        if isinstance(config_body.content, dict):
            # Handle single component update/creation
            component_id_from_path = _extract_component_id(filename)
            config_payload = config_body.content.copy()

            id_field_name = COMPONENT_META.get(cm_component_type, (None, None))[1]
            if not id_field_name:
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error: Unknown component ID field.",
                )

            # Ensure the payload's ID matches the filename-derived ID for saving to the correct file.
            if (
                id_field_name not in config_payload
                or config_payload[id_field_name] != component_id_from_path
            ):
                logger.warning(
                    f"ID in payload for PUT request ('{config_payload.get(id_field_name)}') "
                    f"for file '{filename}' differs from filename-derived ID ('{component_id_from_path}') or is missing. "
                    f"Forcing payload ID to '{component_id_from_path}' to ensure file '{filename}' is updated."
                )
                config_payload[id_field_name] = component_id_from_path

            saved_model = cm.save_component_config(
                cm_component_type, config_payload
            )  # This saves as component_id_from_path.json
            logger.info(
                f"Successfully saved (updated/created) single component '{getattr(saved_model, id_field_name)}' of type '{cm_component_type}' to file {filename}"
            )
            return saved_model.model_dump(mode="json")

        elif isinstance(config_body.content, list):
            # Handle list of components update, overwrites specified filename
            saved_models = cm.save_components_to_file(
                cm_component_type, config_body.content, filename, overwrite=True
            )
            logger.info(
                f"Successfully updated/saved {len(saved_models)} components of type '{cm_component_type}' to file '{filename}'"
            )
            return [model.model_dump(mode="json") for model in saved_models]

        else:
            logger.error(
                f"PUT /configs/{component_type}/{filename}: Received content is not a dictionary or a list. Found type: {type(config_body.content)}."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request body: 'content' must be a single JSON object or a list of JSON objects.",
            )

    except (
        ValueError,  # Catches ID issues from cm methods or _get_cm_component_type
        ValidationError,
    ) as val_err:  # Catch CM's ValueError or Pydantic's ValidationError
        logger.error(
            f"Validation or value error for '{component_type}/{filename}': {val_err}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration data: {str(val_err)}",
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(
            f"Unexpected error saving config file '{component_type}/{filename}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration file: {str(e)}",
        )


@router.delete("/{component_type}/{filename:path}", status_code=status.HTTP_200_OK)
async def delete_config_file(
    component_type: str,
    filename: str,
    cm: ComponentManager = Depends(get_component_manager),
):
    """Deletes a specific JSON configuration file."""
    logger.info(f"Request received to delete config file: {component_type}/{filename}")
    try:
        cm_component_type = _get_cm_component_type(component_type)
        component_id = _extract_component_id(filename)

        # ComponentManager.delete_component_config returns True if deleted (or not found in memory but file also not found)
        # and False if deletion failed (e.g., OS error, or not in memory but file deletion failed).
        # It logs warnings if file not found on disk but was in memory, or vice-versa.
        # For API, if it returns True, it means the state is "deleted" or "was not there".
        # If it returns False, it means an actual error occurred during deletion attempt.

        # Check if component exists first to return 404 if not found at all
        if cm.get_component_config(cm_component_type, component_id) is None:
            # Further check if file exists on disk, CM might have it in memory but no file
            # However, list_component_files is a better check for "does a file exist for this ID"
            if f"{component_id}.json" not in cm.list_component_files(cm_component_type):
                logger.warning(
                    f"Config file '{filename}' of type '{component_type}' not found for deletion."
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Configuration file not found for deletion.",
                )

        deleted = cm.delete_component_config(cm_component_type, component_id)

        if deleted:
            logger.info(
                f"Successfully deleted or confirmed not present for component ID '{component_id}' of type '{cm_component_type}'"
            )
            return {
                "status": "success",
                "filename": filename,
                "component_type": component_type,
                "message": "File deleted successfully or was not found.",
            }
        else:
            # This path implies an actual error during deletion (e.g., file system error)
            # because if the file/component just didn't exist, delete_component_config would likely return True.
            logger.error(
                f"Deletion failed for component ID '{component_id}' of type '{cm_component_type}' due to an internal error."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete configuration file due to an internal error.",
            )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:  # Catch any other unexpected errors
        logger.error(
            f"Unexpected error deleting config file '{component_type}/{filename}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while deleting configuration file: {str(e)}",
        )
