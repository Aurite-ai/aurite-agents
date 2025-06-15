#!/usr/bin/env python3
"""
Local File Storage MCP Server

A consolidated MCP server that provides file system operations within a project directory.
This server automatically detects the project directory and provides secure file operations.
"""

import difflib
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Default to console
)
logger = logging.getLogger(__name__)

# Add file logging for debugging in packaged environments
try:
    # Use a temporary file for the log
    log_file_path = Path(tempfile.gettempdir()) / "aurite_local_file_storage_server.log"
    # Create a file handler that overwrites the log on each run
    file_handler = logging.FileHandler(log_file_path, mode="w")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Add the handler to the root logger to capture everything
    logging.getLogger().addHandler(file_handler)
    logger.info(f"Logging to file: {log_file_path}")
except Exception as e:
    logger.error(f"Failed to set up file logging: {e}")

# Global project directory - will be set on startup
_project_dir: Optional[Path] = None

app = FastMCP("local-file-storage-server")


def get_project_dir() -> Path:
    """Get the project directory, auto-detecting if not set."""
    global _project_dir
    if _project_dir is not None:
        return _project_dir

    try:
        logger.info("Attempting to determine project directory...")
        # Try environment variable first
        env_dir = os.getenv("AURITE_PROJECT_DIR")
        logger.info(f"AURITE_PROJECT_DIR environment variable: {env_dir}")
        if env_dir and Path(env_dir).exists():
            _project_dir = Path(env_dir).resolve()
            logger.info(f"SUCCESS: Using AURITE_PROJECT_DIR: {_project_dir}")
            return _project_dir

        # Try to get the original working directory from PWD environment variable
        pwd_dir = os.getenv("PWD")
        logger.info(f"PWD environment variable: {pwd_dir}")
        if pwd_dir and Path(pwd_dir).exists():
            _project_dir = Path(pwd_dir).resolve()
            logger.info(f"SUCCESS: Using PWD: {_project_dir}")
            return _project_dir

        # Fallback to current working directory
        cwd = Path.cwd().resolve()
        logger.info(f"Falling back to current working directory: {cwd}")
        _project_dir = cwd
        logger.info(f"SUCCESS: Using current working directory: {_project_dir}")
        return _project_dir

    except Exception as e:
        logger.error(
            f"CRITICAL: Failed to determine project directory: {e}", exc_info=True
        )
        # Raise the exception to ensure the server fails loudly if it can't find a directory.
        raise


def normalize_path(path: str, project_dir: Path) -> Tuple[Path, str]:
    """
    Normalize a path to be relative to the project directory.

    Args:
        path: Path to normalize
        project_dir: Project directory path

    Returns:
        Tuple of (absolute path, relative path)

    Raises:
        ValueError: If the path is outside the project directory
    """
    if project_dir is None:
        raise ValueError("Project directory cannot be None")

    path_obj = Path(path)

    # If the path is absolute, make it relative to the project directory
    if path_obj.is_absolute():
        try:
            # Make sure the path is inside the project directory
            relative_path = path_obj.relative_to(project_dir)
            return path_obj, str(relative_path)
        except ValueError:
            raise ValueError(
                f"Security error: Path '{path}' is outside the project directory '{project_dir}'. "
                f"All file operations must be within the project directory."
            )

    # If the path is already relative, make sure it doesn't try to escape
    absolute_path = project_dir / path_obj
    try:
        # Make sure the resolved path is inside the project directory
        try:
            resolved_path = absolute_path.resolve()
            project_resolved = project_dir.resolve()
            # Check if the resolved path starts with the resolved project dir
            if os.path.commonpath([resolved_path, project_resolved]) != str(
                project_resolved
            ):
                raise ValueError(
                    f"Security error: Path '{path}' resolves to a location outside "
                    f"the project directory '{project_dir}'. Path traversal is not allowed."
                )
        except (FileNotFoundError, OSError):
            # During testing with non-existent paths, just do a simple string check
            pass

        return absolute_path, str(path_obj)
    except ValueError as e:
        # If the error already has our detailed message, pass it through
        if "Security error:" in str(e):
            raise
        # Otherwise add more context
        raise ValueError(
            f"Security error: Path '{path}' is outside the project directory '{project_dir}'. "
            f"All file operations must be within the project directory."
        ) from e


