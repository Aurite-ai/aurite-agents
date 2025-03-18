"""
Test script for the planning MCP server.

This script demonstrates:
1. Connecting to the planning MCP server
2. Getting the planning prompt
3. Using the save_plan tool
4. Using the list_plans tool
5. Accessing plan resources
"""

import asyncio
import logging
import sys
from pathlib import Path
from contextlib import AsyncExitStack

# Add parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PlanningClient:
    def __init__(self):
        # Initialize session and client objects
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
    
    async def connect_to_server(self, server_script_path: str):
        """Connect to the planning MCP server
        
        Args:
            server_script_path: Path to the server script
        """
        # Setup connection parameters
        server_params = StdioServerParameters(
            command="python",
            args=[str(server_script_path)],
            env=None
        )
        
        # Connect to the server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        
        # Initialize the client
        await self.session.initialize()
        
        # List available tools
        tools_result = await self.session.list_tools()
        logger.info(f"Available tools: {[t.name for t in tools_result.tools]}")
        
        # List available prompts
        prompts_result = await self.session.list_prompts()
        logger.info(f"Available prompts: {[p.name for p in prompts_result.prompts]}")
    
    async def test_planning_prompt(self):
        """Test getting the planning prompt"""
        logger.info("Testing planning prompt...")
        
        # Get the planning prompt
        # Note: MCP API expects resources to be a string, not a list
        prompt_result = await self.session.get_prompt(
            "planning_prompt",
            {
                "task": "Build a web application to manage tasks",
                "timeframe": "2 weeks",
                "resources": "Frontend developer, Backend developer, UI/UX designer"
            }
        )
        
        # Debug what attributes are available
        logger.info(f"Prompt result keys: {dir(prompt_result)}")
        
        # Based on the keys above, try to access 'messages' or use a fallback
        if hasattr(prompt_result, 'messages') and prompt_result.messages:
            prompt_content = prompt_result.messages[0].content if prompt_result.messages else ""
        else:
            # Fallback: try model_dump() to get all fields
            data = prompt_result.model_dump()
            logger.info(f"Prompt result data: {data}")
            
            # Try to extract the prompt from the data
            if 'messages' in data and data['messages']:
                prompt_content = data['messages'][0].get('content', "")
            else:
                prompt_content = str(prompt_result)
        
        logger.info("Planning prompt received:")
        print("\n" + str(prompt_content) + "\n")
        return str(prompt_content)
    
    async def test_save_plan(self):
        """Test saving a plan"""
        logger.info("Testing save_plan...")
        
        # Create a test plan
        plan_content = """
# Project Plan: Task Management Web Application

## Objective
Create a functional, user-friendly task management web application within 2 weeks.

## Key Steps
1. Requirements analysis and planning
2. UI/UX design
3. Frontend development
4. Backend development
5. Integration and testing
6. Deployment

## Timeline
- Step 1: 2 days
- Step 2: 3 days
- Step 3: 5 days
- Step 4: 5 days
- Step 5: 3 days
- Step 6: 1 day

## Resources Required
- Frontend developer
- Backend developer
- UI/UX designer
"""
        
        # Save the plan - using call_tool instead of execute_tool for compatibility
        tool_result = await self.session.call_tool(
            "save_plan",
            {
                "plan_name": "task_app_project",
                "plan_content": plan_content,
                "tags": ["web", "application", "project"]
            }
        )
        
        # Extract the content field from the result if it exists
        result_content = tool_result.content if hasattr(tool_result, 'content') else str(tool_result)
        logger.info(f"Save plan result: {result_content}")
        return result_content
    
    async def test_list_plans(self):
        """Test listing plans"""
        logger.info("Testing list_plans...")
        
        # List all plans - using call_tool instead of execute_tool
        tool_result = await self.session.call_tool(
            "list_plans",
            {}
        )
        
        # Extract the content field from the result if it exists
        result_content = tool_result.content if hasattr(tool_result, 'content') else str(tool_result)
        logger.info(f"List plans result: {result_content}")
        return result_content
    
    async def test_filtered_plans(self, tag):
        """Test filtering plans by tag"""
        logger.info(f"Testing list_plans with tag '{tag}'...")
        
        # List plans with a specific tag - using call_tool instead of execute_tool
        tool_result = await self.session.call_tool(
            "list_plans",
            {"tag": tag}
        )
        
        # Extract the content field from the result if it exists
        result_content = tool_result.content if hasattr(tool_result, 'content') else str(tool_result)
        logger.info(f"Tag-filtered list result: {result_content}")
        return result_content
    
    async def test_plan_resource(self, plan_name):
        """Test accessing plan resource"""
        logger.info(f"Testing plan resource for '{plan_name}'...")
        
        # Access the plan resource - using read_resource instead of get_resource
        resource_result = await self.session.read_resource(f"planning://plan/{plan_name}")
        
        # Debug what attributes are available
        logger.info(f"Resource result keys: {dir(resource_result)}")
        
        # Try different attribute names
        try:
            resource_content = resource_result.content
        except AttributeError:
            try:
                resource_content = resource_result.text
            except AttributeError:
                try:
                    resource_content = str(resource_result)
                except:
                    resource_content = "Could not extract resource content"
        
        logger.info("Plan resource content:")
        print("\n" + resource_content + "\n")
        return resource_content
    
    async def test_analysis_prompt(self, plan_name):
        """Test the plan analysis prompt"""
        logger.info(f"Testing plan analysis prompt for '{plan_name}'...")
        
        # Get the analysis prompt
        prompt_result = await self.session.get_prompt(
            "plan_analysis_prompt",
            {"plan_name": plan_name}
        )
        
        # Debug what attributes are available
        logger.info(f"Analysis prompt result keys: {dir(prompt_result)}")
        
        # Based on the keys above, try to access 'messages' or use a fallback
        if hasattr(prompt_result, 'messages') and prompt_result.messages:
            prompt_content = prompt_result.messages[0].content if prompt_result.messages else ""
        else:
            # Fallback: try model_dump() to get all fields
            data = prompt_result.model_dump()
            logger.info(f"Analysis prompt result data: {data}")
            
            # Try to extract the prompt from the data
            if 'messages' in data and data['messages']:
                prompt_content = data['messages'][0].get('content', "")
            else:
                prompt_content = str(prompt_result)
        
        logger.info("Plan analysis prompt:")
        print("\n" + str(prompt_content) + "\n")
        return str(prompt_content)
    
    async def test_with_llm(self, plan_name):
        """Test plan creation and analysis with Claude"""
        # Check if we have an API key
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.warning("Skipping LLM test, ANTHROPIC_API_KEY not set")
            return
        
        logger.info("Testing planning with Claude...")
        
        # Get the prompt first
        prompt_text = await self.test_planning_prompt()
        
        # Process with Claude
        response = await self.process_query(
            f"Create a detailed project plan for building a mobile weather app. " +
            f"The plan should be comprehensive and follow a structured format."
        )
        
        logger.info("LLM-generated plan:")
        print("\n" + response + "\n")
        
        # Now test plan analysis
        if plan_name:
            # Get the plan content
            plan_content = await self.test_plan_resource(plan_name)
            
            # Analyze with Claude
            response = await self.process_query(
                f"Analyze this existing plan called '{plan_name}'. " +
                f"Identify any gaps, inconsistencies, or areas for improvement."
            )
            
            logger.info("LLM plan analysis:")
            print("\n" + response + "\n")
    
    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [{"role": "user", "content": query}]
        
        # Get available tools
        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]
        
        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )
        
        # Process response and handle tool calls
        tool_results = []
        final_text = []
        
        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input
                
                # Execute tool call
                try:
                    # Use call_tool instead of execute_tool
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_results.append({"call": tool_name, "result": result})
                    final_text.append(f"\n[Calling tool {tool_name} with args {tool_args}]")
                    
                    # Extract content from result
                    result_content = result.content if hasattr(result, 'content') else str(result)
                    final_text.append(f"\n[Tool result: {result_content}]")
                except Exception as e:
                    logger.error(f"Error calling tool {tool_name}: {e}")
                    final_text.append(f"\n[Error calling tool {tool_name}: {e}]")
                
                # Add the assistant's tool use message
                messages.append(
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": content.id,
                                "name": tool_name,
                                "input": tool_args,
                            }
                        ],
                    }
                )
                
                # Add the tool result message
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": str(result),
                            }
                        ],
                    }
                )
                
                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools,
                )
                
                final_text.append("\n" + response.content[0].text)
        
        return "\n".join(final_text)
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    """Main test function"""
    # Path to the server script
    server_path = Path(__file__).parent / "planning_server.py"
    
    logger.info(f"Starting planning server: {server_path}")
    
    client = PlanningClient()
    try:
        await client.connect_to_server(server_path)
        
        # Test planning prompt
        await client.test_planning_prompt()
        
        # Test save_plan
        await client.test_save_plan()
        
        # Test list_plans
        await client.test_list_plans()
        
        # Test filtered list
        await client.test_filtered_plans("web")
        
        # Test plan resource
        await client.test_plan_resource("task_app_project")
        
        # Test analysis prompt
        await client.test_analysis_prompt("task_app_project")
        
        # Test with LLM if API key is available
        await client.test_with_llm("task_app_project")
        
        logger.info("All tests completed successfully!")
    finally:
        await client.cleanup()


