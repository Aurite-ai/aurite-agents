from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dummy")

@mcp.tool()
def get_address(name: str) -> str:
    """Get the address of a person by name
    
    Args:
        name: The name of the person
        
    Returns:
        The address as a string
    """
    addresses = {
        "Alice": "765 Bakers Ave",
        "Bob": "112 Fifth Street",
        "Charlie": "898 Beale Street"
    }

    if name in addresses:
        return addresses[name]
    
    return "454 Mission Street"

@mcp.tool()
def calculate_distance(address1: str, address2: str) -> float:
    """Calculate the distance in miles between two addresses
    
    Args:
        address1: The first address
        address2: The second address
        
    Returns:
        The distance between them in miles
    """
    return 5.4

if __name__ == "__main__":
    mcp.run(transport="stdio")
