from mem0 import Memory
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("memory")

m = Memory()

@mcp.tool()
def add_memories(memory_str: str, user_id: str) -> str:
    """Extract facts from a string and store them as memories

    Args:
        memory_str: The string containing one or more memories to store
        user_id: The id of the user to associate the memories with
    """
    m.add(memory_str, user_id)
    
    return "Memories added successfully"
    
@mcp.tool()
def search_memories(query: str, user_id: str, limit: int = 5) -> list[str]:
    """Search for memories relevant to a query
    
    Args:
        query: The query to search with
        user_id: The id of the user whose associated memories we will search
        limit: Max memories to return. Default 5
        
    Returns:
        List of memory strings
    """
    results = m.search(query, user_id).get("results", [])
    
    memories = []
    
    for mem in results[:limit]:
        memories.append(mem.get("memory", ""))
        
    return memories

if __name__ == "__main__":
    mcp.run(transport='stdio')