# Aurite API Client Examples

This directory contains comprehensive examples demonstrating how to use the Aurite API Client. The examples are organized by functionality and provide real-world usage patterns for building applications with the Aurite Framework.

## 📁 Directory Structure

```
frontend/packages/api-client/examples/
├── README.md                           # This overview document
├── shared/                             # Shared utilities and setup
│   └── client-setup.ts                # Common client initialization
├── execution/                          # Agent and workflow execution
│   ├── agent-basic.ts                 # Basic agent execution
│   ├── agent-streaming.ts             # Real-time streaming responses
│   ├── workflow-simple.ts             # Simple workflow execution
│   └── debug-planning-agent.ts        # Debug specific planning agent
├── mcp-host/                          # MCP server and tool management
│   ├── server-management.ts           # Register/unregister servers
│   └── tool-execution.ts              # Direct tool calls and analysis
├── config/                            # Configuration management
│   ├── config-listing.ts              # List and explore configurations
│   └── reload-configs.ts              # Reload configuration files
├── system/                            # System monitoring and health
│   └── health-check.ts                # System-level health monitoring
├── analyze-http-requests.ts           # HTTP request analysis and reporting
├── health-check.ts                    # API health checks and diagnostics
└── test-env.ts                        # Environment setup validation
```

## 🚀 Quick Start

### Prerequisites

1. **Aurite Server Running**: Ensure the Aurite server is running on `localhost:8000`
2. **API Key**: Have a valid API key for authentication
3. **Dependencies**: Install the required dependencies

```bash
cd frontend
npm install
npm run build
```

### Running Examples

Each example can be run independently:

```bash
# Development and Testing Tools
npx tsx examples/test-env.ts                    # Test environment setup
npx tsx examples/health-check.ts                # API health diagnostics
npx tsx examples/analyze-http-requests.ts       # HTTP request analysis

# Configuration Management
npx tsx examples/config/config-listing.ts       # List configurations
npx tsx examples/config/reload-configs.ts       # Reload configurations

# Agent and Workflow Execution
npx tsx examples/execution/agent-basic.ts       # Basic agent execution
npx tsx examples/execution/agent-streaming.ts   # Real-time streaming
npx tsx examples/execution/workflow-simple.ts   # Simple workflow
npx tsx examples/execution/debug-planning-agent.ts  # Debug specific agent

# MCP Host Management
npx tsx examples/mcp-host/server-management.ts  # Server management
npx tsx examples/mcp-host/tool-execution.ts     # Tool execution

# System Monitoring
npx tsx examples/system/health-check.ts         # System health check
```

## 📚 Example Categories

### 🛠️ Development & Testing Tools

Essential utilities for development, debugging, and testing:

#### **test-env.ts** - Environment Setup Validation
- Tests environment variable loading from multiple locations
- Validates API connectivity and authentication
- Provides clear diagnostics for setup issues
- Helps troubleshoot connection problems

**Key Features:**
- ✅ Multi-location .env file detection
- ✅ Environment variable validation
- ✅ API connectivity testing
- ✅ Authentication verification
- ✅ Clear error diagnostics

#### **health-check.ts** - API Health Diagnostics
- Comprehensive API health monitoring
- Tests all major API endpoints
- Validates service availability
- Provides system status overview

**Key Features:**
- ✅ Multi-endpoint health checks
- ✅ Service status monitoring
- ✅ Configuration availability testing
- ✅ Tool discovery validation
- ✅ Comprehensive error reporting

#### **analyze-http-requests.ts** - HTTP Request Analysis
- Intercepts and analyzes all HTTP requests from examples
- Generates detailed request/response reports
- Provides performance metrics and statistics
- Creates comprehensive analysis documentation

**Key Features:**
- ✅ Request/response interception
- ✅ Performance metrics tracking
- ✅ Endpoint usage statistics
- ✅ Detailed transaction logging
- ✅ Markdown report generation

### 🤖 Execution Examples (`execution/`)

These examples demonstrate how to run agents and workflows:

#### **agent-basic.ts** - Basic Agent Execution
- Simple agent execution with complete responses
- Session management and conversation history
- Different agent types and configurations
- Error handling for agent operations
- Execution status monitoring

**Key Features:**
- ✅ Basic agent execution
- ✅ Session-based conversation history
- ✅ Multiple agent types
- ✅ Comprehensive error handling
- ✅ Status monitoring

#### **agent-streaming.ts** - Real-time Streaming
- Real-time streaming of agent responses
- Event-driven architecture with proper event handling
- Advanced streaming with metrics and tracking
- Stream cancellation and timeout handling
- Concurrent streaming operations

**Key Features:**
- ✅ Real-time response streaming
- ✅ Event type handling (llm_response, tool_call, tool_output)
- ✅ Stream cancellation with AbortController
- ✅ Performance metrics and tracking
- ✅ Concurrent stream management

