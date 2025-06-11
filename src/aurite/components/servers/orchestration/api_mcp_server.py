import httpx
import os
import json
from mcp.server.fastmcp import FastMCP
from mcp import types
from typing import Dict, List

# It's good practice to load environment variables for configuration
from dotenv import load_dotenv

load_dotenv()

# Get API configuration from environment variables with defaults
API_BASE_URL = os.getenv("AURITE_API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")

app = FastMCP("aurite-api-mcp-server")


def get_api_headers() -> Dict[str, str]:
    """Constructs the authorization headers for API requests."""
    if not API_KEY:
        raise ValueError("API_KEY environment variable is not set.")
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }


async def api_request(method: str, url: str, **kwargs) -> list[types.TextContent]:
    """Helper function to make API requests and handle responses."""
    headers = get_api_headers()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            # Return the raw JSON text, which is more useful for an agent
            return [types.TextContent(type="text", text=response.text)]
    except httpx.HTTPStatusError as e:
        # Provide a more informative error message
        error_text = f"Error: API request failed with status {e.response.status_code}. Response: {e.response.text}"
        return [types.TextContent(type="text", text=error_text)]
    except Exception as e:
        return [
            types.TextContent(
                type="text", text=f"An unexpected error occurred: {str(e)}"
            )
        ]


@app.tool()
async def list_registered_components(component_type: str) -> list[types.TextContent]:
    """
    Lists the names of all currently registered components of a given type.

    Args:
        component_type: The type of component to list. One of 'agents', 'mcp_servers', 'llms', 'simple_workflows', 'custom_workflows'.
    """
    # Map to the correct API endpoint path
    component_path_segment = {
        "mcp_servers": "clients",  # API uses 'clients' for mcp_servers
        "simple_workflows": "workflows",
    }.get(component_type, component_type)

    api_url = f"{API_BASE_URL}/components/{component_path_segment}"
    return await api_request("GET", api_url)


@app.tool()
async def get_component_config(
    component_type: str, component_id_or_name: str
) -> list[types.TextContent]:
    """
    Gets a specific component configuration by its ID or name.

    Args:
        component_type: The type of the component (e.g., "agents").
        component_id_or_name: The unique ID or name of the component.
    """
    api_url = f"{API_BASE_URL}/configs/{component_type}/id/{component_id_or_name}"
    return await api_request("GET", api_url)


@app.tool()
async def create_agent_config(
    name: str,
    system_prompt: str,
    mcp_servers: List[str] = [],
    llm_config_id: str = "anthropic_claude_3_haiku",
) -> list[types.TextContent]:
    """
    Creates and registers a new agent within the Aurite framework by generating its configuration file.

    Args:
        name: The unique name for the new agent.
        system_prompt: The system prompt for the agent.
        mcp_servers: A list of MCP server names to connect to this agent.
        llm_config_id: The ID of the LLM configuration to use.
    """
    api_url = f"{API_BASE_URL}/configs/agents/{name}.json"
    payload = {
        "content": {
            "name": name,
            "system_prompt": system_prompt,
            "mcp_servers": mcp_servers,
            "llm_config_id": llm_config_id,
        }
    }
    return await api_request("POST", api_url, json=payload)


@app.tool()
async def execute_component(
    component_type: str,
    name: str,
    input: str,
) -> list[types.TextContent]:
    """
    Executes a component by name, handling registration automatically.

    Args:
        component_type: The type of component. One of 'agent', 'simple_workflow', 'custom_workflow'.
        name: The name of the component to execute.
        input: The input message or JSON string for the component.
    """
    # Map user-friendly type to API path segments
    config_path_segment = {
        "agent": "agents",
        "simple_workflow": "simple-workflows",
        "custom_workflow": "custom-workflows",
    }.get(component_type)

    base_api_segment = {
        "agent": "agents",
        "simple_workflow": "workflows",
        "custom_workflow": "custom_workflows",
    }.get(component_type)

    if not config_path_segment or not base_api_segment:
        return [
            types.TextContent(
                type="text", text=f"Error: Invalid component_type '{component_type}'."
            )
        ]

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:  # Increased timeout for workflows
        try:
            # Step 1: Get the component's configuration from the config files
            config_url = f"{API_BASE_URL}/configs/{config_path_segment}/id/{name}"
            config_response = await client.get(config_url, headers=get_api_headers())
            config_response.raise_for_status()
            component_config = config_response.json()

            # Step 2: Register the component with the running host
            register_url = f"{API_BASE_URL}/{base_api_segment}/register"
            register_response = await client.post(
                register_url, headers=get_api_headers(), json=component_config
            )
            if (
                register_response.status_code != 409
            ):  # Ignore 409 Conflict (already registered)
                register_response.raise_for_status()

            # Step 3: Prepare the execution payload
            if component_type == "agent":
                payload = {"user_message": input}
            elif component_type == "simple_workflow":
                payload = {"initial_user_message": input}
            else:  # custom_workflow
                try:
                    payload = {"initial_input": json.loads(input)}
                except json.JSONDecodeError:
                    payload = {"initial_input": input}

            # Step 4: Execute the component
            execute_url = f"{API_BASE_URL}/{base_api_segment}/{name}/execute"
            execute_response = await client.post(
                execute_url, headers=get_api_headers(), json=payload
            )
            execute_response.raise_for_status()

            return [types.TextContent(type="text", text=execute_response.text)]

        except httpx.HTTPStatusError as e:
            error_text = f"Error: API request failed with status {e.response.status_code}. Response: {e.response.text}"
            return [types.TextContent(type="text", text=error_text)]
        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"An unexpected error occurred: {str(e)}"
                )
            ]


if __name__ == "__main__":
    app.run()
