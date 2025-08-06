"""
FileManager class for handling configuration file operations.

This module provides a dedicated class for managing file operations related to
configuration files, including listing sources, reading/writing files, and
managing component storage.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manages file operations for configuration files.

    This class handles all file-related operations for the configuration system,
    including listing configuration sources, reading/writing configuration files,
    and managing the file structure.
    """

    def __init__(
        self,
        config_sources: List[Tuple[Path, Path]],
        project_root: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
        project_name: Optional[str] = None,
        workspace_name: Optional[str] = None,
    ):
        """
        Initialize the FileManager with configuration context.

        Args:
            config_sources: List of (source_path, context_root) tuples
            project_root: Path to the current project root (if in a project)
            workspace_root: Path to the workspace root (if in a workspace)
            project_name: Name of the current project
            workspace_name: Name of the workspace
        """
        self.config_sources = config_sources
        self.project_root = project_root
        self.workspace_root = workspace_root
        self.project_name = project_name
        self.workspace_name = workspace_name

    def _validate_path(self, path: Path) -> bool:
        """
        Validate that a path is safe and within allowed directories.

        Args:
            path: Path to validate

        Returns:
            True if path is valid, False otherwise
        """
        try:
            # Resolve to absolute path
            abs_path = path.resolve()

            # Check if path contains parent directory references
            if ".." in str(path):
                logger.warning(f"Path contains parent directory references: {path}")
                return False

            # Check if path is within one of our allowed directories
            allowed = False
            for source_path, _ in self.config_sources:
                try:
                    abs_path.relative_to(source_path)
                    allowed = True
                    break
                except ValueError:
                    continue

            if not allowed:
                logger.warning(f"Path is outside allowed directories: {path}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating path {path}: {e}")
            return False

    def _detect_file_format(self, path: Path) -> Optional[str]:
        """
        Detect the file format based on extension.

        Args:
            path: Path to check

        Returns:
            'json', 'yaml', or None if unsupported
        """
        suffix = path.suffix.lower()
        if suffix == ".json":
            return "json"
        elif suffix in [".yaml", ".yml"]:
            return "yaml"
        return None

    def list_config_sources(self) -> List[Dict[str, Any]]:
        """
        List all configuration source directories with context information.

        Returns:
            List of dictionaries containing:
                - path: The configuration directory path
                - context: 'project', 'workspace', or 'user'
                - project_name: Name of the project (if applicable)
                - workspace_name: Name of the workspace (if applicable)
        """
        sources = []

        for source_path, context_root in self.config_sources:
            # Determine context type
            if self.workspace_root and context_root == self.workspace_root:
                context = "workspace"
                project_name = None
            elif self.project_root and context_root == self.project_root:
                context = "project"
                project_name = self.project_name
            elif context_root == Path.home() / ".aurite":
                context = "user"
                project_name = None
            else:
                # It's a project within the workspace
                context = "project"
                project_name = context_root.name

            source_info = {
                "path": str(source_path),
                "context": context,
            }

            if project_name:
                source_info["project_name"] = project_name

            if self.workspace_name and context in ["project", "workspace"]:
                source_info["workspace_name"] = self.workspace_name

            sources.append(source_info)

        logger.debug(f"Listed {len(sources)} configuration sources")
        return sources

    def list_config_files(self, source_name: str) -> List[str]:
        """
        List all configuration files for a specific source.

        Args:
            source_name: The name of the source (e.g., 'workspace', 'project_bravo')

        Returns:
            A list of relative file paths.
        """
        # Build source mapping with better workspace handling
        source_map = {}
        for s in self.list_config_sources():
            # Map by project name if it's a project
            if s.get("project_name"):
                source_map[s["project_name"]] = s

            # Map by workspace name if it's a workspace context
            if s["context"] == "workspace" and s.get("workspace_name"):
                source_map[s["workspace_name"]] = s
                # Also map "workspace" as an alias
                source_map["workspace"] = s

        if source_name not in source_map:
            logger.warning(f"Source '{source_name}' not found.")
            return []

        source_info = source_map[source_name]
        source_path = Path(source_info["path"])
        source_path.parent if source_info["context"] == "project" else self.workspace_root

        if not source_path.is_dir():
            logger.warning(f"Config source path {source_path} is not a directory.")
            return []

        files = set()  # Use set to avoid duplicates
        for pattern in ["*.json", "*.yaml", "*.yml"]:
            for config_file in source_path.rglob(pattern):
                try:
                    # Use the source path as the base for the relative path
                    rel_path = config_file.relative_to(source_path)
                    files.add(str(rel_path))  # Set automatically deduplicates
                except ValueError:
                    # This can happen if the file is not under the source_path, which would be unexpected
                    logger.warning(f"File {config_file} is not relative to source path {source_path}")

        files_list = list(files)  # Convert back to list
        logger.debug(f"Found {len(files_list)} files in source '{source_name}'")
        return files_list

    def get_file_content(self, source_name: str, relative_path: str) -> Optional[str]:
        """
        Get the content of a specific configuration file.

        Args:
            source_name: The name of the source the file belongs to.
            relative_path: The relative path of the file within the source.

        Returns:
            The file content as a string, or None if not found or invalid.
        """
        # Build source mapping with better workspace handling
        source_map = {}
        for s in self.list_config_sources():
            # Map by project name if it's a project
            if s.get("project_name"):
                source_map[s["project_name"]] = s

            # Map by workspace name if it's a workspace context
            if s["context"] == "workspace" and s.get("workspace_name"):
                source_map[s["workspace_name"]] = s
                # Also map "workspace" as an alias
                source_map["workspace"] = s

        if source_name not in source_map:
            logger.warning(f"Source '{source_name}' not found for getting file content.")
            return None

        source_info = source_map[source_name]
        source_path = Path(source_info["path"])

        # Construct the full path and validate it
        full_path = source_path / relative_path
        if not self._validate_path(full_path):
            logger.warning(f"Invalid or unauthorized path requested: {full_path}")
            return None

        if not full_path.is_file():
            logger.warning(f"File not found at path: {full_path}")
            return None

        try:
            with full_path.open("r", encoding="utf-8") as f:
                return f.read()
        except IOError as e:
            logger.error(f"Could not read file {full_path}: {e}")
            return None

    def create_config_file(self, source_name: str, relative_path: str, content: str) -> bool:
        """
        Create a new configuration file.

        Args:
            source_name: The name of the source to create the file in.
            relative_path: The relative path for the new file.
            content: The content to write to the file.

        Returns:
            True if the file was created successfully, False otherwise.
        """
        # Build source mapping with better workspace handling
        source_map = {}
        for s in self.list_config_sources():
            # Map by project name if it's a project
            if s.get("project_name"):
                source_map[s["project_name"]] = s

            # Map by workspace name if it's a workspace context
            if s["context"] == "workspace" and s.get("workspace_name"):
                source_map[s["workspace_name"]] = s
                # Also map "workspace" as an alias
                source_map["workspace"] = s

        if source_name not in source_map:
            logger.warning(f"Source '{source_name}' not found for creating file.")
            return False

        source_info = source_map[source_name]
        source_path = Path(source_info["path"])

        # Construct the full path and validate it
        full_path = source_path / relative_path
        if not self._validate_path(full_path):
            logger.warning(f"Invalid or unauthorized path for file creation: {full_path}")
            return False

        if full_path.exists():
            logger.warning(f"File already exists at path: {full_path}")
            return False

        try:
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with full_path.open("w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Successfully created file: {full_path}")
            return True
        except IOError as e:
            logger.error(f"Could not create file {full_path}: {e}")
            return False

    def update_config_file(self, source_name: str, relative_path: str, content: str) -> bool:
        """
        Update an existing configuration file.

        Args:
            source_name: The name of the source where the file exists.
            relative_path: The relative path of the file to update.
            content: The new content to write to the file.

        Returns:
            True if the file was updated successfully, False otherwise.
        """
        # Build source mapping with better workspace handling
        source_map = {}
        for s in self.list_config_sources():
            # Map by project name if it's a project
            if s.get("project_name"):
                source_map[s["project_name"]] = s

            # Map by workspace name if it's a workspace context
            if s["context"] == "workspace" and s.get("workspace_name"):
                source_map[s["workspace_name"]] = s
                # Also map "workspace" as an alias
                source_map["workspace"] = s

        if source_name not in source_map:
            logger.warning(f"Source '{source_name}' not found for updating file.")
            return False

        source_info = source_map[source_name]
        source_path = Path(source_info["path"])

        full_path = source_path / relative_path
        if not self._validate_path(full_path) or not full_path.is_file():
            logger.warning(f"File not found or invalid path for update: {full_path}")
            return False

        try:
            with full_path.open("w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Successfully updated file: {full_path}")
            return True
        except IOError as e:
            logger.error(f"Could not update file {full_path}: {e}")
            return False

    def delete_config_file(self, source_name: str, relative_path: str) -> bool:
        """
        Delete an existing configuration file.

        Args:
            source_name: The name of the source where the file exists.
            relative_path: The relative path of the file to delete.

        Returns:
            True if the file was deleted successfully, False otherwise.
        """
        # Build source mapping with better workspace handling
        source_map = {}
        for s in self.list_config_sources():
            # Map by project name if it's a project
            if s.get("project_name"):
                source_map[s["project_name"]] = s

            # Map by workspace name if it's a workspace context
            if s["context"] == "workspace" and s.get("workspace_name"):
                source_map[s["workspace_name"]] = s
                # Also map "workspace" as an alias
                source_map["workspace"] = s

        if source_name not in source_map:
            logger.warning(f"Source '{source_name}' not found for deleting file.")
            return False

        source_info = source_map[source_name]
        source_path = Path(source_info["path"])

        full_path = source_path / relative_path
        if not self._validate_path(full_path) or not full_path.is_file():
            logger.warning(f"File not found or invalid path for deletion: {full_path}")
            return False

        try:
            full_path.unlink()
            logger.info(f"Successfully deleted file: {full_path}")
            return True
        except IOError as e:
            logger.error(f"Could not delete file {full_path}: {e}")
            return False

    def find_or_create_component_file(
        self,
        component_type: str,
        context_name: str,
        file_path: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Finds an existing config file or determines the path for a new one.

        Args:
            component_type: The type of component (e.g., 'agent').
            context_name: The name of the context ('workspace' or a project name).
            file_path: Optional user-provided file path.

        Returns:
            The absolute path to the target file, or None on error.
        """
        # Build source mapping with better workspace handling
        source_map = {}
        for s in self.list_config_sources():
            # Map by project name if it's a project
            if s.get("project_name"):
                source_map[s["project_name"]] = s

            # Map by workspace name if it's a workspace context
            if s["context"] == "workspace" and s.get("workspace_name"):
                source_map[s["workspace_name"]] = s
                # Also map "workspace" as an alias
                source_map["workspace"] = s

        if context_name not in source_map:
            logger.error(f"Context '{context_name}' not found. Available contexts: {list(source_map.keys())}")
            return None

        source_info = source_map[context_name]
        source_path = Path(source_info["path"])

        if file_path:
            if "/" not in file_path:
                # It's a filename, not a path
                # Search for this file in the given context
                existing_files = [f for f in self.list_config_files(context_name) if Path(f).name == file_path]
                if len(existing_files) > 1:
                    logger.error(f"Multiple files named '{file_path}' found in '{context_name}'.")
                    return None
                elif len(existing_files) == 1:
                    return source_path / existing_files[0]
                else:
                    # File not found, create it in a default location
                    return source_path / f"{component_type}s" / file_path
            else:
                # It's a relative path
                return source_path / file_path
        else:
            # No file_path provided, use default
            return source_path / f"{component_type}s" / f"{component_type}s.json"

    def add_component_to_file(self, file_path: Path, component_config: Dict[str, Any]) -> bool:
        """
        Adds a new component to a configuration file.

        Args:
            file_path: The absolute path to the file.
            component_config: The configuration of the component to add.

        Returns:
            True if the component was added successfully, False otherwise.
        """
        file_format = self._detect_file_format(file_path)
        if not file_format:
            logger.error(f"Unsupported file format for {file_path}")
            return False

        try:
            if file_path.exists():
                with file_path.open("r", encoding="utf-8") as f:
                    if file_format == "json":
                        content = json.load(f)
                    else:
                        content = yaml.safe_load(f)
                if not isinstance(content, list):
                    logger.error(f"File {file_path} does not contain a list of components.")
                    return False
            else:
                content = []

            # Check for existing component with the same name
            component_name = component_config.get("name")
            if file_path.exists():
                if any(c.get("name") == component_name for c in content):
                    logger.error(f"Component '{component_name}' already exists in {file_path}.")
                    return False

            content.append(component_config)

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with file_path.open("w", encoding="utf-8") as f:
                if file_format == "json":
                    json.dump(content, f, indent=2, ensure_ascii=False)
                else:
                    yaml.safe_dump(content, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Added component '{component_name}' to {file_path}")
            return True

        except (IOError, json.JSONDecodeError, yaml.YAMLError) as e:
            logger.error(f"Failed to add component to {file_path}: {e}")
            return False
