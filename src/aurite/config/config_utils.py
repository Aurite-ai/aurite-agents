import logging
from pathlib import Path
from typing import Dict, Any, Type

# Import model classes for type checking and field identification
# These are the models that currently have path fields needing resolution/relativization
from .config_models import ClientConfig, CustomWorkflowConfig

# It's good practice to also import PROJECT_ROOT_DIR if utils need it directly,
# or ensure it's passed in, as we are doing.
# from . import PROJECT_ROOT_DIR # This would create a circular dependency if utils are imported by __init__

logger = logging.getLogger(__name__)


def resolve_path_fields(
    data: Dict[str, Any], model_class: Type, base_path: Path
) -> Dict[str, Any]:
    """
    Resolves string path fields in a data dictionary to absolute Path objects.

    Identifies known path fields (e.g., 'server_path', 'module_path') based
    on the provided Pydantic model_class and converts their string values
    to resolved, absolute Path objects relative to base_path if they
    are not already absolute.

    Args:
        data: The raw data dictionary (e.g., from JSON).
        model_class: The target Pydantic model class to identify path fields.
        base_path: The base directory for resolving relative paths.

    Returns:
        A new dictionary with path fields resolved to Path objects.
        Original data dictionary is not modified.
    """
    resolved_data = data.copy()  # Work with a copy

    if model_class == ClientConfig and "server_path" in resolved_data:
        sp_val = resolved_data["server_path"]
        if sp_val:  # Ensure the path is not None or empty
            sp = Path(sp_val)
            if not sp.is_absolute():
                resolved_data["server_path"] = (base_path / sp).resolve()
            else:
                # If it's already an absolute path, just resolve it to normalize (e.g., handle '..')
                resolved_data["server_path"] = sp.resolve()

    if model_class == CustomWorkflowConfig and "module_path" in resolved_data:
        mp_val = resolved_data["module_path"]
        if mp_val:  # Ensure the path is not None or empty
            mp = Path(mp_val)
            if not mp.is_absolute():
                resolved_data["module_path"] = (base_path / mp).resolve()
            else:
                resolved_data["module_path"] = mp.resolve()

    # Add more 'if model_class == ...' blocks here if other models get path fields
    # that need similar resolution logic.

    return resolved_data


def relativize_path_fields(
    data: Dict[str, Any], model_class: Type, base_path: Path
) -> Dict[str, Any]:
    """
    Converts absolute Path object fields in a data dictionary to relative string paths.

    Identifies Path object fields based on the model_class and converts them
    to string paths relative to base_path if possible. If a path cannot
    be made relative (e.g., it's on a different drive on Windows), it's
    converted to an absolute string path.

    Args:
        data: The data dictionary (e.g., from model.model_dump()).
        model_class: The Pydantic model class to identify path fields.
        base_path: The base directory for creating relative paths.

    Returns:
        A new dictionary with Path fields converted to string paths.
        Original data dictionary is not modified.
    """
    relativized_data = data.copy()  # Work with a copy

    component_id_for_log = "unknown_component"  # Fallback for logging
    if model_class == ClientConfig and "client_id" in relativized_data:
        component_id_for_log = relativized_data["client_id"]
    elif model_class == CustomWorkflowConfig and "name" in relativized_data:
        component_id_for_log = relativized_data["name"]
    # Add more elif for other models if they have a clear ID field for logging

    if model_class == ClientConfig and "server_path" in relativized_data:
        sp_val = relativized_data["server_path"]
        if isinstance(sp_val, Path):
            try:
                relativized_data["server_path"] = str(sp_val.relative_to(base_path))
            except ValueError:
                logger.warning(
                    f"Could not make server_path relative to base_path for "
                    f"{model_class.__name__} '{component_id_for_log}'. Storing absolute path: {sp_val}"
                )
                relativized_data["server_path"] = str(sp_val.resolve())
        elif isinstance(sp_val, str):
            # If it's already a string, assume it's correctly formatted (e.g. already relative or absolute)
            pass

    if model_class == CustomWorkflowConfig and "module_path" in relativized_data:
        mp_val = relativized_data["module_path"]
        if isinstance(mp_val, Path):
            try:
                relativized_data["module_path"] = str(mp_val.relative_to(base_path))
            except ValueError:
                logger.warning(
                    f"Could not make module_path relative to base_path for "
                    f"{model_class.__name__} '{component_id_for_log}'. Storing absolute path: {mp_val}"
                )
                relativized_data["module_path"] = str(mp_val.resolve())
        elif isinstance(mp_val, str):
            pass

    # Add more 'if model_class == ...' blocks here if other models get path fields
    # that need similar relativization logic.

    return relativized_data
