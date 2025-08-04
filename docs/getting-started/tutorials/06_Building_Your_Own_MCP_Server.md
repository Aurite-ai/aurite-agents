# Tutorial: Building Your Own MCP Server

**Welcome to the advanced tutorial on creating custom MCP servers!** This tutorial builds on everything you've learned about agents, tools, and project configuration. Now you'll learn how to extend the Aurite framework by creating your own Model Context Protocol (MCP) server that provides custom tools to your agents.

**Learning Objectives:**

**Primary Goal: Understanding MCP and Building a Custom Server**

- Understand what the Model Context Protocol (MCP) is and how it enables tool integration.
- Learn the structure and components of an MCP server.
- Build a functional MCP server from scratch that provides custom tools.
- Test your MCP server to ensure it works correctly.

**Secondary Goal: Integration with Aurite Framework**

- Learn how to register your custom MCP server as a `ClientConfig` in your Aurite project.
- Create an agent that uses your custom MCP server.
- Successfully run an agent that uses your custom tools.

---

## Prerequisites

⚠️ **Before you begin this tutorial, please ensure you have completed:**

- All previous tutorials, especially "[Understanding Projects](07_Understanding_Projects.md)".
- A working Aurite project set up locally.
- Python 3.12+ installed and configured.
- Basic understanding of Python programming.
- Familiarity with JSON configuration files.

---

## Part 1: Understanding the Model Context Protocol (MCP)

### What is MCP?

The **Model Context Protocol (MCP)** is a standardized way for AI applications to connect with external data sources and tools. Think of it as a bridge that allows your AI agents to interact with the outside world.

**Key Concepts:**

- **MCP Server**: A program that provides tools, resources, or prompts to AI agents.
- **MCP Client**: The AI application (like Aurite) that connects to and uses MCP servers.
- **Tools**: Functions that agents can call to perform actions (e.g., search the web, save files).

### How MCP Works in Aurite

1.  **MCP Servers** run as separate processes and provide tools.
2.  **`ClientConfig`** objects in your `aurite_config.json` define how to connect to these servers.
3.  **Agents** specify which MCP servers they can use via the `mcp_servers` field in their configuration.
4.  When an agent runs, Aurite connects to the specified servers and makes their tools available.

For this tutorial, we'll create a server that communicates via **`stdio`** (standard input/output), as it's the most straightforward method for custom Python scripts.

---

## Part 2: Building the MCP Server Step-by-Step

We will create a simple **Task Management Server** that stores tasks in memory.

### Step 1: Create the Project Directory and Server File

First, let's set up the file structure. Inside your Aurite project folder (e.g., `my_first_aurite_project`), create a new directory called `mcp_servers`.

Inside this new `mcp_servers` directory, create a file named `task_manager_server.py`.

Your project structure should look like this:

```
my_first_aurite_project/
├── mcp_servers/
│   └── task_manager_server.py
├── aurite_config.json
└── run_example_project.py
```

### Step 2: Create the Server Skeleton

Open `task_manager_server.py` and add the following boilerplate code. This sets up the basic server structure.

```python
#!/usr/bin/env python3
"""
A simple Task Management MCP Server that stores tasks in memory.
"""
import logging
from typing import Dict, Any, List

# MCP imports
from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance
mcp = FastMCP("In-Memory Task Manager")

# In-memory storage for our tasks
tasks: List[Dict[str, Any]] = []

# --- Tool implementations will go here ---

# Allow direct execution of the server
if __name__ == "__main__":
    mcp.run()
```

### Step 3: Add the `create_task` Tool

Now, let's add our first tool. This function will add a new task to our in-memory `tasks` list. Add the following code to `task_manager_server.py` where the comment `--- Tool implementations will go here ---` is.

```python
@mcp.tool()
async def create_task(title: str, priority: str = "medium") -> Dict[str, Any]:
    """
    Create a new task.

    Args:
        title: The title of the task (required).
        priority: Priority level (low, medium, high).

    Returns:
        A dictionary with the created task information.
    """
    task_id = len(tasks)  # Use the list index as a simple ID
    new_task = {
        "id": task_id,
        "title": title,
        "priority": priority,
        "completed": False,
    }
    tasks.append(new_task)
    logger.info(f"Created task: {new_task}")
    return {"success": True, "task": new_task}
```

