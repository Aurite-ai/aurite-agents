import asyncio
from src.host.host import MCPHost, HostConfig

async def test_host_memory():
    host = MCPHost(HostConfig(clients=[]))
    
    try:
        await host.initialize()
        
        print("inserting memory")
        await host.add_memories("my favorite color is yellow", user_id="test")
        
        print("reading memory")
        results = await host.search_memories("what is my favorite color?", user_id="test", limit=5)
        
        print(results)
    finally:
        await host.shutdown()
        
        
async def main():
    """Run all tests"""
    await test_host_memory()

if __name__ == "__main__":
    asyncio.run(main())