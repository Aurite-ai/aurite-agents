import logging
from pathlib import Path
from typing import Dict, Any, List, Optional  # Added List and Optional
import json
from pydantic import ValidationError, BaseModel  # Added BaseModel here

# Use relative import for models and the ComponentManager
from .config_models import (
    ProjectConfig,
    ClientConfig,
    LLMConfig,
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    HostConfig,  # Added HostConfig import
)
from .component_manager import ComponentManager
from .config_utils import resolve_path_fields  # Import the utility

# PROJECT_ROOT_DIR is no longer used here.
# Path resolution will be based on current_project_root (for user project files)
# or handled by ComponentManager using importlib.resources (for packaged defaults).

from termcolor import colored  # Added import

logger = logging.getLogger(__name__)


class ProjectManager:
    """
    Manages the loading and resolution of project configurations.
    It uses a ComponentManager to resolve references to reusable components.
    """

    def __init__(self, component_manager: ComponentManager):
        """
        Initializes the ProjectManager.

        Args:
            component_manager: An initialized instance of ComponentManager.
        """
        if not isinstance(component_manager, ComponentManager):
            raise TypeError("component_manager must be an instance of ComponentManager")
        self.component_manager = component_manager
        self.active_project_config: Optional[ProjectConfig] = None
        self.current_project_root: Optional[Path] = (
            None  # For storing the root of the active project
        )
        component_counts = self.component_manager.get_component_counts()
        count_str = ", ".join(
            f"{count} {ctype}" for ctype, count in component_counts.items()
        )
        logger.debug(
            f"ProjectManager initialized, ComponentManager loaded: {count_str if count_str else '0 components'}."
        )

    def _parse_and_resolve_project_data(
        self,
        project_data: Dict[str, Any],
        project_identifier_for_logging: str,
        current_project_root_for_inline_res: Path,
    ) -> ProjectConfig:
        """
        Parses a dictionary of project data, resolving component references
        using the associated ComponentManager, and returns the ProjectConfig object.
        This is the core logic used by parse_project_file and for validating project data.

        Args:
            project_data: A dictionary containing the raw project data.
            project_identifier_for_logging: A string (e.g., filename) for logging context.

        Returns:
            A fully resolved ProjectConfig object.

        Raises:
            RuntimeError: If validation errors occur.
            ValueError: If component references are invalid or cannot be resolved.
        """
        project_name = project_data.get("name", project_identifier_for_logging)
        project_description = project_data.get("description")
        logger.debug(
            f"Processing project data for: '{project_name}' (source: {project_identifier_for_logging})"
        )

        # Resolve all component types using the helper
        resolved_mcp_servers = self._resolve_components(
            project_data,
            project_name,  # For logging context within _resolve_components
            "mcp_servers",
            ClientConfig,
            "name",
            "MCP Server",
            "mcp_servers",
            current_project_root_for_inline_res,
        )
        resolved_llm_configs = self._resolve_components(
            project_data,
            project_name,
            "llms",  # Changed from llm_configs
            LLMConfig,
            "llm_id",
            "LLMConfig",
            "llm_configs",  # COMPONENT_META key for llms is 'llm_configs'
            current_project_root_for_inline_res,
        )
        resolved_agents = self._resolve_components(
            project_data,
            project_name,
            "agents",  # Changed from agent_configs
            AgentConfig,
            "name",
            "Agent",
            "agents",  # COMPONENT_META key for agents is 'agents'
            current_project_root_for_inline_res,
        )
        resolved_simple_workflows = self._resolve_components(
            project_data,
            project_name,
            "simple_workflows",  # Changed from simple_workflow_configs
            WorkflowConfig,
            "name",
            "SimpleWorkflow",
            "simple_workflows",  # COMPONENT_META key for simple_workflows is 'simple_workflows'
            current_project_root_for_inline_res,
        )
        resolved_custom_workflows = self._resolve_components(
            project_data,
            project_name,
            "custom_workflows",  # Changed from custom_workflow_configs
            CustomWorkflowConfig,
            "name",
            "CustomWorkflow",
            "custom_workflows",  # COMPONENT_META key for custom_workflows is 'custom_workflows'
            current_project_root_for_inline_res,
        )

        try:
            # Validate the final ProjectConfig structure
            project_config = ProjectConfig(
                name=project_name,
                description=project_description,
                mcp_servers=resolved_mcp_servers,
                llms=resolved_llm_configs,  # Changed from llm_configs
                agents=resolved_agents,  # Changed from agent_configs
                simple_workflows=resolved_simple_workflows,  # Changed from simple_workflow_configs
                custom_workflows=resolved_custom_workflows,  # Changed from custom_workflow_configs
            )
            logger.debug(
                f"Successfully parsed and resolved project data for '{project_name}'."
            )
            return project_config
        except ValidationError as e:
            logger.error(
                f"Failed to validate final ProjectConfig for '{project_name}' from {project_identifier_for_logging}: {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to validate final ProjectConfig for '{project_name}': {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error assembling final ProjectConfig for '{project_name}' from {project_identifier_for_logging}: {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"An unexpected error assembling final ProjectConfig for '{project_name}': {e}"
            ) from e

    def parse_project_file(self, project_config_file_path: Path) -> ProjectConfig:
        """
        Reads and parses a project configuration file, resolving component references
        using the associated ComponentManager, and returns the ProjectConfig object.
        This method does NOT set the parsed project as the active project.

        Args:
            project_config_file_path: Path to the project JSON file.

        Returns:
            A fully resolved ProjectConfig object.

        Raises:
            FileNotFoundError: If the project file does not exist.
            RuntimeError: If JSON parsing fails or validation errors occur.
            ValueError: If component references are invalid or cannot be resolved.
        """
        logger.debug(
            f"Reading and parsing project configuration from: {project_config_file_path}"
        )
        if not project_config_file_path.is_file():
            raise FileNotFoundError(
                f"Project configuration file not found: {project_config_file_path}"
            )

        try:
            with open(project_config_file_path, "r") as f:
                project_data_dict = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(
                f"Error parsing project configuration file {project_config_file_path}: {e}"
            )
            raise RuntimeError(f"Error parsing project configuration file: {e}") from e

        # Use the new internal method to do the actual parsing and resolution
        # Establish current_project_root before calling _parse_and_resolve_project_data
        current_project_root = project_config_file_path.parent
        # Load project-specific components from user's project structure
        # This needs to happen *before* _parse_and_resolve_project_data if it relies on these components
        # being available in ComponentManager for string-based lookups.
        self.component_manager.load_project_components(current_project_root)

        return self._parse_and_resolve_project_data(
            project_data_dict, str(project_config_file_path), current_project_root
        )

    def load_project(self, project_config_file_path: Path) -> ProjectConfig:
        """
        Loads a project configuration file by parsing it and then sets it
        as the active project in the ProjectManager. If the file is not found,
        it creates an empty ProjectConfig instead of raising an error.

        Args:
            project_config_file_path: Path to the project JSON file.

        Returns:
            A fully resolved ProjectConfig object, which may be empty if the file was not found.

        Raises:
            RuntimeError: If JSON parsing fails or validation errors occur.
            ValueError: If component references are invalid or cannot be resolved.
        """
        logger.debug(
            f"Attempting to load project configuration from: {project_config_file_path} and set as active."
        )
        self.current_project_root = project_config_file_path.parent
        logger.debug(f"Current project root set to: {self.current_project_root}")

        # Load project-specific components from the user's project structure.
        # This allows user components to override packaged defaults.
        self.component_manager.load_project_components(self.current_project_root)

        try:
            # Parse the project file. This will use components already loaded into ComponentManager
            # (both packaged and project-specific) for resolving string references.
            project_config = self.parse_project_file(project_config_file_path)
            logger.info(
                colored(
                    f"Project '{project_config.name}' successfully loaded from `{project_config_file_path}`.",
                    "yellow",
                    attrs=["bold"],
                )
            )
        except FileNotFoundError:
            project_name = project_config_file_path.name
            logger.warning(
                f"Project file not found at {project_config_file_path}. Creating an empty project named '{project_name}'."
            )
            project_config = ProjectConfig(name=project_name, description=None)

        # Set the parsed or newly created project_config as the active one
        self.active_project_config = project_config
        return project_config

    def unload_active_project(self):
        if self.active_project_config:
            logger.info(
                f"Unloading active project '{self.active_project_config.name}' from ProjectManager."
            )
            self.active_project_config = None
            self.current_project_root = None  # Clear current_project_root as well
        else:
            logger.info("No active project to unload from ProjectManager.")

    def get_active_project_config(self) -> Optional[ProjectConfig]:
        return self.active_project_config

    def get_host_config_for_active_project(
        self,
    ) -> Optional[HostConfig]:  # No longer need quotes, HostConfig is imported
        if not self.active_project_config:
            logger.warning(
                "Cannot get HostConfig: No active project loaded in ProjectManager."
            )
            return None
        return HostConfig(
            name=self.active_project_config.name,
            description=self.active_project_config.description,
            mcp_servers=list(self.active_project_config.mcp_servers.values()),
        )

    def add_component_to_active_project(
        self,
        component_type_key: str,
        component_id: str,
        component_model: BaseModel,  # No longer need quotes
    ):
        if not self.active_project_config:
            logger.error(
                "Cannot add component: No active project loaded in ProjectManager."
            )
            raise RuntimeError("No active project to add component to.")

        target_dict = getattr(self.active_project_config, component_type_key, None)
        if target_dict is None or not isinstance(target_dict, dict):
            logger.error(
                f"Invalid component_type_key '{component_type_key}' for active_project_config."
            )
            raise ValueError(f"Invalid component type key: {component_type_key}")

        target_dict[component_id] = component_model
        logger.debug(
            f"Component '{component_id}' of type '{component_type_key}' added to active project '{self.active_project_config.name}'."
        )

    # --- Private Helper for Resolving ---
    def _resolve_components(
        self,
        project_data: Dict[str, Any],  # The raw data from the project file
        project_name: str,  # For logging context
        project_key: str,  # e.g., "clients", "agent_configs"
        model_class: type,
        id_field: str,
        type_name: str,  # User-friendly type name for logging, e.g., "Client", "Agent"
        cm_component_type_key: str,  # Exact key for ComponentManager, e.g., "clients", "agents"
        current_project_root_for_inline_res: Path,  # Added to pass to resolve_path_fields
    ) -> Dict[str, Any]:
        """
        Helper function to resolve component references or use inline definitions
        within a project configuration. Uses the ComponentManager to look up referenced IDs.
        """
        resolved_items: Dict[str, Any] = {}
        item_references = project_data.get(project_key, []) or []

        if not isinstance(item_references, list):
            logger.warning(
                f"'{project_key}' in project '{project_name}' is not a list. Skipping resolution for this key."
            )
            return {}

        for item_ref in item_references:
            component_id = None
            try:
                if isinstance(item_ref, str):  # It's an ID reference
                    component_id = item_ref
                    # Use ComponentManager to get the pre-loaded, validated component
                    component_model = self.component_manager.get_component_config(
                        cm_component_type_key,
                        component_id,  # Use the exact key
                    )
                    if component_model:
                        resolved_items[component_id] = component_model
                        logger.debug(
                            f"Resolved {type_name} component reference: '{component_id}'"
                        )
                    else:
                        # Raise or log warning? Let's raise for now, as a missing reference is likely an error.
                        logger.error(
                            f"{type_name} component ID '{component_id}' referenced in project '{project_name}' not found in ComponentManager."
                        )
                        raise ValueError(
                            f"{type_name} component ID '{component_id}' not found."
                        )

                elif isinstance(item_ref, dict):  # Inline definition
                    component_id = item_ref.get(id_field)
                    if not component_id:
                        logger.warning(
                            f"Inline {type_name} definition missing ID field '{id_field}' in project '{project_name}'. Skipping: {item_ref}"
                        )
                        continue

                    # Resolve paths for the inline definition using the utility function
                    data_to_validate = resolve_path_fields(
                        item_ref, model_class, current_project_root_for_inline_res
                    )

                    # Validate the inline definition
                    inline_item = model_class(**data_to_validate)

                    # Decide precedence: Let inline definition override component if ID conflicts
                    if component_id in resolved_items:
                        logger.warning(
                            f"Inline {type_name} definition for '{component_id}' overrides previously resolved reference in project '{project_name}'."
                        )
                    resolved_items[component_id] = inline_item
                    logger.debug(
                        f"Loaded and validated inline {type_name} definition: '{component_id}'"
                    )

                    # Also add/update it in the component manager's central store
                    # so it's available for other components to look up during this project load.
                    cm_store = self.component_manager._component_stores.get(
                        cm_component_type_key
                    )
                    if cm_store is not None:
                        cm_store[component_id] = inline_item
                        logger.debug(
                            f"Registered inline {type_name} '{component_id}' to ComponentManager's in-memory store."
                        )
                else:
                    logger.warning(
                        f"Invalid {type_name} reference in project '{project_name}'. Expected string ID or dict definition. Got: {item_ref}"
                    )

            except ValidationError as e:
                logger.error(
                    f"Validation failed for inline {type_name} definition '{component_id or item_ref}' in project '{project_name}': {e}"
                )
                # Decide whether to skip this item or raise an error for the whole project load
                raise ValueError(f"Invalid inline {type_name} definition: {e}") from e
            except (
                ValueError
            ) as e:  # Catch missing reference or inline validation errors specifically
                logger.error(
                    f"Value error processing {type_name} reference '{component_id or item_ref}' in project '{project_name}': {e}",
                    exc_info=True,  # Include traceback for ValueError as well
                )
                # Re-raise the ValueError so it's not caught by the generic Exception handler below
                raise
            except Exception as e:  # Catch other unexpected errors
                logger.error(
                    f"Unexpected error processing {type_name} reference '{component_id or item_ref}' in project '{project_name}': {e}",
                    exc_info=True,  # Changed message to 'Unexpected error'
                )
                # Decide whether to skip or raise
                raise RuntimeError(
                    f"Error processing {type_name} reference: {e}"
                ) from e

        return resolved_items

    def create_project_file(
        self,
        project_name: str,
        project_file_path: Path,  # Changed from file_path to project_file_path for clarity
        project_description: Optional[str] = None,
        client_configs: Optional[List[ClientConfig]] = None,
        llm_configs: Optional[List[LLMConfig]] = None,
        agent_configs: Optional[List[AgentConfig]] = None,
        simple_workflow_configs: Optional[List[WorkflowConfig]] = None,
        custom_workflow_configs: Optional[List[CustomWorkflowConfig]] = None,
        overwrite: bool = False,
    ) -> ProjectConfig:
        """
        Creates a new project JSON file from the provided configurations and metadata.

        Args:
            project_name: The name of the project.
            project_file_path: The absolute Path where the project JSON file should be created.
            project_description: Optional description for the project.
            client_configs: Optional list of ClientConfig objects.
            llm_configs: Optional list of LLMConfig objects.
            agent_configs: Optional list of AgentConfig objects.
            simple_workflow_configs: Optional list of WorkflowConfig objects.
            custom_workflow_configs: Optional list of CustomWorkflowConfig objects.
            overwrite: If True, overwrite the file if it already exists. Defaults to False.

        Returns:
            The created ProjectConfig object.

        Raises:
            FileExistsError: If the project file already exists and overwrite is False.
            IOError: If there's an error writing the file.
            RuntimeError: For other unexpected errors or Pydantic validation issues.
            TypeError: If project_file_path is not a Path object.
        """
        logger.info(
            f"Attempting to create project file '{project_name}' at: {project_file_path}, overwrite={overwrite}"
        )

        try:
            if not isinstance(project_file_path, Path):
                raise TypeError("project_file_path must be a Path object.")
            # Path resolution should ideally happen before calling this, or be clearly documented.
            # For now, assume project_file_path is the final intended path.

            if project_file_path.exists() and not overwrite:
                logger.error(
                    f"Project file {project_file_path} already exists and overwrite is False."
                )
                raise FileExistsError(
                    f"Project file {project_file_path} already exists. Set overwrite=True to replace it."
                )

            # Construct dictionaries for ProjectConfig
            mcp_servers_dict = (
                {c.name: c for c in client_configs} if client_configs else {}
            )
            # Input arg is llm_configs, but ProjectConfig field is llms
            llms_dict = {lc.llm_id: lc for lc in llm_configs} if llm_configs else {}
            # Input arg is agent_configs, but ProjectConfig field is agents
            agents_dict = (
                {ac.name: ac for ac in agent_configs if ac.name}
                if agent_configs
                else {}
            )
            # Input arg is simple_workflow_configs, but ProjectConfig field is simple_workflows
            simple_workflows_dict = (
                {swc.name: swc for swc in simple_workflow_configs if swc.name}
                if simple_workflow_configs
                else {}
            )
            # Input arg is custom_workflow_configs, but ProjectConfig field is custom_workflows
            custom_workflows_dict = (
                {cwfc.name: cwfc for cwfc in custom_workflow_configs if cwfc.name}
                if custom_workflow_configs
                else {}
            )

            # Create ProjectConfig model instance
            project_config_model = ProjectConfig(
                name=project_name,
                description=project_description,
                mcp_servers=mcp_servers_dict,
                llms=llms_dict,  # Changed from llm_configs
                agents=agents_dict,  # Changed from agent_configs
                simple_workflows=simple_workflows_dict,  # Changed from simple_workflow_configs
                custom_workflows=custom_workflows_dict,  # Changed from custom_workflow_configs
            )

            # Ensure parent directory exists
            project_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize ProjectConfig to JSON and write to file
            # Use .model_dump_json() for Pydantic v2
            project_json_content = project_config_model.model_dump_json(indent=4)

            with open(project_file_path, "w") as f:
                f.write(project_json_content)

            logger.info(
                f"Successfully created project file for '{project_name}' at {project_file_path}"
            )
            return project_config_model

        except FileExistsError:  # Re-raise specifically
            raise
        except (
            TypeError,
            ValidationError,
        ) as e:  # Catch Pydantic validation or type errors
            logger.error(
                f"Invalid data for creating project '{project_name}': {e}",
                exc_info=True,
            )
            raise
        except IOError as e:
            logger.error(
                f"Failed to write project file {project_file_path}: {e}", exc_info=True
            )
            raise IOError(f"Failed to write project file: {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error creating project file '{project_name}' at {project_file_path}: {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"An unexpected error occurred during project file creation for '{project_name}': {e}"
            ) from e
