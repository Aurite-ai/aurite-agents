# Aurite API Client for TypeScript/JavaScript

A type-safe TypeScript client for interacting with the Aurite Framework API. The client is organized into four main modules that correspond to the Aurite API structure:

- **Execution**: Run agents and workflows
- **Host**: Manage MCP servers and tools
- **Config**: Manage configurations
- **System**: Monitor and manage the framework

## Installation

```bash
npm install @aurite/api-client
# or
yarn add @aurite/api-client
```

## Project Structure

```
src/
├── client/
│   ├── AuriteApiClient.ts      # Main client class
│   └── BaseClient.ts           # Base HTTP client
├── config/
│   └── environment.ts          # Environment variable loading
├── routes/
│   ├── ConfigManagerClient.ts  # Configuration management
│   ├── ExecutionFacadeClient.ts# Agent & workflow execution
│   ├── MCPHostClient.ts        # MCP server & tool management
│   └── SystemClient.ts         # System monitoring & management
├── types/
│   ├── api.ts                  # Core API types and errors
│   ├── requests.ts             # Request payload types
│   └── responses.ts            # Response payload types
└── utils/
    └── errorHandling.ts        # Utility functions
```

## Usage

### Basic Setup

```typescript
import { createAuriteClient } from '@aurite/api-client';

const client = createAuriteClient(
  process.env.AURITE_API_BASE_URL || 'http://localhost:8000',
  process.env.API_KEY || 'your-api-key'
);

// The client provides four sub-clients:
// - client.execution: for running agents and workflows
// - client.host: for managing MCP servers and tools
// - client.config: for managing configurations
// - client.system: for system monitoring and management
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

### Managing MCP Servers and Tools

```typescript
// List available tools
const tools = await client.host.listTools();

// Register a server
await client.host.registerServerByName('weather_server');
```

### Configuration Management

```typescript
// List configurations
const agents = await client.config.listConfigs('agent');

// Get a specific configuration
const agentConfig = await client.config.getConfig('agent', 'Weather Agent');
```

### System Management

```typescript
// Get framework version
const version = await client.system.getFrameworkVersion();

// Perform a comprehensive health check
const health = await client.system.comprehensiveHealthCheck();

// List active processes
const processes = await client.system.listActiveProcesses();
```

## API Reference

### Client Structure

The main client provides access to four sub-clients:

```typescript
const client = createAuriteClient(baseUrl, apiKey);

client.execution  // ExecutionFacadeClient
client.host       // MCPHostClient
client.config     // ConfigManagerClient
client.system     // SystemClient
```

### Client Methods

#### Execution (`client.execution`)
- `getStatus()` - Get the execution facade status
- `runAgent(name, request)` - Run an agent synchronously
- `streamAgent(name, request, onEvent)` - Stream agent responses
- `runSimpleWorkflow(name, request)` - Run a simple workflow
- `runCustomWorkflow(name, request)` - Run a custom workflow

#### Host (`client.host`)
- `getStatus()` - Get MCP host status and tool count
- `listTools()` - List all available tools
- `registerServerByName(name)` - Register a server by its configured name
- `registerServerByConfig(config)` - Register a server with a custom config
- `unregisterServer(name)` - Unregister a server
- `callTool(name, args)` - Call a tool directly

#### Config (`client.config`)
- `listConfigs(type)` - List all configs of a given type
- `getConfig(type, name)` - Get a specific configuration
- `createConfig(type, config)` - Create a new configuration
- `updateConfig(type, name, config)` - Update an existing configuration
- `deleteConfig(type, name)` - Delete a configuration
- `reloadConfigs()` - Reload all configurations from disk

#### System (`client.system`)
- `getSystemInfo()` - Get detailed system information
- `getFrameworkVersion()` - Get the framework version
- `getSystemCapabilities()` - Get system capabilities
- `getEnvironmentVariables()` - Get environment variables
- `updateEnvironmentVariables(vars)` - Update environment variables
- `listDependencies()` - List project dependencies
- `checkDependencyHealth()` - Check health of dependencies
- `getSystemMetrics()` - Get system performance metrics
- `listActiveProcesses()` - List active system processes
- `comprehensiveHealthCheck()` - Run a full health check

## Types

The client re-exports all necessary TypeScript interfaces for requests, responses, and core types.

**Core Types:**
- `ApiConfig`, `RequestOptions`, `ConfigType`, `ExecutionStatus`, `TransportType`, `LLMProvider`
- `ApiError`, `TimeoutError`, `CancellationError`

**Request Types:**
- `AgentRunRequest`, `WorkflowRunRequest`, `ToolCallArgs`
- `AgentConfig`, `LLMConfig`, `ServerConfig`

**Response Types:**
- `AgentRunResult`, `WorkflowExecutionResult`, `ToolCallResult`
- `StreamEvent`, `StreamingOptions`, `WorkflowStatus`, `StepStatus`
- `ServerDetailedStatus`, `ToolDetails`

## Examples

See the `examples/` directory for comprehensive usage examples.

## Development

To compile TypeScript:

```bash
npm run build
```

To run tests:

```bash
# Run all tests
npm test

# Run unit tests
npm run test:unit

# Run integration tests (requires running API)
npm run test:integration
