"""
FileManager class for handling configuration file operations.

This module provides a dedicated class for managing file operations related to
configuration files, including listing sources, reading/writing files, and
managing component storage.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
