# Aurite API Client for TypeScript/JavaScript

A type-safe TypeScript client for interacting with the Aurite Framework API. The client is organized into three main modules that correspond to the Aurite API structure:

- **Execution**: Run agents and workflows
- **Host**: Manage MCP servers and tools
- **Config**: Manage configurations

## Installation

```bash
npm install
# or
yarn install
```

## Project Structure

```
src/
├── index.ts                    # Main entry point
├── AuriteApiClient.ts         # Main client class
├── BaseClient.ts              # Base HTTP client
├── types.ts                   # TypeScript type definitions
├── ExecutionFacadeClient.ts   # Agent & workflow execution
├── MCPHostClient.ts           # MCP server & tool management
└── ConfigManagerClient.ts     # Configuration management
```

## Usage

### Basic Setup

```typescript
import { createAuriteClient } from 'aurite-api-client';

const client = createAuriteClient(
  process.env.AURITE_API_BASE_URL || 'http://localhost:8000',
  process.env.AURITE_API_KEY || 'your-api-key'
);

// The client provides three sub-clients:
// - client.execution - for running agents and workflows
// - client.host - for managing MCP servers and tools
// - client.config - for managing configurations
```

### Running an Agent

```typescript
const result = await client.execution.runAgent('Weather Agent', {
  user_message: 'What is the weather in San Francisco?',
});

console.log(result.final_response?.content);
```

### Streaming Agent Responses

```typescript
await client.execution.streamAgent(
  'Weather Agent',
  { user_message: 'Tell me about the weather' },
  (event) => {
    if (event.type === 'llm_response') {
      console.log(event.data.content);
    }
  }
);
```

### Running Workflows

```typescript
// Simple workflow
const workflowResult = await client.execution.runSimpleWorkflow('Weather Planning Workflow', {
  initial_input: 'What should I wear today?',
});

// Custom workflow
const customResult = await client.execution.runCustomWorkflow('ExampleCustomWorkflow', {
  initial_input: 'London',
});
```

### Managing MCP Servers and Tools

```typescript
// List available tools
const tools = await client.host.listTools();

// Register a server
await client.host.registerServerByName('weather_server');

// Call a tool directly
const weatherData = await client.host.callTool('weather_lookup', {
  location: 'New York',
});

// Unregister a server
await client.host.unregisterServer('weather_server');
```

### Configuration Management

```typescript
// List configurations
const agents = await client.config.listConfigs('agent');

// Get a specific configuration
const agentConfig = await client.config.getConfig('agent', 'Weather Agent');

// Create a new configuration
await client.config.createConfig('agent', {
  name: 'My Agent',
  description: 'Custom agent',
  system_prompt: 'You are helpful.',
  llm_config_id: 'anthropic_claude_3_haiku',
});

// Update configuration
await client.config.updateConfig('agent', 'My Agent', updatedConfig);

// Delete configuration
await client.config.deleteConfig('agent', 'My Agent');
```

## API Reference

### Client Structure

The main client provides access to three sub-clients:

```typescript
const client = createAuriteClient(baseUrl, apiKey);

client.execution  // ExecutionFacadeClient
client.host       // MCPHostClient
client.config     // ConfigManagerClient
```

### Client Methods

#### Execution Facade (`client.execution`)
- `getStatus()` - Get the execution facade status
- `runAgent(name, request)` - Run an agent synchronously
- `streamAgent(name, request, onEvent)` - Stream agent responses
- `runSimpleWorkflow(name, request)` - Run a simple workflow
- `runCustomWorkflow(name, request)` - Run a custom workflow

#### MCP Host (`client.host`)
- `getStatus()` - Get MCP host status and tool count
- `listTools()` - List all available tools
- `registerServerByName(name)` - Register a server by its configured name
- `registerServerByConfig(config)` - Register a server with a custom config
- `unregisterServer(name)` - Unregister a server
- `callTool(name, args)` - Call a tool directly

#### Configuration Manager (`client.config`)
- `listConfigs(type)` - List all configs of a given type
- `getConfig(type, name)` - Get a specific configuration
- `createConfig(type, config)` - Create a new configuration
- `updateConfig(type, name, config)` - Update an existing configuration
- `deleteConfig(type, name)` - Delete a configuration
- `reloadConfigs()` - Reload all configurations from disk

## Types

The client exports TypeScript interfaces for all request and response types:

- `AgentRunRequest` - Request payload for running agents
- `AgentRunResult` - Response from agent execution
- `WorkflowRunRequest` - Request payload for workflows
- `WorkflowExecutionResult` - Response from workflow execution
- `StreamEvent` - Events emitted during streaming
- `ServerConfig` - MCP server configuration
- `ToolCallResult` - Response from tool calls

## Examples

See `example.ts` for comprehensive usage examples.

## Development

To run the examples:

```bash
npm run example
# or
npx tsx example.ts
```

To compile TypeScript:

```bash
npm run build
```

To run tests:

```bash
# Unit tests (mocked, no API required)
npm test
# or
npm run test:watch

# Integration tests (requires running API)
npx tsx test-integration.ts
# or with API key
API_KEY=your-actual-api-key npx tsx test-integration.ts
