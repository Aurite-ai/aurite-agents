# Tutorial: Building Your Own MCP Server

**Welcome to the advanced tutorial on creating custom MCP servers!** This tutorial builds on everything you've learned about agents, tools, and project configuration. Now you'll learn how to extend the Aurite framework by creating your own Model Context Protocol (MCP) server that provides custom tools to your agents.

**Learning Objectives:**

**Primary Goal: Understanding MCP and Building a Custom Server**
*   Understand what the Model Context Protocol (MCP) is and how it enables tool integration
*   Learn the structure and components of an MCP server
*   Build a functional MCP server from scratch that provides custom tools
*   Test your MCP server to ensure it works correctly

**Secondary Goal: Integration with Aurite Framework**
*   Learn how to register your custom MCP server as a ClientConfig in your Aurite project
*   Create an agent that uses your custom MCP server
*   Understand the difference between packaged servers and custom servers
*   Successfully run an agent that uses your custom tools

---

## Prerequisites

⚠️ **Before you begin this tutorial, please ensure you have completed:**

*   All previous tutorials, especially "Understanding Projects" and "Using the CLI"
*   A working Aurite project set up locally
*   Python 3.12+ installed and configured
*   Basic understanding of Python programming
*   Familiarity with JSON configuration files

---

## Part 1: Understanding the Model Context Protocol (MCP)

### What is MCP?

The **Model Context Protocol (MCP)** is a standardized way for AI applications to connect with external data sources and tools. Think of it as a bridge that allows your AI agents to interact with the outside world.

**Key Concepts:**

*   **MCP Server**: A program that provides tools, resources, or prompts to AI agents
*   **MCP Client**: The AI application (like Aurite) that connects to and uses MCP servers
*   **Tools**: Functions that agents can call to perform actions (e.g., search the web, save files)
*   **Resources**: Data sources that agents can read from (e.g., files, databases)
*   **Prompts**: Pre-defined prompt templates that can be used by agents

### How MCP Works in Aurite

In the Aurite framework:

1. **MCP Servers** run as separate processes and provide tools/resources
2. **ClientConfig** objects define how to connect to these servers
3. **Agents** specify which MCP servers they can use via the `mcp_servers` field
4. When an agent runs, Aurite connects to the specified servers and makes their tools available

### Transport Types

MCP servers can communicate using different transport methods:

*   **`stdio`**: For local Python scripts that communicate via standard input/output
*   **`http_stream`**: For servers running as web services with HTTP endpoints
*   **`local`**: For servers installed via package managers (like npm packages from Smithery)

For this tutorial, we'll focus on creating a **`stdio`** server since it's the most straightforward for custom development.

---

## Part 2: Planning Your MCP Server

Before we start coding, let's plan what our MCP server will do. For this tutorial, we'll create a **Task Management Server** that provides tools for:

1. **Creating tasks** with titles, descriptions, and priorities
2. **Listing tasks** with optional filtering
3. **Marking tasks as complete**
4. **Getting task statistics**

This will demonstrate the key concepts while being practical and useful.

### Server Structure

Our MCP server will:
*   Use the Python MCP SDK for easy development
*   Store tasks in a simple JSON file for persistence
*   Provide 4 tools: `create_task`, `list_tasks`, `complete_task`, and `get_task_stats`
*   Include proper error handling and validation

---

## Part 3: Setting Up the Development Environment

### Step 1: Create the MCP Server Directory

First, let's create a dedicated directory for our MCP server within your Aurite project:

```bash
# Navigate to your Aurite project root (where aurite_config.json is)
cd your_project_name

# Create the MCP servers directory
mkdir -p mcp_servers
cd mcp_servers
```

### Step 2: Install Required Dependencies

We need to install the MCP SDK for Python. Create a requirements file for our server:

```bash
# Create requirements file for our MCP server
cat > requirements.txt << EOF
mcp>=1.0.0
pydantic>=2.0.0
EOF

# Install the dependencies
pip install -r requirements.txt
```

---

## Part 4: Building the MCP Server

### Step 1: Create the Server File

Create a new file called `task_manager_server.py`:

