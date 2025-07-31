# @aurite/api-client

A production-ready TypeScript client for the Aurite Framework API with comprehensive error handling, retry logic, and full type safety.

[![npm version](https://badge.fury.io/js/@aurite%2Fapi-client.svg)](https://badge.fury.io/js/@aurite%2Fapi-client)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔒 **Type Safety**: Full TypeScript support with comprehensive type definitions
- 🔄 **Retry Logic**: Intelligent retry mechanisms for network failures
- 🛡️ **Error Handling**: Comprehensive error categorization and handling
- 📊 **Streaming Support**: Real-time streaming for agent responses
- 🧪 **Testing**: Extensive unit and integration test coverage
- 📖 **Examples**: Comprehensive examples for all API endpoints
- 🚀 **Production Ready**: Built for production use with robust error handling

## Installation

### Option 1: Install as NPM Package

```bash
npm install @aurite/api-client
# or
yarn add @aurite/api-client
# or
pnpm add @aurite/api-client
```

### Option 2: Development within Workspace

If you're working within the Aurite Framework repository:

```bash
# Clone the repository
git clone https://github.com/aurite-ai/aurite-agents.git
cd aurite-agents/frontend

# Install dependencies for all packages
npm install

# Build all packages (required for workspace dependencies)
npm run build
```

## Quick Start

```typescript
import { createAuriteClient } from '@aurite/api-client';

// Create client instance
const client = createAuriteClient(
  process.env.AURITE_API_URL || 'http://localhost:8000',
  process.env.API_KEY || 'your-api-key'
);

// Run an agent
const result = await client.execution.runAgent('Weather Agent', {
  user_message: 'What is the weather in San Francisco?',
});

console.log(result.final_response?.content);
```

## API Structure

The client provides access to four main API modules:

### 🤖 Execution (`client.execution`)

Execute agents and workflows with streaming support.

```typescript
// Run an agent
const result = await client.execution.runAgent('Weather Agent', {
  user_message: 'What is the weather today?',
});

// Stream agent responses
await client.execution.streamAgent(
  'Weather Agent',
  { user_message: 'Tell me about the weather' },
  event => {
    if (event.type === 'llm_response') {
      console.log(event.data.content);
    }
  }
);

// Execute workflows
const workflowResult = await client.execution.runLinearWorkflow('Data Processing', {
  input_data: { source: 'api', format: 'json' },
});
```

### 🔧 Host (`client.host`)

Manage MCP servers and tools.

```typescript
// List available tools
const tools = await client.host.listTools();

// Register an MCP server
await client.host.registerServerByName('weather_server');

// Call a tool directly
const toolResult = await client.host.callTool('get_weather', {
  location: 'San Francisco',
});
```

### ⚙️ Config (`client.config`)

Manage configurations for agents, LLMs, and servers.

```typescript
// List all agent configurations
const agents = await client.config.listConfigs('agent');

// Get a specific configuration
const agentConfig = await client.config.getConfig('agent', 'Weather Agent');

// Create a new configuration
await client.config.createConfig('agent', {
  name: 'New Agent',
  llm: 'gpt-4',
  system_prompt: 'You are a helpful assistant.',
});
```

### 🔍 System (`client.system`)

Monitor system health and manage the framework.

```typescript
// Get system information
const systemInfo = await client.system.getSystemInfo();

// Check framework version
const version = await client.system.getFrameworkVersion();

// Perform health check
const health = await client.system.comprehensiveHealthCheck();
```

## Advanced Usage

### Error Handling

The client provides comprehensive error handling with categorized error types:

```typescript
import { ApiError, TimeoutError, CancellationError } from '@aurite/api-client';

try {
  const result = await client.execution.runAgent('Weather Agent', {
    user_message: 'What is the weather?',
  });
} catch (error) {
  if (error instanceof ApiError) {
    console.error('API Error:', error.message);
    console.error('Status:', error.status);
    console.error('Category:', error.category);
  } else if (error instanceof TimeoutError) {
    console.error('Request timed out:', error.message);
  } else if (error instanceof CancellationError) {
    console.error('Request was cancelled:', error.message);
  }
}
```

### Streaming Responses

Stream real-time responses from agents:

```typescript
await client.execution.streamAgent(
  'Weather Agent',
  { user_message: 'Tell me about the weather' },
  event => {
    switch (event.type) {
      case 'llm_response':
        console.log('LLM Response:', event.data.content);
        break;
      case 'tool_call':
        console.log('Tool Call:', event.data.name, event.data.arguments);
        break;
      case 'tool_result':
        console.log('Tool Result:', event.data.result);
        break;
      case 'error':
        console.error('Stream Error:', event.data.message);
        break;
    }
  }
);
```

### Custom Configuration

Configure the client with custom options:

```typescript
import { createAuriteClient } from '@aurite/api-client';

const client = createAuriteClient('http://localhost:8000', 'your-api-key', {
  timeout: 30000, // 30 second timeout
  retryAttempts: 3, // Retry failed requests 3 times
  retryDelay: 1000, // Wait 1 second between retries
  headers: {
    // Custom headers
    'User-Agent': 'MyApp/1.0.0',
  },
});
```

## Examples

The package includes comprehensive examples in the `examples/` directory:

### Running Examples

```bash
# Run basic examples
npm run example

# Run integration tests (requires running API server)
npm run example:integration
```

### Example Categories

- **Configuration Management**: `examples/config/`
  - List and manage configurations
  - Create and update agent configs
  - Reload configurations

- **Agent Execution**: `examples/execution/`
  - Basic agent execution
  - Streaming responses
  - Debug and troubleshooting

- **Workflow Management**: `examples/execution/`
  - Simple workflow execution
  - Custom workflow handling

- **MCP Server Management**: `examples/mcp-host/`
  - Server registration
  - Tool management and execution

- **System Operations**: `examples/system/`
  - Health checks
  - System information retrieval

## Development

### Setup

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Environment Variables

Create a `.env` file:

```bash
# API Configuration
AURITE_API_URL=http://localhost:8000
API_KEY=your_api_key_here

# Environment
NODE_ENV=development
```

### Workspace Development

When developing within the Aurite Framework workspace, you can also run examples and tests from the frontend root:

```bash
# From frontend root directory
npm run example --workspace=packages/api-client
npm run test:integration --workspace=packages/api-client
```

### Building

```bash
# Build the package
npm run build

# Build in watch mode
npm run dev

# Clean build artifacts
npm run clean
```

### Testing

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Run only unit tests
npm run test:unit

# Run only integration tests (requires API server)
npm run test:integration
```

### Code Quality

```bash
# Lint code
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format

# Check formatting
npm run format:check

# Type check
npm run typecheck

# Validate everything
npm run validate
```

## API Reference

### Client Creation

```typescript
createAuriteClient(baseUrl: string, apiKey: string, options?: ClientOptions): AuriteApiClient
```

### Client Methods

#### Execution Client (`client.execution`)

- `getStatus()` - Get execution facade status
- `runAgent(name, request)` - Run an agent synchronously
- `streamAgent(name, request, onEvent)` - Stream agent responses
- `runLinearWorkflow(name, request)` - Run a linear workflow
- `runCustomWorkflow(name, request)` - Run a custom workflow

#### Host Client (`client.host`)

- `getStatus()` - Get MCP host status
- `listTools()` - List all available tools
- `registerServerByName(name)` - Register a server by name
- `registerServerByConfig(config)` - Register a server with custom config
- `unregisterServer(name)` - Unregister a server
- `callTool(name, args)` - Call a tool directly

#### Config Client (`client.config`)

- `listConfigs(type)` - List configurations by type
- `getConfig(type, name)` - Get a specific configuration
- `createConfig(type, config)` - Create a new configuration
- `updateConfig(type, name, config)` - Update a configuration
- `deleteConfig(type, name)` - Delete a configuration
- `reloadConfigs()` - Reload configurations from disk

#### System Client (`client.system`)

- `getSystemInfo()` - Get detailed system information
- `getFrameworkVersion()` - Get framework version
- `getSystemCapabilities()` - Get system capabilities
- `getEnvironmentVariables()` - Get environment variables
- `updateEnvironmentVariables(vars)` - Update environment variables
- `listDependencies()` - List project dependencies
- `checkDependencyHealth()` - Check dependency health
- `getSystemMetrics()` - Get system performance metrics
- `listActiveProcesses()` - List active processes
- `comprehensiveHealthCheck()` - Run full health check

## Type Definitions

The client exports comprehensive TypeScript types:

### Core Types

- `ApiConfig` - Client configuration options
- `RequestOptions` - Request-specific options
- `ConfigType` - Configuration type enumeration
- `ExecutionStatus` - Execution status enumeration

### Request Types

- `AgentRunRequest` - Agent execution request
- `WorkflowRunRequest` - Workflow execution request
- `ToolCallArgs` - Tool call arguments

### Response Types

- `AgentRunResult` - Agent execution result
- `WorkflowExecutionResult` - Workflow execution result
- `StreamEvent` - Streaming event types
- `ToolCallResult` - Tool call result

### Error Types

- `ApiError` - API-related errors
- `TimeoutError` - Request timeout errors
- `CancellationError` - Request cancellation errors

## Troubleshooting

### Common Issues

**Connection Errors:**

```typescript
// Ensure the API server is running and accessible
const client = createAuriteClient('http://localhost:8000', 'your-key');
try {
  await client.system.getFrameworkVersion();
} catch (error) {
  console.error('Connection failed:', error.message);
}
```

**Authentication Errors:**

```typescript
// Verify your API key is correct
const client = createAuriteClient(baseUrl, 'correct-api-key');
```

**Timeout Issues:**

```typescript
// Increase timeout for long-running operations
const client = createAuriteClient(baseUrl, apiKey, {
  timeout: 60000, // 60 seconds
});
```

### Debug Mode

Enable debug logging:

```typescript
// Set environment variable
process.env.DEBUG = 'aurite:*';

// Or enable in code
const client = createAuriteClient(baseUrl, apiKey, {
  debug: true,
});
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes with tests
4. Run validation: `npm run validate`
5. Commit your changes: `git commit -am 'Add new feature'`
6. Push to the branch: `git push origin feature/new-feature`
7. Submit a pull request

### Development Guidelines

- Write TypeScript with strict type checking
- Include comprehensive tests for new features
- Follow the existing code style (ESLint + Prettier)
- Update documentation for new features
- Maintain backwards compatibility

## License

MIT License - see [LICENSE](../../LICENSE) file for details.

## Links

- **Repository**: [https://github.com/aurite-ai/aurite-agents](https://github.com/aurite-ai/aurite-agents)
- **Documentation**: [https://github.com/aurite-ai/aurite-agents](https://github.com/aurite-ai/aurite-agents)
- **NPM Package**: [https://www.npmjs.com/package/@aurite/api-client](https://www.npmjs.com/package/@aurite/api-client)
- **Issues**: [GitHub Issues](https://github.com/aurite-ai/aurite-agents/issues)
- **API Reference**: [API Documentation](../../../docs/usage/api_reference.md)

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history and changes.