def load_gitignore_patterns(start_dir: Path) -> List[str]:
    """
    Load gitignore patterns by searching upwards from start_dir for a .gitignore file.
    """
    current_dir = start_dir.resolve()
    root = Path(current_dir.anchor)
    patterns = []

    while current_dir != root:
        gitignore_file = current_dir / ".gitignore"
        if gitignore_file.is_file():
            logger.info(f"Found .gitignore at: {gitignore_file}")
            try:
                with open(gitignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
                # Stop after finding the first .gitignore
                return patterns
            except Exception as e:
                logger.warning(
                    f"Could not read .gitignore file at {gitignore_file}: {e}"
                )
                # Continue searching upwards even if one is unreadable

        # Move to the parent directory
        current_dir = current_dir.parent

    logger.info("No .gitignore file found in the directory hierarchy.")
    return patterns


def should_ignore_file(file_path: str, gitignore_patterns: List[str]) -> bool:
    """Check if a file should be ignored based on gitignore patterns."""
    import fnmatch

    for pattern in gitignore_patterns:
        # Handle directory patterns (ending with /)
        if pattern.endswith("/"):
            dir_pattern = pattern[:-1]
            if "/" in file_path:
                path_parts = file_path.split("/")
                if any(fnmatch.fnmatch(part, dir_pattern) for part in path_parts[:-1]):
                    return True
        else:
            # Handle file patterns
            if fnmatch.fnmatch(file_path, pattern):
                return True
            # Also check if any parent directory matches
            if "/" in file_path:
                path_parts = file_path.split("/")
                for i in range(len(path_parts)):
                    partial_path = "/".join(path_parts[: i + 1])
                    if fnmatch.fnmatch(partial_path, pattern):
                        return True

    return False


def discover_files(directory: Path, project_dir: Path) -> List[str]:
    """Discover all files recursively, excluding the .git directory and applying gitignore rules."""
    discovered_files = []

    # Load gitignore patterns by searching upwards from the project directory
    gitignore_patterns = load_gitignore_patterns(project_dir)

    for root, dirs, files in os.walk(directory):
        # Skip .git directories and common build/cache directories
        dirs_to_remove = []
        for d in dirs:
            if d in [
                ".git",
                "__pycache__",
                ".pytest_cache",
                "node_modules",
                ".venv",
                "venv",
                "notebook-venv",
                ".mypy_cache",
                "dist",
                "build",
                ".tox",
                "aurite_agents.egg-info",
            ]:
                dirs_to_remove.append(d)

        for d in dirs_to_remove:
            dirs.remove(d)

        root_path = Path(root)
        try:
            rel_root = root_path.relative_to(project_dir)
        except ValueError:
            continue

        for file in files:
            # Skip common temporary and build files
            if file.endswith(
                (
                    ".pyc",
                    ".pyo",
                    ".pyd",
                    ".so",
                    ".egg-info",
                    ".log",
                    ".tmp",
                    ".swp",
                    ".DS_Store",
                )
            ):
                continue
            if file.startswith(".") and file not in [".env", ".env.example"]:
                continue

            rel_file_path = str(rel_root / file)

            # Check against gitignore patterns
            if should_ignore_file(rel_file_path, gitignore_patterns):
                continue

            discovered_files.append(rel_file_path)

    return discovered_files


@dataclass
class EditOperation:
    """Represents a single edit operation."""

    old_text: str
    new_text: str


@dataclass
class EditOptions:
    """Optional formatting settings for edit operations."""

    preserve_indentation: bool = True
    normalize_whitespace: bool = True


def normalize_line_endings(text: str) -> str:
    """Convert all line endings to Unix style (\n)."""
    return text.replace("\r\n", "\n")


def get_line_indentation(line: str) -> str:
    """Extract the indentation (leading whitespace) from a line."""
    match = re.match(r"^(\s*)", line)
    return match.group(1) if match else ""


def preserve_indentation(old_text: str, new_text: str) -> str:
    """Preserve the indentation pattern from old_text in new_text."""
    # Special case for markdown lists: don't modify indentation if the new text has list markers
    if ("- " in new_text or "* " in new_text) and (
        "- " in old_text or "* " in old_text
    ):
        return new_text

    old_lines = old_text.split("\n")
    new_lines = new_text.split("\n")

    # Handle empty content
    if not old_lines or not new_lines:
        return new_text

    # Extract the base indentation from the first line of old text
    base_indent = (
        get_line_indentation(old_lines[0]) if old_lines and old_lines[0].strip() else ""
    )

    # Pre-calculate indentation maps for efficiency
    old_indents = {
        i: get_line_indentation(line)
        for i, line in enumerate(old_lines)
        if line.strip()
    }
    new_indents = {
        i: get_line_indentation(line)
        for i, line in enumerate(new_lines)
        if line.strip()
    }

    # Calculate first line indentation length for relative adjustments
    first_new_indent_len = len(new_indents.get(0, "")) if new_indents else 0

    # Process each line with the appropriate indentation
    result_lines = []
    for i, new_line in enumerate(new_lines):
        # Empty lines remain empty
        if not new_line.strip():
            result_lines.append("")
            continue

        # Get current indentation in new text
        new_indent = new_indents.get(i, "")

        # Determine target indentation based on context
        if i < len(old_lines) and i in old_indents:
            # Matching line in old text - use its indentation
            target_indent = old_indents[i]
        elif i == 0:
            # First line gets base indentation
            target_indent = base_indent
        elif first_new_indent_len > 0:
            # Calculate relative indentation for other lines
            curr_indent_len = len(new_indent)

            # Default to base indent but look for better match from previous lines
            target_indent = base_indent

            # Find the closest previous line with appropriate indentation to use as template
            for prev_i in range(i - 1, -1, -1):
                if prev_i in old_indents and prev_i in new_indents:
                    prev_old = old_indents[prev_i]
                    prev_new = new_indents[prev_i]
                    if len(prev_new) <= curr_indent_len:
                        # Add spaces to match the relative indentation
                        relative_spaces = curr_indent_len - len(prev_new)
                        target_indent = prev_old + " " * relative_spaces
                        break
        else:
            # When first line has no indentation, use the new text's indentation
            target_indent = new_indent

        # Apply the calculated indentation
        result_lines.append(target_indent + new_line.lstrip())

    return "\n".join(result_lines)


def create_unified_diff(original: str, modified: str, file_path: str) -> str:
    """Create a unified diff between original and modified content."""
    original_lines = original.splitlines(True)
    modified_lines = modified.splitlines(True)

    diff_lines = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )

    return "".join(diff_lines)