#### **workflow-simple.ts** - Simple Workflow Execution
- Sequential agent workflow execution
- Different input types and formats
- Workflow vs direct agent comparison
- Complex multi-step workflow handling
- Error handling and graceful degradation

**Key Features:**
- ✅ Sequential workflow execution
- ✅ Multiple input format handling
- ✅ Step-by-step result tracking
- ✅ Workflow comparison analysis
- ✅ Complex input processing

#### **debug-planning-agent.ts** - Debug Specific Agent
- Targeted debugging for specific agents
- Detailed conversation history analysis
- Step-by-step execution tracking
- Error diagnosis and troubleshooting

**Key Features:**
- ✅ Specific agent debugging
- ✅ Detailed conversation analysis
- ✅ Execution step tracking
- ✅ Error diagnosis tools

### 🔧 MCP Host Examples (`mcp-host/`)

These examples demonstrate MCP server and tool management:

#### **server-management.ts** - MCP Server Management
- Server registration by name (pre-configured)
- Server registration with custom configuration
- Server unregistration and cleanup
- Complete server lifecycle management
- Multiple server management
- Error handling scenarios

**Key Features:**
- ✅ Server registration (by name and config)
- ✅ Server unregistration
- ✅ Lifecycle management
- ✅ Multiple server handling
- ✅ Comprehensive error scenarios

#### **tool-execution.ts** - Direct Tool Calls
- Tool discovery and schema inspection
- Direct tool calls with various argument types
- Tool error handling and validation
- Concurrent tool execution
- Tool response analysis and performance testing

**Key Features:**
- ✅ Tool discovery and inspection
- ✅ Multiple argument types
- ✅ Concurrent tool execution
- ✅ Response format analysis
- ✅ Performance benchmarking

### ⚙️ Configuration Examples (`config/`)

These examples demonstrate configuration management:

#### **config-listing.ts** - Configuration Exploration
- List all configuration types
- Explore agent, LLM, and MCP server configurations
- Workflow configuration analysis
- Configuration search and filtering
- Summary and statistics
- Error handling for invalid configurations

**Key Features:**
- ✅ All configuration type listing
- ✅ Detailed configuration exploration
- ✅ Search and filtering capabilities
- ✅ Statistical summaries
- ✅ Comprehensive error handling

#### **reload-configs.ts** - Configuration Reloading
- Reload configuration files from disk
- Refresh configuration cache
- Handle configuration updates
- Validate configuration changes

**Key Features:**
- ✅ Configuration file reloading
- ✅ Cache refresh functionality
- ✅ Update validation
- ✅ Error handling for invalid configs

### 🔬 System Examples (`system/`)

These examples demonstrate system-level monitoring and health checks:

#### **health-check.ts** - System Health Monitoring
- System-level health checks
- Service availability monitoring
- Resource status validation
- Performance metrics collection

**Key Features:**
- ✅ System health monitoring
- ✅ Service availability checks
- ✅ Resource validation
- ✅ Performance metrics

## 🛠️ Shared Utilities (`shared/`)

### **client-setup.ts** - Common Setup
Provides shared utilities used across all examples:

- **`createExampleClient()`** - Pre-configured API client
- **`handleExampleError()`** - Consistent error handling
- **`runExample()`** - Example execution wrapper
- **`prettyPrint()`** - JSON formatting utility
- **`delay()`** - Async delay utility

## 📋 Example Patterns

### Basic Usage Pattern

```typescript
import { createExampleClient, runExample, handleExampleError } from '../shared/client-setup';

async function myExample() {
  const client = createExampleClient();

  try {
    // Your API calls here
    const result = await client.execution.runAgent('Weather Agent', {
      user_message: 'What is the weather?'
    });

    console.log('Result:', result);
  } catch (error) {
    handleExampleError(error, 'My Example');
  }
}

// Run with proper error handling and formatting
runExample('My Example', myExample);
```

### Error Handling Pattern

```typescript
try {
  const result = await client.someOperation();
  console.log('✅ Success:', result);
} catch (error) {
  console.log('❌ Expected error:');
  handleExampleError(error, 'Operation Name');
}
```

### Streaming Pattern

```typescript
await client.execution.streamAgent(
  'Agent Name',
  { user_message: 'Hello' },
  (event) => {
    switch (event.type) {
      case 'llm_response':
        process.stdout.write(event.data.content);
        break;
      case 'tool_call':
        console.log(`\n🔧 Tool: ${event.data.name}`);
        break;
      case 'error':
        console.error('❌ Error:', event.data.message);
        break;
    }
  }
);
```

## 🎯 Key API Client Features Demonstrated

### ✅ **Agent Execution**
- Basic execution with complete responses
- Session management and conversation history
- Real-time streaming with event handling
- Multiple agent types and configurations

### ✅ **Workflow Management**
- Simple sequential workflows
- Complex input processing
- Step-by-step result tracking
- Error handling and recovery

