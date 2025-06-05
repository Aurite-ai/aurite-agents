import os

from urllib.parse import unquote_plus
from mem0 import MemoryClient
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv


load_dotenv()

mcp = FastMCP("memory")

os.environ["OPENAI_API_KEY"] = os.getenv("MEM0_API_KEY")

m = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

app_id = "ebsFWnezbMcIyXRag"


@mcp.tool()
def add_memories(memory_str: str, user_id: str, prompt: str | None = None) -> str:
    """Extract facts from a string and store them as memories

    Args:
        memory_str: The string containing one or more memories to store
        user_id: The id of the user to associate the memories with
        prompt: Optional, a prompt to guide how memories are stored
    """

    m.add(memory_str, user_id, prompt=prompt)

    return "Memories added successfully"


# @mcp.resource("mem0://search/{user_id}/{query}/{limit}")
# keeping as tool for now because it is easier to access in host.py
@mcp.tool()
def search_memories(query: str, user_id: str, limit: int = 5) -> list[str]:
    """Search for memories relevant to a query

    Args:
        query: The query to search with (URL-encoded)
        user_id: The id of the user whose associated memories we will search
        limit: Max memories to return. Default 5

    Returns:
        List of memory strings
    """
    query = unquote_plus(query)

    results = m.search(query, user_id=user_id, app_id=app_id)

    memories = []

    for mem in results[:limit]:
        memories.append(mem.get("memory", ""))

    return memories


@mcp.tool()
def get_all_memories(user_id: str) -> list[str]:
    """Get all memories of a user

    Args:
        user_id: The id of the user

    Returns:
        List of memory strings
    """

    results = m.get_all(user_id=user_id, app_id=app_id)

    memories = []

    for mem in results:
        memories.append(mem.get("memory", ""))

    return memories


@mcp.tool()
def delete_all_memories(user_id: str):
    """Delete all memories of a user

    Args:
        user_id: The id of the user
    """

    m.delete_all(user_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
