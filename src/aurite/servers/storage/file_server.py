"""MCP server for reading files"""
import os

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from aurite.config import PROJECT_ROOT_DIR

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

    if os.path.exists(PROJECT_ROOT_DIR / filepath):
        with open(PROJECT_ROOT_DIR / filepath, "r") as file:
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