### ✅ **MCP Integration**
- Server registration and management
- Tool discovery and execution
- Direct tool calls with various arguments
- Concurrent operations and performance testing

### ✅ **Configuration Management**
- Complete configuration exploration
- Search and filtering capabilities
- Statistical analysis and summaries
- Configuration reloading and validation

### ✅ **Development Tools**
- Environment setup validation
- HTTP request analysis and reporting
- Health monitoring and diagnostics
- Comprehensive error handling

### ✅ **Error Handling**
- Comprehensive error categorization
- User-friendly error messages
- Retry logic and graceful degradation
- Professional error reporting

### ✅ **Performance Features**
- Concurrent operations
- Streaming with cancellation
- Performance metrics and benchmarking
- Resource management and cleanup

## 🔧 Configuration

### API Client Setup

The examples use a shared configuration in `shared/client-setup.ts`:

```typescript
export const DEFAULT_CONFIG = {
  baseUrl: process.env.AURITE_API_URL || 'http://localhost:8000',
  apiKey: process.env.API_KEY || 'your_test_key', // Example API key
};
```

**For production use:**
- Use environment variables for API keys
- Configure appropriate base URLs
- Implement proper authentication

### Environment Variables

Create a `.env` file in the frontend directory:

```bash
# API Configuration
AURITE_API_URL=http://localhost:8000
API_KEY=your_actual_api_key_here

# Optional: Development settings
NODE_ENV=development
```

### Server Requirements

The examples expect the following to be available:
- **Aurite Server** running on `localhost:8000`
- **Weather Agent** configured and available
- **Weather Server** MCP server configured
- **Planning Server** MCP server configured
- **Weather Planning Workflow** configured

## 📖 Learning Path

### 1. **Start with Setup and Validation**
   - `test-env.ts` - Validate your environment setup
   - `health-check.ts` - Check API connectivity and health
   - `config/config-listing.ts` - Explore available configurations

### 2. **Learn Basic Operations**
   - `execution/agent-basic.ts` - Learn basic agent execution
   - `config/reload-configs.ts` - Understand configuration management
   - `mcp-host/server-management.ts` - Basic MCP server operations

### 3. **Explore Advanced Features**
   - `execution/agent-streaming.ts` - Real-time streaming
   - `mcp-host/tool-execution.ts` - Direct tool operations
   - `execution/workflow-simple.ts` - Workflow execution

### 4. **Master Development Tools**
   - `analyze-http-requests.ts` - HTTP request analysis
   - `execution/debug-planning-agent.ts` - Debugging techniques
   - `system/health-check.ts` - System monitoring

### 5. **Build Applications**
   - Combine patterns from multiple examples
   - Implement error handling and user feedback
   - Add performance monitoring and optimization

## 🔍 Development Workflow

### Testing Your Setup
```bash
# 1. Test environment
npx tsx examples/test-env.ts

# 2. Check API health
npx tsx examples/health-check.ts

# 3. List available configurations
npx tsx examples/config/config-listing.ts
```

### Debugging Issues
```bash
# 1. Run HTTP analysis to see all requests
npx tsx examples/analyze-http-requests.ts

# 2. Debug specific agents
npx tsx examples/execution/debug-planning-agent.ts

# 3. Check system health
npx tsx examples/system/health-check.ts
```

### Performance Analysis
```bash
# Run HTTP analysis for detailed performance metrics
npx tsx examples/analyze-http-requests.ts
```

## 🤝 Contributing

When adding new examples:

1. **Follow the established patterns** in existing examples
2. **Use shared utilities** from `shared/client-setup.ts`
3. **Include comprehensive error handling** for all scenarios
4. **Add detailed comments** explaining the functionality
5. **Test with the live server** to ensure accuracy
6. **Update this README** with new example descriptions
7. **Consider adding to the HTTP analysis script** if it's a new category

## 📞 Support

For questions about the examples or API client:

1. **Check the main documentation** in `frontend/README.md`
2. **Review the API client source** in `frontend/packages/api-client/src/`
3. **Run the examples** against a live server for testing
4. **Use the development tools** (`test-env.ts`, `health-check.ts`) for diagnostics
5. **Examine error messages** for debugging information

## 🚨 Troubleshooting

### Common Issues

**Environment Setup:**
- Run `npx tsx examples/test-env.ts` to validate setup
- Check `.env` file location and format
- Verify API key and URL configuration

**API Connectivity:**
- Run `npx tsx examples/health-check.ts` for diagnostics
- Ensure Aurite server is running on the correct port
- Check firewall and network settings

**Configuration Issues:**
- Run `npx tsx examples/config/config-listing.ts` to see available configs
- Use `npx tsx examples/config/reload-configs.ts` to refresh configurations
- Check configuration file syntax and location

**Performance Issues:**
- Run `npx tsx examples/analyze-http-requests.ts` for detailed analysis
- Check network latency and server response times
- Monitor resource usage during execution

---

**Happy coding with the Aurite API Client! 🚀**
