import os

from mem0 import MemoryClient
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv


load_dotenv()

mcp = FastMCP("memory")

os.environ["OPENAI_API_KEY"] = os.getenv("MEM0_API_KEY")

m = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

user_id = "fd9c8ecb-4dce-42af-a76a-bfa6ff43c889"
app_id = "ebsFWnezbMcIyXRag"

results = m.get_all(user_id=user_id, app_id=app_id)

print(results)