async def test_directly():
    """Import and test the functions directly"""
    import sys
    from pathlib import Path
    
    # Add parent directory to path so we can import the module
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Import the mcp object and functions from the module
    try:
        # Import functions directly (they're now decorators on the mcp object)
        from planning_server import mcp, save_plan, list_plans, planning_prompt, plan_resource
        
        # Create a mock Context
        class MockContext:
            def info(self, message):
                print(f"INFO: {message}")
        
        ctx = MockContext()
        
        # Test planning prompt
        print("\nTesting planning_prompt...")
        prompt = planning_prompt(
            task="Build a mobile app",
            timeframe="3 weeks",
            resources="Developer, Designer"
        )
        print(f"Prompt: {prompt[:100]}...")
        
        # Test save_plan
        print("\nTesting save_plan...")
        save_result = save_plan(
            plan_name="direct_test_plan",
            plan_content="This is a test plan created directly.",
            tags=["test", "direct"],
            ctx=ctx
        )
        print(f"Save result: {save_result}")
        
        # Test list_plans
        print("\nTesting list_plans...")
        list_result = list_plans(ctx=ctx)
        print(f"List result: {list_result}")
        
        # Test filtered list_plans
        print("\nTesting list_plans with tag filter...")
        filtered_result = list_plans(tag="test", ctx=ctx)
        print(f"Filtered list result: {filtered_result}")
        
        # Test plan_resource
        print("\nTesting plan_resource...")
        resource = plan_resource("direct_test_plan")
        print(f"Resource: {resource[:100]}...")
    except ImportError as e:
        print(f"ImportError: {e}")
        print("\nRunning simplified test...")
        
        # Just test if we can import the module
        import planning_server
        print(f"Successfully imported planning_server module: {planning_server}")
        print(f"Available attributes: {dir(planning_server)}")
    
    print("\nDirect test complete!")


if __name__ == "__main__":
    # Decide which test to run based on a command line argument
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        asyncio.run(test_directly())
    else:
        asyncio.run(main())