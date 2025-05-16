"""MCP server for reading files"""

import os
from pathlib import Path  # Added Path import

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
# from aurite.config import PROJECT_ROOT_DIR # PROJECT_ROOT_DIR is no longer available globally

load_dotenv()

mcp = FastMCP("file")

FILES = [
    "README.md",
    "docs/layers/0_frontends.md",
    "docs/layers/1_entrypoints.md",
    "docs/layers/2_orchestration.md",
    "docs/layers/3_host.md",
]


@mcp.tool()
def read_file(filepath: str) -> str:
    """Read a file and return the string content

    Args:
        filepath: The path to the file to be read. Must be on the list of allowed filepaths (use list_filepaths())
    """
    if filepath not in FILES:
        return "Unauthorized to read file"

    # Path resolution needs to be re-evaluated for this server in a packaged context.
    # For now, let's assume files are relative to CWD or absolute paths if PROJECT_ROOT_DIR is not used.
    # This server might need a configurable base path if used in a packaged environment.
    # Temporarily, this will likely only work if the server is run from the old project root.
    # A proper fix would involve passing a base_path or using a known location.
    # For now, to prevent error, we'll try a direct path, which might fail if not run from repo root.
    # A better solution for a packaged server would be to serve files from importlib.resources
    # if they are packaged, or require absolute paths / user-project relative paths.

    # Tentative change: make it relative to CWD for now, or expect absolute.
    # This server's utility in a packaged context is limited without further refactoring.
    target_path = Path(filepath)  # Assume filepath could be absolute or relative to CWD
    if not target_path.is_absolute():
        # This is a placeholder; a real server would need a defined content root.
        # For now, let's assume it's relative to where the server is run.
        # Or, if this server is only for dev, this logic might be fine if run from repo root.
        # Given we are removing PROJECT_ROOT_DIR, this part needs a decision.
        # For now, let's make it try to resolve from CWD.
        target_path = Path.cwd() / filepath

    if os.path.exists(target_path):  # Use target_path
        with open(target_path, "r") as file:  # Use target_path
            return file.read()
    else:
        return "File not found"


@mcp.tool()
def read_file_by_index(index: int) -> str:
    """Read a file by index and return the string content

    Args:
        index: The index of the file to be read. Must be on the list of allowed filepaths (use list_filepaths())
    """

    if index >= len(FILES) or index < 0:
        return "Invalid index"

    return read_file(FILES[index])


@mcp.tool()
def list_filepaths() -> list[str]:
    """Return a list of file paths to documentation files. They will be of the format 'index: filepath'"""

    file_str = "\n".join([f"{i}: {FILES[i]}" for i in range(len(FILES))])

    return file_str


if __name__ == "__main__":
    mcp.run(transport="stdio")
