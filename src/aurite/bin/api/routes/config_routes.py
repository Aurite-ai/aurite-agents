import logging
from pathlib import Path  # Added Path
from typing import Any, List  # Added Any, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from aurite.config.component_manager import (
    ComponentManager,  # Not directly used by get_config_file anymore, but by others
)
from aurite.config.component_manager import COMPONENT_META

# Import dependencies from the new location (relative to parent of routes' parent)
from ...dependencies import (
    get_component_manager,  # get_component_manager will still be used for other endpoints
)
from ...dependencies import get_current_project_root  # Added get_current_project_root
from ...dependencies import get_api_key

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
    "clients": "mcp_servers",
    "llms": "llms",
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
    cm: ComponentManager = Depends(get_component_manager),
    current_project_root: Path = Depends(get_current_project_root),
):
    """Lists available JSON configuration filenames for a given component type."""
    logger.info(f"Request received to list configs for API type: {component_type}")
    try:
        cm_component_type = _get_cm_component_type(component_type)
        filenames = cm.list_component_files(
            cm_component_type, project_root_path=current_project_root
        )
        logger.info(
            f"Found {len(filenames)} config files for CM type '{cm_component_type}' in project {current_project_root}"
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
    "/{component_type}/id/{component_id_or_name}",
    response_model=Any,
    summary="Get a specific component configuration by its ID or name",
)
async def get_specific_component_config_by_id(
    component_type: str,
    component_id_or_name: str,
    cm: ComponentManager = Depends(get_component_manager),
):
    logger.info(
        f"Request received for specific component: type='{component_type}', id/name='{component_id_or_name}'"
    )
    try:
        # Validate and map API component type to ComponentManager's internal type key
        cm_internal_type = _get_cm_component_type(component_type)

        # Retrieve the component model from ComponentManager
        component_model = cm.get_component_config(
            cm_internal_type, component_id_or_name
        )

        if component_model is None:
            logger.warning(
                f"Component type '{component_type}' with ID/name '{component_id_or_name}' not found by ComponentManager."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Component '{component_id_or_name}' of type '{component_type}' not found.",
            )

        logger.info(
            f"Successfully retrieved component '{component_id_or_name}' of type '{component_type}'."
        )
        # Return the Pydantic model dumped as a JSON-compatible dict
        return component_model.model_dump(mode="json")

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (e.g., from _get_cm_component_type or our own 404)
        raise http_exc
    except Exception as e:
        logger.error(
            f"Unexpected error retrieving component: type='{component_type}', id/name='{component_id_or_name}'. Error: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while retrieving the component: {str(e)}",
        )


@router.get(
    "/{component_type}/{filename:path}",
    response_model=Any,  # Changed response_model to Any
)
async def get_config_file(
    component_type: str,
    filename: str,
    current_project_root: Path = Depends(get_current_project_root),
    # cm: ComponentManager = Depends(get_component_manager), # Not using CM directly here
):
    """Gets the raw parsed JSON content of a specific component configuration file."""
    logger.info(
        f"Request to get raw config file content: {component_type}/{filename} from project {current_project_root}"
    )
    try:
        cm_component_type = _get_cm_component_type(
            component_type
        )  # Validates component_type

        if not filename.endswith(".json"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename must end with .json.",
            )

        # Construct path using COMPONENT_SUBDIRS from component_manager
        # This requires COMPONENT_SUBDIRS to be accessible or duplicated here.
        # For now, let's assume COMPONENT_SUBDIRS is available (e.g. imported or defined locally)
        # from aurite.config.component_manager import COMPONENT_SUBDIRS (needs to be added to imports if not already)
        from aurite.config.component_manager import (
            COMPONENT_SUBDIRS,  # Local import for clarity
        )

        subdir_name = COMPONENT_SUBDIRS.get(cm_component_type)
        if not subdir_name:
            logger.error(
                f"No subdirectory mapping for component type '{cm_component_type}'."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: Undefined component subdirectory for '{cm_component_type}'.",
            )

        component_config_dir = (current_project_root / "config" / subdir_name).resolve()
        config_file_path = (component_config_dir / filename).resolve()

        # Security check
        if not str(config_file_path).startswith(str(component_config_dir)):
            logger.error(
                f"Path traversal attempt or invalid filename for get_config_file: {filename}. Resolved to {config_file_path}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename or path.",
            )

        if not config_file_path.is_file():
            logger.warning(f"Config file not found: {config_file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config file '{filename}' of type '{component_type}' not found.",
            )

        import json  # Ensure json is imported

        content = json.loads(config_file_path.read_text(encoding="utf-8"))
        return content

    except HTTPException as http_exc:
        raise http_exc
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from config file {config_file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading config file '{filename}': Invalid JSON content.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in GET /configs/{component_type}/{filename}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while retrieving config file '{filename}': {str(e)}",
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
    current_project_root: Path = Depends(get_current_project_root),
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
            # Actually, cm.create_component_file does not exist. We need to use save_component_config
            # and check for file existence first.
            component_id_for_file_check = config_payload.get(
                id_field_name, component_id_from_path
            )
            file_path_to_check = cm._get_component_file_path(
                cm_component_type, component_id_for_file_check, current_project_root
            )

            if file_path_to_check.exists():
                raise FileExistsError(
                    f"Configuration file {file_path_to_check.name} already exists for component ID {component_id_for_file_check}."
                )

            created_model = cm.save_component_config(
                cm_component_type,
                config_payload,
                project_root_path=current_project_root,
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
                cm_component_type,
                config_body.content,
                filename,
                project_root_path=current_project_root,
                overwrite=False,
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
    current_project_root: Path = Depends(get_current_project_root),
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
                cm_component_type,
                config_payload,
                project_root_path=current_project_root,
            )  # This saves as component_id_from_path.json
            logger.info(
                f"Successfully saved (updated/created) single component '{getattr(saved_model, id_field_name)}' of type '{cm_component_type}' to file {filename}"
            )
            return saved_model.model_dump(mode="json")

        elif isinstance(config_body.content, list):
            # Handle list of components update, overwrites specified filename
            saved_models = cm.save_components_to_file(
                cm_component_type,
                config_body.content,
                filename,
                project_root_path=current_project_root,
                overwrite=True,
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
    current_project_root: Path = Depends(get_current_project_root),
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
        # We need current_project_root for list_component_files
        if cm.get_component_config(cm_component_type, component_id) is None:
            # Further check if file exists on disk, CM might have it in memory but no file
            # However, list_component_files is a better check for "does a file exist for this ID"
            if f"{component_id}.json" not in cm.list_component_files(
                cm_component_type, project_root_path=current_project_root
            ):
                logger.warning(
                    f"Config file '{filename}' of type '{component_type}' not found for deletion in project {current_project_root}."
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Configuration file not found for deletion.",
                )

        deleted = cm.delete_component_config(
            cm_component_type, component_id, project_root_path=current_project_root
        )

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