```python
#!/usr/bin/env python3
"""
Task Management MCP Server

This server provides tools for managing tasks:
- create_task: Create a new task with title, description, and priority
- list_tasks: List all tasks with optional filtering
- complete_task: Mark a task as completed
- get_task_stats: Get statistics about tasks
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

# MCP imports
from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TASKS_FILE = Path(__file__).parent / "tasks.json"

# Create the MCP server
mcp = FastMCP("Task Manager")

# Task storage
def load_tasks() -> List[Dict[str, Any]]:
    """Load tasks from the JSON file."""
    if not TASKS_FILE.exists():
        return []
    
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.warning("Could not load tasks file, starting with empty list")
        return []

def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    """Save tasks to the JSON file."""
    try:
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save tasks: {e}")
        raise

@mcp.tool()
async def create_task(
    title: str,
    description: str = "",
    priority: str = "medium"
) -> Dict[str, Any]:
    """
    Create a new task.
    
    Args:
        title: The title of the task (required)
        description: Detailed description of the task
        priority: Priority level (low, medium, high)
    
    Returns:
        Dictionary with the created task information
    """
    # Validate priority
    valid_priorities = ["low", "medium", "high"]
    if priority not in valid_priorities:
        return {
            "success": False,
            "error": f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
        }
    
    # Load existing tasks
    tasks = load_tasks()
    
    # Create new task
    new_task = {
        "id": str(uuid4()),
        "title": title,
        "description": description,
        "priority": priority,
        "completed": False,
        "created_at": datetime.now().isoformat(),
        "completed_at": None
    }
    
    # Add to tasks list
    tasks.append(new_task)
    
    # Save tasks
    try:
        save_tasks(tasks)
        return {
            "success": True,
            "task": new_task,
            "message": f"Task '{title}' created successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save task: {str(e)}"
        }

@mcp.tool()
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all tasks with optional filtering.
    
    Args:
        status: Filter by status ('completed', 'pending', or None for all)
        priority: Filter by priority ('low', 'medium', 'high', or None for all)
    
    Returns:
        Dictionary with list of tasks matching the filters
    """
    # Load tasks
    tasks = load_tasks()
    
    # Apply filters
    filtered_tasks = tasks
    
    if status:
        if status == "completed":
            filtered_tasks = [t for t in filtered_tasks if t["completed"]]
        elif status == "pending":
            filtered_tasks = [t for t in filtered_tasks if not t["completed"]]
        else:
            return {
                "success": False,
                "error": "Invalid status. Must be 'completed' or 'pending'"
            }
    
    if priority:
        valid_priorities = ["low", "medium", "high"]
        if priority not in valid_priorities:
            return {
                "success": False,
                "error": f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
            }
        filtered_tasks = [t for t in filtered_tasks if t["priority"] == priority]
    
    return {
        "success": True,
        "tasks": filtered_tasks,
        "count": len(filtered_tasks),
        "total_tasks": len(tasks)
    }

@mcp.tool()
async def complete_task(task_id: str) -> Dict[str, Any]:
    """
    Mark a task as completed.
    
    Args:
        task_id: The ID of the task to complete
    
    Returns:
        Dictionary with the result of the operation
    """
    # Load tasks
    tasks = load_tasks()
    
    # Find the task
    task_found = False
    for task in tasks:
        if task["id"] == task_id:
            if task["completed"]:
                return {
                    "success": False,
                    "error": "Task is already completed"
                }
            
            task["completed"] = True
            task["completed_at"] = datetime.now().isoformat()
            task_found = True
            break
    
    if not task_found:
        return {
            "success": False,
            "error": f"Task with ID '{task_id}' not found"
        }
    
    # Save tasks
    try:
        save_tasks(tasks)
        return {
            "success": True,
            "message": f"Task '{task_id}' marked as completed"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save task: {str(e)}"
        }

@mcp.tool()
async def get_task_stats() -> Dict[str, Any]:
    """
    Get statistics about all tasks.
    
    Returns:
        Dictionary with task statistics
    """
    # Load tasks
    tasks = load_tasks()
    
    if not tasks:
        return {
            "success": True,
            "stats": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "completion_rate": 0.0,
                "priority_breakdown": {"low": 0, "medium": 0, "high": 0}
            }
        }
    
    # Calculate statistics
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t["completed"]])
    pending_tasks = total_tasks - completed_tasks
    completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0.0
    
    # Priority breakdown
    priority_breakdown = {"low": 0, "medium": 0, "high": 0}
    for task in tasks:
        priority_breakdown[task["priority"]] += 1
    
    return {
        "success": True,
        "stats": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": round(completion_rate, 2),
            "priority_breakdown": priority_breakdown
        }
    }

# Allow direct execution of the server
if __name__ == "__main__":
    mcp.run()
```