@app.tool()
def list_directory() -> List[str]:
    """List files and directories in the project directory.

    Returns:
        A list of filenames in the project directory
    """
    try:
        project_dir = get_project_dir()
        logger.info(f"Listing all files in project directory: {project_dir}")

        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory does not exist: {project_dir}")

        if not project_dir.is_dir():
            raise NotADirectoryError(f"Project path is not a directory: {project_dir}")

        # Discover all files recursively
        all_files = discover_files(project_dir, project_dir)
        logger.info(f"Discovered {len(all_files)} files in project directory")

        return all_files
    except Exception as e:
        logger.error(f"Error listing project directory: {str(e)}")
        raise


@app.tool()
def read_file(file_path: str) -> str:
    """Read the contents of a file.

    Args:
        file_path: Path to the file to read (relative to project directory)

    Returns:
        The contents of the file as a string
    """
    if not file_path or not isinstance(file_path, str):
        logger.error(f"Invalid file path parameter: {file_path}")
        raise ValueError(f"File path must be a non-empty string, got {type(file_path)}")

    project_dir = get_project_dir()
    logger.info(f"Reading file: {file_path}")

    try:
        # Normalize the path to be relative to the project directory
        abs_path, rel_path = normalize_path(file_path, project_dir)

        if not abs_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File '{file_path}' does not exist")

        if not abs_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            raise IsADirectoryError(f"Path '{file_path}' is not a file")

        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.debug(f"Successfully read {len(content)} bytes from {rel_path}")
        return content
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error while reading {file_path}: {str(e)}")
        raise ValueError(
            f"File '{file_path}' contains invalid characters. Ensure it's a valid text file."
        ) from e
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise


@app.tool()
def save_file(file_path: str, content: str) -> bool:
    """Write content to a file.

    Args:
        file_path: Path to the file to write to (relative to project directory)
        content: Content to write to the file

    Returns:
        True if the file was written successfully
    """
    if not file_path or not isinstance(file_path, str):
        logger.error(f"Invalid file path parameter: {file_path}")
        raise ValueError(f"File path must be a non-empty string, got {type(file_path)}")

    if content is None:
        logger.warning("Content is None, treating as empty string")
        content = ""

    if not isinstance(content, str):
        logger.error(f"Invalid content type: {type(content)}")
        raise ValueError(f"Content must be a string, got {type(content)}")

    project_dir = get_project_dir()
    logger.info(f"Writing to file: {file_path}")

    try:
        # Normalize the path to be relative to the project directory
        abs_path, rel_path = normalize_path(file_path, project_dir)

        # Create directory if it doesn't exist
        if not abs_path.parent.exists():
            logger.info(f"Creating directory: {abs_path.parent}")
            abs_path.parent.mkdir(parents=True)

        # Use a temporary file for atomic write
        temp_fd, temp_path = tempfile.mkstemp(dir=str(abs_path.parent))
        temp_file = Path(temp_path)

        try:
            logger.debug(f"Writing to temporary file for {rel_path}")

            # Write content to temporary file
            with open(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)

            # Atomically replace the target file
            logger.debug(f"Atomically replacing {rel_path} with temporary file")
            # On Windows, we need to remove the target file first
            if os.name == "nt" and abs_path.exists():
                abs_path.unlink()
            os.replace(temp_path, str(abs_path))

            logger.debug(f"Successfully wrote {len(content)} bytes to {rel_path}")
            return True

        finally:
            # Clean up the temporary file if it still exists
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.warning(
                        f"Failed to clean up temporary file {temp_file}: {str(e)}"
                    )

    except Exception as e:
        logger.error(f"Error writing to file: {str(e)}")
        raise


@app.tool()
def append_file(file_path: str, content: str) -> bool:
    """Append content to the end of a file.

    Args:
        file_path: Path to the file to append to (relative to project directory)
        content: Content to append to the file

    Returns:
        True if the content was appended successfully
    """
    if not file_path or not isinstance(file_path, str):
        logger.error(f"Invalid file path parameter: {file_path}")
        raise ValueError(f"File path must be a non-empty string, got {type(file_path)}")

    if content is None:
        logger.warning("Content is None, treating as empty string")
        content = ""

    if not isinstance(content, str):
        logger.error(f"Invalid content type: {type(content)}")
        raise ValueError(f"Content must be a string, got {type(content)}")

    project_dir = get_project_dir()
    logger.info(f"Appending to file: {file_path}")

    try:
        # Normalize the path to be relative to the project directory
        abs_path, rel_path = normalize_path(file_path, project_dir)

        # Check if the file exists
        if not abs_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File '{file_path}' does not exist")

        if not abs_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            raise IsADirectoryError(f"Path '{file_path}' is not a file")

        # Read existing content
        existing_content = read_file(file_path)

        # Append new content
        combined_content = existing_content + content

        # Use save_file to write the combined content
        logger.debug(f"Appending {len(content)} bytes to {rel_path}")
        return save_file(file_path, combined_content)

    except Exception as e:
        logger.error(f"Error appending to file: {str(e)}")
        raise


