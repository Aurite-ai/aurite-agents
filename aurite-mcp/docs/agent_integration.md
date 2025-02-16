# Integrating Agents with Aurite MCP Host

This guide explains how to integrate AI agents with the Aurite MCP Host system, enabling them to access tools, resources, and prompts through the Model Context Protocol.

## Overview

Aurite MCP Host acts as a bridge between AI agents and tool servers, providing:

- Secure access to tools and resources
- Standardized communication protocol
- Resource boundary enforcement
- Prompt template management

## Integration Methods

### 1. Direct Integration

Use the MCPHost class directly in your agent code:

```python
from aurite_mcp.host import MCPHost, HostConfig, ClientConfig, RootConfig

async def setup_agent_tools():
    # Configure tool servers
    tool_config = ClientConfig(
        client_id="agent-tools",
        server_path=Path("tools/server.py"),
        roots=[
            RootConfig(
                uri="agent://tools/v1",
                name="Agent Tools",
                capabilities=["search", "analyze", "execute"],
            )
        ],
        capabilities=["tool_execution", "prompts", "resources"],
    )

    # Initialize host
    host = MCPHost(HostConfig(clients=[tool_config]))
    await host.initialize()
    return host

class Agent:
    def __init__(self):
        self.host = await setup_agent_tools()

    async def execute_task(self, task_description: str):
        # Use prompts for task analysis
        analysis = await self.host.execute_prompt(
            "analyze-task",
            {"task": task_description},
            "agent-tools"
        )

        # Access required resources
        context = await self.host.read_resource(
            "agent://tools/v1/context.json",
            "agent-tools"
        )

        # Execute tools based on analysis
        result = await self.host.call_tool(
            "execute",
            {"task": task_description, "context": context}
        )

        return result
```

### 2. Agent Framework Integration

For agents built with frameworks like LangChain or AutoGPT:

```python
from langchain.agents import Agent
from langchain.tools import Tool
from aurite_mcp.host import MCPHost
from aurite_mcp.integrations.langchain import MCPToolkit

class MCPAgent(Agent):
    def __init__(self, host: MCPHost):
        self.host = host
        self.toolkit = MCPToolkit(host)

        # Register MCP tools with LangChain
        self.tools = [
            Tool(
                name=tool.name,
                description=tool.description,
                func=self.toolkit.get_tool_executor(tool.name)
            )
            for tool in self.toolkit.list_tools()
        ]

    async def execute(self, input_str: str):
        # Agent execution logic here
        pass
```

## Resource Management

### 1. Setting Up Root URIs

Define resource boundaries for your agent:

```python
roots = [
    RootConfig(
        uri="agent://workspace",
        name="Agent Workspace",
        capabilities=["read", "write"],
    ),
    RootConfig(
        uri="agent://memory",
        name="Agent Memory Store",
        capabilities=["read", "write"],
    )
]
```

### 2. Resource Access Patterns

```python
class AgentMemory:
    def __init__(self, host: MCPHost):
        self.host = host

    async def store_memory(self, memory_data: dict):
        await self.host.call_tool(
            "write_memory",
            {
                "uri": "agent://memory/episodes",
                "data": memory_data
            }
        )

    async def retrieve_memory(self, query: str):
        return await self.host.call_tool(
            "search_memory",
            {
                "query": query,
                "uri": "agent://memory/episodes"
            }
        )
```

## Prompt Templates

### 1. Defining Agent Prompts

Create standardized prompts for common agent tasks:

```python
prompts = [
    {
        "name": "analyze-task",
        "description": "Analyze a task and break it down into steps",
        "arguments": [
            {
                "name": "task",
                "description": "Task description",
                "required": True
            },
            {
                "name": "context",
                "description": "Additional context",
                "required": False
            }
        ]
    },
    {
        "name": "generate-plan",
        "description": "Generate an execution plan for a task",
        "arguments": [
            {
                "name": "task",
                "description": "Task description",
                "required": True
            },
            {
                "name": "constraints",
                "description": "Task constraints",
                "required": True
            }
        ]
    }
]
```

### 2. Using Prompts in Agents

```python
class PlanningAgent:
    async def plan_task(self, task: str, constraints: dict):
        # Generate initial plan
        plan = await self.host.execute_prompt(
            "generate-plan",
            {
                "task": task,
                "constraints": constraints
            },
            "planning-server"
        )

        # Refine plan with additional context
        context = await self.host.read_resource(
            "agent://memory/previous_plans.json",
            "memory-server"
        )

        refined_plan = await self.host.execute_prompt(
            "refine-plan",
            {
                "plan": plan,
                "context": context
            },
            "planning-server"
        )

        return refined_plan
```

## Best Practices

1. **Resource Isolation**

   - Use specific root URIs for different agent components
   - Implement proper access control through capabilities
   - Validate resource access before operations

2. **Prompt Management**

   - Create reusable prompt templates
   - Include proper argument validation
   - Document prompt purposes and requirements

3. **Error Handling**

   ```python
   async def safe_tool_execution(self, tool_name: str, args: dict):
       try:
           return await self.host.call_tool(tool_name, args)
       except ValueError as e:
           logger.error(f"Tool validation error: {e}")
           # Handle validation errors
       except Exception as e:
           logger.error(f"Tool execution error: {e}")
           # Handle execution errors
   ```

4. **Performance Optimization**
   - Cache frequently used resources
   - Batch related tool calls when possible
   - Implement proper cleanup in agent shutdown

## Security Considerations

1. **Access Control**

   - Implement proper authentication for agents
   - Use specific root URIs for sensitive operations
   - Validate all resource access attempts

2. **Resource Validation**

   - Sanitize all inputs before tool execution
   - Validate resource URIs against root boundaries
   - Implement rate limiting for tool calls

3. **Monitoring**
   - Log all agent operations
   - Track resource usage
   - Monitor tool execution patterns

## Troubleshooting

Common issues and solutions:

1. **Resource Access Denied**

   - Verify root URI configuration
   - Check capability requirements
   - Validate client registration

2. **Tool Execution Failures**

   - Verify tool availability
   - Check argument validation
   - Review error logs

3. **Prompt Execution Issues**
   - Validate prompt registration
   - Check argument requirements
   - Review prompt template format

## Examples

See the `examples` directory for complete agent integration examples:

- Basic agent implementation
- LangChain integration
- AutoGPT integration
- Custom framework integration
