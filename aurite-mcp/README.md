# Aurite MCP Host

A Python implementation of the Model Context Protocol (MCP) host that manages communication between AI agents and tool servers.

## Overview

Aurite MCP Host is a robust implementation of the Model Context Protocol, designed to:

- Manage multiple MCP clients and tool servers
- Handle resource discovery and access
- Support prompt templates and execution
- Provide secure and efficient message routing
- Enforce resource boundaries through root URIs

## Features

### Core Functionality

- **Multi-Client Support**: Manage multiple MCP clients simultaneously
- **Tool Management**: Dynamic tool discovery and routing
- **Resource Management**: Secure resource access and updates
- **Prompt System**: Template-based prompt management
- **Root Boundaries**: URI-based access control

### Advanced Features

- **Transport Layer**

  - Stdio transport support
  - Extensible for additional transport types (e.g., SSE)
  - Connection lifecycle management

- **Resource System**

  - Resource discovery and registration
  - Content access and validation
  - Real-time update notifications
  - Root-based access control

- **Prompt System**
  - Prompt template management
  - Argument validation
  - Dynamic prompt execution
  - Client-specific prompt routing

## Installation

```bash
# Install in development mode
pip install -e .
```

Requirements:

- Python >= 3.12
- MCP SDK >= 0.1.0

## Usage

### Basic Example

```python
from src.host import MCPHost, HostConfig, ClientConfig, RootConfig
from pathlib import Path

# Configure a client
weather_config = ClientConfig(
    client_id="weather-client",
    server_path=Path("src/servers/server.py"),
    roots=[
        RootConfig(
            uri="weather://api.weather.gov",
            name="NWS Weather API",
            capabilities=["get_alerts", "get_forecast"],
        )
    ],
    capabilities=["weather_info"],
)

# Create and initialize the host
host = MCPHost(HostConfig(clients=[weather_config]))
await host.initialize()

# Call a tool
alerts = await host.call_tool("get_alerts", {"state": "CA"})
```

### Working with Resources

```python
# List available resources
resources = await host.list_resources()

# Read a resource
content = await host.read_resource("file:///logs/app.log", "client-id")

# Subscribe to updates
await host.subscribe_to_resource("file:///logs/app.log", "client-id")
```

### Using Prompts

```python
# List available prompts
prompts = await host.list_prompts()

# Execute a prompt
result = await host.execute_prompt(
    "analyze-code",
    {"language": "python", "code": "..."},
    "client-id"
)
```

## Architecture

The host is built with a modular architecture consisting of several key components:

### Core Managers

- **TransportManager**: Handles communication channels
- **RootManager**: Manages resource boundaries
- **MessageRouter**: Routes requests between clients
- **PromptManager**: Handles prompt templates
- **ResourceManager**: Manages resource access

### Message Flow

1. Client sends request to host
2. Host validates access through root manager
3. Request routed to appropriate tool server
4. Response returned through same channel

## Development

### Running Tests

```bash
python -m pytest
```

### Adding New Features

1. Implement feature in appropriate manager
2. Update host interface
3. Add tests
4. Update documentation

## Security

The host implements several security measures:

- Root-based access control
- Resource validation
- Argument sanitization
- Transport security
- Client isolation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Add tests
5. Submit pull request