The `@mcp.tool()` decorator automatically registers this function as a tool that agents can call.

### Step 4: Add the `list_tasks` Tool

Next, let's add a tool to view the tasks. Add this code below the `create_task` function.

```python
@mcp.tool()
async def list_tasks() -> Dict[str, Any]:
    """
    List all tasks.

    Returns:
        A dictionary containing the list of tasks.
    """
    logger.info(f"Listing {len(tasks)} tasks.")
    return {"success": True, "tasks": tasks}
```

### Step 5: Make the Server Executable

On macOS and Linux, you need to make the script executable. Open your terminal, navigate to the `mcp_servers` directory, and run:

```bash
chmod +x task_manager_server.py
```

(Windows users can skip this step.)

---

## Part 3: Testing Your MCP Server

Before integrating with Aurite, let's write a small script to test our server directly.

1.  **Create a Test Script:** In your project's root directory (e.g., `my_first_aurite_project`), create a new file named `test_mcp.py`.

2.  **Add Test Code:** Add the following code to `test_mcp.py`. This script will call your server's tools and print the results.

    ```python
    import asyncio
    import json
    from mcp_servers.task_manager_server import mcp

    async def test_tools():
        """Test the tools in our MCP server."""
        print("--- Testing Task Manager MCP Server ---")

        # Test 1: Create a task
        print("\n1. Creating a task...")
        result = await mcp.call_tool("create_task", {
            "title": "Test Task",
            "priority": "high"
        })
        print(f"Result: {json.dumps(result, indent=2)}")

        # Test 2: List tasks
        print("\n2. Listing all tasks...")
        result = await mcp.call_tool("list_tasks", {})
        print(f"Result: {json.dumps(result, indent=2)}")

        print("\n--- Test completed! ---")

    if __name__ == "__main__":
        asyncio.run(test_tools())
    ```

3.  **Run the Test:** In your terminal, from your project's root directory, run the test script:

    ```bash
    python test_mcp.py
    ```

You should see output showing that a task was created and then listed successfully.

---

## Part 4: Integrating with Aurite

Now let's connect your new server to an agent.

### Step 1: Register the Server in `aurite_config.json`

Open your `aurite_config.json` file and add a new object to the `mcp_servers` array.

```json
{
  "name": "task_manager_server",
  "transport_type": "stdio",
  "server_path": "mcp_servers/task_manager_server.py"
}
```

Make sure to add a comma after the preceding server configuration if one exists.

### Step 2: Create an Agent That Uses the Server

In the same `aurite_config.json` file, add a new agent to the `agents` array that uses your server.

```json
{
  "name": "TaskManagerAgent",
  "system_prompt": "You are a helpful task management assistant. Use the available tools to manage tasks. Always provide clear feedback about the operations you perform.",
  "llm_config_id": "my_openai_gpt4_turbo",
  "mcp_servers": ["task_manager_server"]
}
```

### Step 3: Run the Agent

You can now use the Aurite CLI to interact with your agent.

```bash
# Test creating a task
aurite run-agent TaskManagerAgent "Create a new task: 'Buy groceries' with medium priority"

# Test listing tasks
aurite run-agent TaskManagerAgent "Show me all my tasks"
```

---

## 🎉 Congratulations!

You've successfully built, tested, and integrated your first custom MCP server!

### ✅ What You've Learned:

- How to build a simple MCP server with the `FastMCP` helper.
- How to define tools using the `@mcp.tool()` decorator.
- How to test an MCP server directly.
- How to register a custom server in `aurite_config.json`.
- How to create an agent that uses your custom tools.

### 🚀 Next Steps:

- Try adding a `complete_task` tool to your server.
- Experiment with adding more complex logic, like file persistence.
- Explore the official MCP documentation for more advanced features.
