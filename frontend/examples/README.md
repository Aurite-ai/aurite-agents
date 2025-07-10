# Aurite API Client Examples

This directory contains comprehensive examples demonstrating how to use the Aurite API Client. The examples are organized by functionality and provide real-world usage patterns for building applications with the Aurite Framework.

## 📁 Directory Structure

```
frontend/examples/
├── README.md                    # This overview document
├── shared/                      # Shared utilities and setup
│   └── client-setup.ts         # Common client initialization
├── execution/                   # Agent and workflow execution
│   ├── agent-basic.ts          # Basic agent execution
│   ├── agent-streaming.ts      # Real-time streaming responses
│   └── workflow-simple.ts      # Simple workflow execution
├── mcp-host/                   # MCP server and tool management
│   ├── server-management.ts   # Register/unregister servers
│   └── tool-execution.ts      # Direct tool calls and analysis
└── config/                     # Configuration management
    └── config-listing.ts      # List and explore configurations
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
# Run a specific example
npx tsx examples/execution/agent-basic.ts

# Run all examples in a category
npx tsx examples/execution/agent-streaming.ts
npx tsx examples/mcp-host/server-management.ts
npx tsx examples/config/config-listing.ts
```

## 📚 Example Categories

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
- Error handling for edge cases

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
  baseUrl: process.env.EXAMPLE_API_BASE_URL || 'http://localhost:8000',
  apiKey: process.env.EXAMPLE_API_KEY || 'your_test_key', // Example API key
};
```

**For production use:**
- Use environment variables for API keys
- Configure appropriate base URLs
- Implement proper authentication

### Server Requirements

The examples expect the following to be available:
- **Aurite Server** running on `localhost:8000`
- **Weather Agent** configured and available
- **Weather Server** MCP server configured
- **Planning Server** MCP server configured
- **Weather Planning Workflow** configured

## 📖 Learning Path

### 1. **Start with Basics**
   - `execution/agent-basic.ts` - Learn basic agent execution
   - `config/config-listing.ts` - Explore available configurations

### 2. **Explore Advanced Features**
   - `execution/agent-streaming.ts` - Real-time streaming
   - `mcp-host/server-management.ts` - MCP server management

### 3. **Master Complex Operations**
   - `execution/workflow-simple.ts` - Workflow execution
   - `mcp-host/tool-execution.ts` - Direct tool operations

### 4. **Build Applications**
   - Combine patterns from multiple examples
   - Implement error handling and user feedback
   - Add performance monitoring and optimization

## 🤝 Contributing

When adding new examples:

1. **Follow the established patterns** in existing examples
2. **Use shared utilities** from `shared/client-setup.ts`
3. **Include comprehensive error handling** for all scenarios
4. **Add detailed comments** explaining the functionality
5. **Test with the live server** to ensure accuracy
6. **Update this README** with new example descriptions

## 📞 Support

For questions about the examples or API client:

1. **Check the main documentation** in `frontend/README.md`
2. **Review the API client source** in `frontend/src/`
3. **Run the examples** against a live server for testing
4. **Examine error messages** for debugging information

---

**Happy coding with the Aurite API Client! 🚀**