### Step 2: Make the Server Executable

Make sure your server file is executable:

```bash
chmod +x task_manager_server.py
```

---

## Part 5: Testing Your MCP Server

Before integrating with Aurite, let's test our MCP server to make sure it works correctly.

### Step 1: Test Server Startup

First, let's verify the server can start without errors:

```bash
# Navigate to your mcp_servers directory
cd mcp_servers

# Test the server startup (it should start and wait for input)
python task_manager_server.py
```

If the server starts without errors, you can stop it with `Ctrl+C`.

### Step 2: Create a Test Script

Create a simple test script to verify our tools work:

```python
# Create test_server.py
cat > test_server.py << 'EOF'
#!/usr/bin/env python3
"""
Simple test script for our Task Manager MCP Server
"""

import asyncio
import json
from task_manager_server import mcp

async def test_tools():
    """Test all the tools in our MCP server."""
    print("Testing Task Manager MCP Server...")
    print("=" * 50)
    
    # Test 1: Create a task
    print("\n1. Creating a task...")
    result = await mcp.call_tool("create_task", {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "high"
    })
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test 2: List tasks
    print("\n2. Listing all tasks...")
    result = await mcp.call_tool("list_tasks", {})
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test 3: Get task stats
    print("\n3. Getting task statistics...")
    result = await mcp.call_tool("get_task_stats", {})
    print(f"Result: {json.dumps(result, indent=2)}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_tools())
EOF

# Run the test
python test_server.py
```

If everything works correctly, you should see output showing the creation of a task, listing of tasks, and task statistics.

---

## Part 6: Integrating with Aurite

Now that our MCP server is working, let's integrate it with your Aurite project.

### Step 1: Register the MCP Server as a ClientConfig

Open your `aurite_config.json` file and add a new MCP server configuration:

```json
{
  "llms": [
    // ... your existing LLM configurations
  ],
  "mcp_servers": [
    // ... your existing MCP server configurations
    {
      "name": "task_manager_server",
      "transport_type": "stdio",
      "server_path": "mcp_servers/task_manager_server.py",
      "capabilities": ["tools"],
      "timeout": 15.0
    }
  ],
  "agents": [
    // ... your existing agent configurations
  ]
}
```

### Step 2: Create an Agent That Uses Your MCP Server

Add a new agent configuration that can use your task management tools:

```json
{
  "agents": [
    // ... your existing agents
    {
      "name": "TaskManagerAgent",
      "system_prompt": "You are a helpful task management assistant. You can help users create, list, complete, and get statistics about their tasks. Use the available tools to manage tasks effectively. Always provide clear feedback about the operations you perform.",
      "llm_config_id": "my_openai_gpt4_turbo",
      "mcp_servers": ["task_manager_server"]
    }
  ]
}
```

### Step 3: Test the Integration

Create a simple test script to verify the integration works:

```python
# Create test_integration.py in your project root
cat > test_integration.py << 'EOF'
#!/usr/bin/env python3
"""
Test script to verify our custom MCP server works with Aurite
"""

import asyncio
from aurite import Aurite

async def test_task_agent():
    """Test our TaskManagerAgent with the custom MCP server."""
    
    # Initialize Aurite
    aurite = Aurite()
    await aurite.initialize()
    
    print("Testing TaskManagerAgent with custom MCP server...")
    print("=" * 60)
    
    # Test 1: Create a task
    print("\n1. Creating a task...")
    result = await aurite.run_agent(
        agent_name="TaskManagerAgent",
        user_message="Create a task called 'Learn MCP Development' with description 'Complete the MCP server tutorial' and high priority"
    )
    print(f"Agent Response: {result.primary_text}")
    
    # Test 2: List tasks
    print("\n2. Listing tasks...")
    result = await aurite.run_agent(
        agent_name="TaskManagerAgent",
        user_message="Show me all my tasks"
    )
    print(f"Agent Response: {result.primary_text}")
    
    # Test 3: Get statistics
    print("\n3. Getting task statistics...")
    result = await aurite.run_agent(
        agent_name="TaskManagerAgent",
        user_message="Give me statistics about my tasks"
    )
    print(f"Agent Response: {result.primary_text}")
    
    print("\n" + "=" * 60)
    print("Integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_task_agent())
EOF

# Run the integration test
python test_integration.py
```