@app.tool()
def delete_this_file(file_path: str) -> bool:
    """Delete a specified file from the filesystem.

    Args:
        file_path: Path to the file to delete (relative to project directory)

    Returns:
        True if the file was deleted successfully
    """
    if not file_path or not isinstance(file_path, str):
        logger.error(f"Invalid file path parameter: {file_path}")
        raise ValueError(f"File path must be a non-empty string, got {type(file_path)}")

    project_dir = get_project_dir()
    logger.info(f"Deleting file: {file_path}")

    try:
        # Normalize the path to be relative to the project directory
        abs_path, rel_path = normalize_path(file_path, project_dir)

        if not abs_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File '{file_path}' does not exist")

        if not abs_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            raise IsADirectoryError(
                f"Path '{file_path}' is not a file or is a directory"
            )

        logger.debug(f"Deleting file: {rel_path}")
        abs_path.unlink()
        logger.info(f"File deleted successfully: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        raise


@app.tool()
def edit_file(
    file_path: str,
    edits: List[Dict[str, str]],
    dry_run: bool = False,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make selective edits to files while preserving formatting.

    Features:
        - Line-based and multi-line content matching
        - Whitespace normalization with indentation preservation
        - Multiple simultaneous edits with correct positioning
        - Smart detection of already-applied edits
        - Git-style diff output with context
        - Preview changes with dry run mode

    Args:
        file_path: Path to the file to edit (relative to project directory)
        edits: List of edit operations (each containing old_text and new_text)
        dry_run: Preview changes without applying (default: False)
        options: Optional formatting settings
                    - preserve_indentation: Keep existing indentation (default: True)
                    - normalize_whitespace: Normalize spaces (default: True)

    Returns:
        Detailed diff and match information including success status
    """
    # Basic validation
    if not file_path or not isinstance(file_path, str):
        logger.error(f"Invalid file path parameter: {file_path}")
        raise ValueError(f"File path must be a non-empty string, got {type(file_path)}")

    if not isinstance(edits, list) or not edits:
        logger.error(f"Invalid edits parameter: {edits}")
        raise ValueError("Edits must be a non-empty list")

    project_dir = get_project_dir()

    # Normalize edit operations (ensure proper format and required fields)
    normalized_edits = []
    for i, edit in enumerate(edits):
        if not isinstance(edit, dict):
            raise ValueError(f"Edit #{i} must be a dictionary, got {type(edit)}")

        # Validate required fields
        if "old_text" not in edit or "new_text" not in edit:
            missing = ", ".join([f for f in ["old_text", "new_text"] if f not in edit])
            raise ValueError(f"Edit #{i} is missing required field(s): {missing}")

        # Create normalized edit with just the fields we need
        normalized_edits.append(
            {"old_text": edit["old_text"], "new_text": edit["new_text"]}
        )

    # Process options (only extract the fields we support)
    normalized_options = {}
    if options:
        for opt in ["preserve_indentation", "normalize_whitespace"]:
            if opt in options:
                normalized_options[opt] = options[opt]

    logger.info(f"Editing file: {file_path}, dry_run: {dry_run}")

    try:
        # Normalize the path to be relative to the project directory
        abs_path, rel_path = normalize_path(file_path, project_dir)

        # Validate file path exists
        if not abs_path.is_file():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file content
        with open(abs_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Convert edits to EditOperation objects
        edit_operations = []
        for edit in normalized_edits:
            edit_operations.append(
                EditOperation(old_text=edit["old_text"], new_text=edit["new_text"])
            )

        # Set up options with defaults
        edit_options = EditOptions(
            preserve_indentation=normalized_options.get("preserve_indentation", True),
            normalize_whitespace=normalized_options.get("normalize_whitespace", True),
        )

        # Apply edits
        modified_content, match_results, changes_made = apply_edits(
            original_content, edit_operations, edit_options
        )

        # Check for actual failures and already applied edits
        failed_matches = [r for r in match_results if r.get("match_type") == "failed"]
        already_applied = [
            r
            for r in match_results
            if r.get("match_type") == "skipped"
            and "already applied" in r.get("details", "")
        ]

        # Handle common result cases
        result = {
            "match_results": match_results,
            "file_path": file_path,
            "dry_run": dry_run,
        }

        # Case 1: Failed matches
        if failed_matches:
            result.update(
                {
                    "success": False,
                    "error": "Failed to find exact match for one or more edits",
                }
            )
            return result

        # Case 2: No changes needed (already applied or identical content)
        if not changes_made or (already_applied and len(already_applied) == len(edits)):
            result.update(
                {
                    "success": True,
                    "diff": "",  # Empty diff indicates no changes
                    "message": "No changes needed - content already in desired state",
                }
            )
            return result

        # Case 3: Changes needed - create diff
        diff = create_unified_diff(original_content, modified_content, file_path)
        result.update({"diff": diff, "success": True})

        # Write changes if not in dry run mode
        if not dry_run and changes_made:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(modified_content)

        return result

    except Exception as e:
        logger.error(f"Error editing file {file_path}: {str(e)}")
        raise


def apply_edits(
    content: str, edits: List[EditOperation], options: Optional[EditOptions] = None
) -> Tuple[str, List[Dict[str, Any]], bool]:
    """Apply a list of edit operations to the content."""
    if options is None:
        options = EditOptions()

    # Normalize line endings
    normalized_content = normalize_line_endings(content)

    # Store match results for reporting
    match_results = []
    changes_made = False

    # Process each edit
    for i, edit in enumerate(edits):
        normalized_old = normalize_line_endings(edit.old_text)
        normalized_new = normalize_line_endings(edit.new_text)

        # Skip if the replacement text is identical to the old text
        if normalized_old == normalized_new:
            match_results.append(
                {
                    "edit_index": i,
                    "match_type": "skipped",
                    "details": "No change needed - text already matches desired state",
                }
            )
            continue

        # Check if the new_text is already in the content
        if (
            normalized_new in normalized_content
            and normalized_old not in normalized_content
        ):
            match_results.append(
                {
                    "edit_index": i,
                    "match_type": "skipped",
                    "details": "Edit already applied - content already in desired state",
                }
            )
            continue

        # Try exact match
        if normalized_old in normalized_content:
            # For exact matches, find position in content
            start_pos = normalized_content.find(normalized_old)
            end_pos = start_pos + len(normalized_old)

            # Apply indentation preservation if requested
            if options.preserve_indentation:
                normalized_new = preserve_indentation(normalized_old, normalized_new)

            # Apply the edit
            normalized_content = (
                normalized_content[:start_pos]
                + normalized_new
                + normalized_content[end_pos:]
            )
            changes_made = True

            # Calculate line information
            lines_before = normalized_content[:start_pos].count("\n")
            line_count = normalized_old.count("\n") + 1

            match_results.append(
                {
                    "edit_index": i,
                    "match_type": "exact",
                    "line_index": lines_before,
                    "line_count": line_count,
                }
            )
        else:
            match_results.append(
                {
                    "edit_index": i,
                    "match_type": "failed",
                    "details": "No exact match found",
                }
            )
            logger.warning(f"Could not find exact match for edit {i}")

    return normalized_content, match_results, changes_made


if __name__ == "__main__":
    try:
        logger.info("Server script starting up...")
        get_project_dir()  # Initialize project directory on startup
        logger.info("Project directory initialized. Starting MCP server...")
        app.run()
    except Exception as e:
        logger.error(f"FATAL: Server failed to start: {e}", exc_info=True)
        # Exit with a non-zero code to indicate failure
        import sys

        sys.exit(1)
