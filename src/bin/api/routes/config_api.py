import logging
import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

# Import dependencies from the new location (relative to parent of routes' parent)
from ...dependencies import (
    get_api_key,
    get_component_manager,
)  # PROJECT_ROOT no longer needed here
from src.config.component_manager import (
    ComponentManager,
)  # For type hinting (Changed to absolute import)

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
    "llm-configs": "llm_configs",  # New API endpoint for LLM configs
    "simple-workflows": "simple_workflows",
    "custom-workflows": "custom_workflows",
    # "testing" type is not managed by ComponentManager, so it's removed from here.
    # If "testing" configs need to be managed, it would require a different mechanism
    # or extending ComponentManager (if appropriate).
}


def _get_cm_component_type(api_component_type: str) -> str:
    """Validates and maps API component type to ComponentManager type key."""
    cm_type = API_TO_CM_TYPE_MAP.get(api_component_type)
    if not cm_type:
        logger.warning(
            f"Invalid component type specified in API path: {api_component_type}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component type '{api_component_type}' specified. "
            f"Valid types are: {', '.join(API_TO_CM_TYPE_MAP.keys())}",
        )
    return cm_type


def _extract_component_id(filename: str) -> str:
    """Extracts component ID from filename (removes .json suffix)."""
    if not filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must end with .json.",
        )
    return filename[:-5]  # Remove .json


@router.get("/{component_type}", response_model=List[str])
async def list_config_files(
    component_type: str,
    cm: ComponentManager = Depends(get_component_manager),
):
    """Lists available JSON configuration filenames for a given component type."""
    logger.info(f"Request received to list configs for API type: {component_type}")
    try:
        cm_component_type = _get_cm_component_type(component_type)
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
    "/{component_type}/{filename:path}", response_model=dict
)  # Return type is dict (JSON)
async def get_config_file(
    component_type: str,
    filename: str,
    cm: ComponentManager = Depends(get_component_manager),
):
    """Gets the content of a specific JSON configuration file."""
    logger.info(f"Request received to get config file: {component_type}/{filename}")
    try:
        cm_component_type = _get_cm_component_type(component_type)
        component_id = _extract_component_id(filename)

        component_model = cm.get_component_config(cm_component_type, component_id)

        if component_model is None:
            logger.warning(
                f"Config component ID '{component_id}' of type '{cm_component_type}' not found."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration file not found.",
            )
        # Return the Pydantic model as a dictionary, which FastAPI will serialize to JSON
        return component_model.model_dump(mode="json")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
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

    content: dict  # Expecting a dictionary for the JSON content


@router.post("/{component_type}/{filename:path}", status_code=status.HTTP_201_CREATED)
async def create_config_file(  # Renamed from upload_config_file for clarity (POST = create)
    component_type: str,
    filename: str,
    config_body: ConfigContent,  # Changed variable name from config_data
    cm: ComponentManager = Depends(get_component_manager),
):
    """Creates a new component JSON configuration file."""
    logger.info(f"Request received to create config file: {component_type}/{filename}")
    try:
        cm_component_type = _get_cm_component_type(component_type)
        component_id_from_path = _extract_component_id(filename)

        # Ensure the ID in the path matches the ID inside the content, if present.
        # ComponentManager's save/create methods also validate this.
        # Here, we primarily use the ID from the path as the definitive one.
        # The content dict itself must contain the ID field.
        config_payload = config_body.content.copy()  # Work with a copy

        # Get the expected ID field name for this component type
        id_field_name = ComponentManager.COMPONENT_META.get(
            cm_component_type, (None, None)
        )[1]
        if not id_field_name:  # Should not happen if _get_cm_component_type worked
            raise HTTPException(
                status_code=500,
                detail="Internal server error: Unknown component ID field.",
            )

        if id_field_name not in config_payload:
            # If ID field is missing in content, inject it from path filename
            config_payload[id_field_name] = component_id_from_path
            logger.debug(
                f"Injected ID '{component_id_from_path}' into payload for type '{cm_component_type}'."
            )
        elif config_payload[id_field_name] != component_id_from_path:
            logger.warning(
                f"ID in path ('{component_id_from_path}') differs from ID in payload ('{config_payload[id_field_name]}') for type '{cm_component_type}'. Using ID from path."
            )
            # Overwrite ID in payload with ID from path to ensure consistency
            config_payload[id_field_name] = component_id_from_path

        # Use create_component_file with overwrite=False for POST
        created_model = cm.create_component_file(
            cm_component_type, config_payload, overwrite=False
        )
        logger.info(
            f"Successfully created component '{created_model.model_dump().get(id_field_name)}' of type '{cm_component_type}'"
        )
        return created_model.model_dump(mode="json")

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
    """Updates an existing specific JSON configuration file. Can also create if not exists (upsert)."""
    logger.info(
        f"Request received to update/create config file: {component_type}/{filename}"
    )
    try:
        cm_component_type = _get_cm_component_type(component_type)
        component_id_from_path = _extract_component_id(filename)

        config_payload = config_body.content.copy()

        id_field_name = ComponentManager.COMPONENT_META.get(
            cm_component_type, (None, None)
        )[1]
        if not id_field_name:
            raise HTTPException(
                status_code=500,
                detail="Internal server error: Unknown component ID field.",
            )

        if id_field_name not in config_payload:
            config_payload[id_field_name] = component_id_from_path
        elif config_payload[id_field_name] != component_id_from_path:
            logger.warning(
                f"ID in path ('{component_id_from_path}') differs from ID in payload ('{config_payload[id_field_name]}') for type '{cm_component_type}'. Using ID from path."
            )
            config_payload[id_field_name] = component_id_from_path

        # save_component_config handles create or update (upsert)
        saved_model = cm.save_component_config(cm_component_type, config_payload)
        logger.info(
            f"Successfully saved (created/updated) component '{saved_model.model_dump().get(id_field_name)}' of type '{cm_component_type}'"
        )
        return saved_model.model_dump(mode="json")

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