---

## Part 7: Using the CLI

You can also test your agent using the Aurite CLI:

```bash
# Test creating a task
aurite run-agent TaskManagerAgent "Create a new task: 'Buy groceries' with medium priority"

# Test listing tasks
aurite run-agent TaskManagerAgent "Show me all my pending tasks"

# Test completing a task (you'll need the task ID from the list)
aurite run-agent TaskManagerAgent "Mark the task with ID [task-id] as completed"

# Test getting statistics
aurite run-agent TaskManagerAgent "What are my task statistics?"
```

---

## Part 8: Understanding the Difference Between Custom and Packaged Servers

### Custom MCP Servers (What You Just Built)

**Characteristics:**
*   Created by you for your specific needs
*   Stored in your project's `mcp_servers/` directory
*   Configured with `transport_type: "stdio"` and `server_path`
*   Fully customizable and under your control

**Use Cases:**
*   Business-specific tools and integrations
*   Experimental or prototype functionality
*   Tools that require custom logic or data sources
*   Learning and development purposes

### Packaged MCP Servers (From Aurite's Toolbox)

**Characteristics:**
*   Pre-built and tested by the Aurite team
*   Available through Just-in-Time (JIT) registration
*   Often use `transport_type: "local"` or `"http_stream"`
*   Ready to use without configuration

**Use Cases:**
*   Common functionality like web search, weather, etc.
*   Quick prototyping and testing
*   Standard integrations with popular services

### When to Use Each

**Use Custom Servers When:**
*   You need functionality that doesn't exist in the packaged toolbox
*   You have specific business requirements or data sources
*   You want to learn how MCP works
*   You need full control over the implementation

**Use Packaged Servers When:**
*   The functionality you need already exists
*   You want to get started quickly
*   You're prototyping or experimenting
*   You prefer tested, maintained solutions

---

## Part 9: Best Practices and Next Steps

### Best Practices for MCP Server Development

1. **Error Handling**: Always include proper error handling and return meaningful error messages
2. **Validation**: Validate all input parameters before processing
3. **Logging**: Use logging to help with debugging and monitoring
4. **Documentation**: Include clear docstrings for all tools
5. **Testing**: Test your server thoroughly before integration
6. **Security**: Be careful with file operations and external API calls

### Extending Your MCP Server

Here are some ideas for extending your task management server:

1. **Add due dates** to tasks with reminder functionality
2. **Implement task categories** or tags for better organization
3. **Add task dependencies** (tasks that depend on other tasks)
4. **Create recurring tasks** functionality
5. **Add file attachments** to tasks
6. **Implement task sharing** between users

### Advanced MCP Concepts

As you become more comfortable with MCP development, you can explore:

1. **Resources**: Provide data sources that agents can read from
2. **Prompts**: Create reusable prompt templates
3. **HTTP Servers**: Build MCP servers that run as web services
4. **Authentication**: Implement secure authentication for your servers
5. **Streaming**: Handle real-time data streams

---

## 🎉 Congratulations!

You've successfully completed the MCP Server Development tutorial! You now know how to:

### ✅ What You've Learned:

1. **MCP Fundamentals**
   - Understand what MCP is and how it works
   - Know the different transport types and when to use them
   - Understand the relationship between servers, clients, and agents

2. **Custom MCP Server Development**
   - Build a complete MCP server from scratch
   - Implement multiple tools with proper error handling
   - Test your server independently before integration

3. **Aurite Integration**
   - Register custom MCP servers as ClientConfig objects
   - Create agents that use your custom tools
   - Test the integration using both Python scripts and the CLI

4. **Best Practices**
   - Understand when to use custom vs. packaged servers
   - Know how to structure and organize MCP server code
   - Implement proper error handling and validation

### 💡 Key Takeaway:

Building custom MCP servers allows you to extend the Aurite framework with any functionality you need. By following the MCP protocol, you can create tools that integrate seamlessly with AI agents, enabling powerful automation and integration capabilities.

### 🚀 Next Steps:

*   Experiment with different types of tools and integrations
*   Explore the MCP documentation for advanced features
*   Consider contributing useful servers back to the community
*   Build MCP servers that integrate with your business systems

**You're now ready to build sophisticated AI agents with custom tools tailored to your specific needs!**
