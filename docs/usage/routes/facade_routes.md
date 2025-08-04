# Execution Facade API Routes

This document provides detailed information about the Execution Facade API endpoints, including request/response schemas, streaming event types, session management, and examples.

## Overview

The Execution Facade API provides unified endpoints for executing agents and workflows within the Aurite Framework. It handles agent conversations (both synchronous and streaming), workflow execution, session management with history persistence, and automatic MCP server registration.

## Base Path

All execution endpoints are prefixed with `/execution/`.

## Key Features

- **Agent Execution**: Run agents with user messages, optional system prompts, and session management
- **Streaming Support**: Real-time streaming of agent responses via Server-Sent Events (SSE)
- **Workflow Execution**: Execute both linear (sequential) and custom (Python-based) workflows
- **Session Management**: Automatic conversation history loading and persistence
- **JIT MCP Server Registration**: Automatic registration of required MCP servers at runtime

## Agent Execution

### Run Agent (Synchronous)

`POST /execution/agents/{agent_name}/run`

Executes an agent synchronously and returns the complete result after all processing is finished.

**Parameters:**

- `agent_name` (path): The name of the agent to execute

**Request Body:**

```json
{
  "user_message": "string", // Required: The user's input message
  "system_prompt": "string", // Optional: Override the agent's system prompt
  "session_id": "string" // Optional: Session ID for conversation history
}
```

**Response:**

```json
{
  "status": "success | error | max_iterations_reached",
  "final_response": {
    "role": "assistant",
    "content": "string",
    "tool_calls": [] // If tools were used
  },
  "conversation_history": [
    // Full conversation including tool interactions
    {
      "role": "user | assistant | tool",
      "content": "string or structured content"
    }
  ],
  "error_message": "string" // Present only if status is "error"
}
```

**Session Management:**

- If `session_id` is provided and the agent has `include_history: true` in its configuration:
  - Previous conversation history is loaded before execution
  - The current user message is immediately added to the session
  - Full conversation history is saved after execution completes
- History is stored in either:
  - **StorageManager**: Persistent database storage (if configured)
  - **CacheManager**: In-memory storage (fallback when DB not configured)

### Stream Agent (Server-Sent Events)

`POST /execution/agents/{agent_name}/stream`

Executes an agent and streams the response in real-time using Server-Sent Events (SSE).

**Parameters:**

- `agent_name` (path): The name of the agent to execute

**Request Body:**
Same as synchronous execution:

```json
{
  "user_message": "string",
  "system_prompt": "string", // Optional
  "session_id": "string" // Optional
}
```

**Response:**
Server-Sent Events stream with the following event types:

#### Event Types

##### `llm_response_start`

Indicates the LLM has started generating a response.

```
data: {"type": "llm_response_start", "data": {}}
```

##### `llm_response`

Contains text chunks as the LLM generates its response.

```
data: {"type": "llm_response", "data": {"content": "partial response text"}}
```

##### `llm_response_stop`

Indicates the LLM has finished generating its response.

```
data: {"type": "llm_response_stop", "data": {}}
```

##### `tool_call`

Indicates a tool is being invoked by the agent.

```
data: {
  "type": "tool_call",
  "data": {
    "name": "weather_tool",
    "input": {"location": "New York", "units": "fahrenheit"}
  }
}
```

##### `tool_output`

Contains the result of a tool execution.

```
data: {
  "type": "tool_output",
  "data": {
    "name": "weather_tool",
    "output": "The current temperature in New York is 72°F"
  }
}
```

##### `error`

Indicates an error occurred during execution.

```
data: {
  "type": "error",
  "data": {
    "message": "Error description"
  }
}
```

**Session Management:**
Same behavior as synchronous execution - history is loaded at start and saved at completion.

**Error Handling:**

- Errors during streaming are sent as `error` events
- The stream is terminated after an error event
- HTTP 500 status code is set for the streaming response on errors

## Workflow Execution

### Run Linear Workflow

`POST /execution/workflows/linear/{workflow_name}/run`

Executes a linear (sequential) workflow with the provided initial input.

**Parameters:**

- `workflow_name` (path): The name of the linear workflow to execute

**Request Body:**

```json
{
  "initial_input": "any", // Required: Input data for the workflow
  "session_id": "string" // Optional: Currently not used for linear workflows
}
```

**Response:**

```json
{
  "status": "completed | failed",
  "final_output": "any", // The output from the last step
  "step_outputs": [
    // Outputs from each step in sequence
    {
      "step_name": "string",
      "output": "any",
      "error": "string" // If step failed
    }
  ],
  "error": "string" // If workflow failed
}
```

### Run Custom Workflow

`POST /execution/workflows/custom/{workflow_name}/run`

Executes a custom (Python-based) workflow with the provided initial input.

**Parameters:**

- `workflow_name` (path): The name of the custom workflow to execute

**Request Body:**

```json
{
  "initial_input": "any", // Required: Input data for the workflow
  "session_id": "string" // Optional: Passed to workflow implementation
}
```

**Response:**
The response format is dynamic and depends on the custom workflow implementation. The workflow's Python code determines the structure of the returned data.

**Session Support:**
The `session_id` is passed to the custom workflow executor, allowing workflow implementations to maintain state across executions if needed.

## Status Endpoint

### Get Execution Facade Status

`GET /execution/status`

Returns the current status of the Execution Facade.

**Response:**

```json
{
  "status": "active"
}
```

**Purpose:**

- Health check for monitoring
- Verify the execution facade is operational
- Future: Could include additional metrics

## History Management Endpoints

### List All Sessions

`GET /execution/history`

Lists all conversation sessions with optional filtering and pagination.

**Query Parameters:**

- `agent_name` (optional): Filter sessions by agent name
- `limit` (optional, default=50): Maximum number of sessions to return (1-100)
- `offset` (optional, default=0): Number of sessions to skip for pagination

**Response:**

```json
{
  "sessions": [
    {
      "session_id": "user123-chat-001",
      "agent_name": "assistant",
      "created_at": "2024-01-15T10:30:00Z",
      "last_updated": "2024-01-15T11:45:00Z",
      "message_count": 12
    }
  ],
  "total": 25,
  "offset": 0,
  "limit": 50
}
```

### Get Session History

`GET /execution/history/{session_id}`

Retrieves the full conversation history for a specific session.

**Parameters:**

- `session_id` (path): The session identifier

**Query Parameters:**

- `raw_format` (optional, default=false): Return raw Anthropic format instead of simplified view

**Response (Simplified Format):**

```json
{
  "session_id": "user123-chat-001",
  "agent_name": "assistant",
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?",
      "timestamp": null
    },
    {
      "role": "assistant",
      "content": "Hello! I'm doing well, thank you for asking. How can I help you today?",
      "timestamp": null
    }
  ],
  "metadata": {
    "session_id": "user123-chat-001",
    "agent_name": "assistant",
    "created_at": "2024-01-15T10:30:00Z",
    "last_updated": "2024-01-15T11:45:00Z",
    "message_count": 2
  }
}
```

**Response (Raw Format with `raw_format=true`):**

```json
{
  "session_id": "user123-chat-001",
  "agent_name": "assistant",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Hello, how are you?"
        }
      ],
      "timestamp": null
    },
    {
      "role": "assistant",
      "content": [
        {
          "type": "text",
          "text": "Hello! I'm doing well, thank you for asking. How can I help you today?"
        }
      ],
      "timestamp": null
    }
  ],
  "metadata": {
    "session_id": "user123-chat-001",
    "agent_name": "assistant",
    "created_at": "2024-01-15T10:30:00Z",
    "last_updated": "2024-01-15T11:45:00Z",
    "message_count": 2
  }
}
```

### Delete Session

`DELETE /execution/history/{session_id}`

Deletes a specific session and all its conversation history.

**Parameters:**

- `session_id` (path): The session identifier to delete

**Response:**

- **204 No Content**: Session successfully deleted
- **404 Not Found**: Session does not exist

### Get Agent History

`GET /execution/agents/{agent_name}/history`

Retrieves all sessions for a specific agent.

**Parameters:**

- `agent_name` (path): The name of the agent

**Query Parameters:**

- `limit` (optional, default=50): Maximum number of sessions to return (1-100)

**Response:**
Same format as `GET /execution/history` but filtered to only show sessions for the specified agent.

### Clean Up History

`POST /execution/history/cleanup`

Manually triggers cleanup of old sessions based on retention policy.

**Query Parameters:**

- `days` (optional, default=30): Delete sessions older than this many days (1-365)
- `max_sessions` (optional, default=50): Maximum number of sessions to keep (1-1000)

**Response:**

```json
{
  "message": "Cleanup completed. Removed sessions older than 30 days, keeping maximum 50 sessions."
}
```

**Note:** Cleanup is automatically triggered when listing sessions, but this endpoint allows manual cleanup with custom parameters.

## Session Management

When using agents with session support, the framework automatically handles conversation history:

- **Session ID**: Include a `session_id` in your request to maintain conversation context
- **History Loading**: If the agent has `include_history: true`, previous messages are loaded
- **Persistence**: History is saved after each execution for future reference

**Note**: For detailed information about session management architecture and storage backends, see [Execution Facade Architecture](../../architecture/design/execution_facade.md).

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Successful execution
- **404 Not Found**: Agent or workflow configuration not found
- **500 Internal Server Error**: Execution errors, MCP server issues

### Error Response Format

All error responses follow this format:

```json
{
  "detail": "Detailed error message describing what went wrong"
}
```

### Common Error Scenarios

#### Configuration Not Found

**Status**: 404

```json
{
  "detail": "Agent configuration 'unknown_agent' not found."
}
```

#### Missing LLM Configuration

**Status**: 500

```json
{
  "detail": "LLM configuration 'gpt-4' not found."
}
```

#### MCP Server Registration Failure

**Status**: 500

```json
{
  "detail": "MCP Server 'weather_server' required by agent 'weather_bot' not found."
}
```

#### Execution Errors

**Status**: 500

```json
{
  "detail": "Unexpected error in ExecutionFacade while running Agent 'assistant': ConnectionError: Failed to connect to LLM provider"
}
```

### Streaming Error Handling

For streaming endpoints, errors are handled differently:

1. **Pre-Stream Errors**: Return HTTP error status with JSON error response
2. **Mid-Stream Errors**: Send error event in SSE stream:
   ```
   data: {"type": "error", "data": {"message": "Tool execution failed: weather_tool"}}
   ```
3. **Connection Handling**: Stream terminates after error event

## Examples

### Basic Agent Execution

**Request:**

```bash
POST /execution/agents/weather_assistant/run
Content-Type: application/json
X-API-Key: your-api-key

{
  "user_message": "What's the weather like in San Francisco?"
}
```

**Response:**

```json
{
  "status": "success",
  "final_response": {
    "role": "assistant",
    "content": "The current weather in San Francisco is partly cloudy with a temperature of 65°F (18°C). It's a pleasant day with light winds from the west at 10 mph."
  },
  "conversation_history": [
    {
      "role": "user",
      "content": "What's the weather like in San Francisco?"
    },
    {
      "role": "assistant",
      "tool_calls": [
        {
          "id": "call_abc123",
          "function": {
            "name": "get_weather",
            "arguments": "{\"location\": \"San Francisco, CA\"}"
          },
          "type": "function"
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "content": "{\"temperature\": 65, \"condition\": \"partly cloudy\", \"wind\": \"10 mph W\"}"
    },
    {
      "role": "assistant",
      "content": "The current weather in San Francisco is partly cloudy with a temperature of 65°F (18°C). It's a pleasant day with light winds from the west at 10 mph."
    }
  ],
  "error_message": null
}
```

### Agent with Session Management

**Request:**

```bash
POST /execution/agents/personal_assistant/run
Content-Type: application/json
X-API-Key: your-api-key

{
  "user_message": "Remember when we discussed my trip to Paris?",
  "session_id": "user123-europe-trip"
}
```

**Response:**

```json
{
  "status": "success",
  "final_response": {
    "role": "assistant",
    "content": "Yes, I remember our conversation about your trip to Paris! You mentioned you were planning to visit in the spring and were particularly interested in seeing the Louvre and trying authentic French pastries. How did your trip go?"
  },
  "conversation_history": [
    // Previous messages loaded from session
    {
      "role": "user",
      "content": "I'm planning a trip to Paris in the spring"
    },
    {
      "role": "assistant",
      "content": "That sounds wonderful! Paris in spring is beautiful..."
    },
    // Current interaction
    {
      "role": "user",
      "content": "Remember when we discussed my trip to Paris?"
    },
    {
      "role": "assistant",
      "content": "Yes, I remember our conversation about your trip to Paris! You mentioned you were planning to visit in the spring and were particularly interested in seeing the Louvre and trying authentic French pastries. How did your trip go?"
    }
  ]
}
```

### Streaming Agent Execution

**Request:**

```bash
POST /execution/agents/code_assistant/stream
Content-Type: application/json
X-API-Key: your-api-key

{
  "user_message": "Write a Python function to calculate fibonacci numbers",
  "system_prompt": "You are an expert Python developer. Provide clean, efficient code with explanations."
}
```

**Response (Server-Sent Events):**

````
data: {"type": "llm_response_start", "data": {}}

data: {"type": "llm_response", "data": {"content": "I'll help you create"}}

data: {"type": "llm_response", "data": {"content": " an efficient Python function"}}

data: {"type": "llm_response", "data": {"content": " to calculate Fibonacci numbers.\n\n"}}

data: {"type": "llm_response", "data": {"content": "Here's an implementation"}}

data: {"type": "llm_response", "data": {"content": " using dynamic programming:\n\n```python\n"}}

data: {"type": "llm_response", "data": {"content": "def fibonacci(n):\n"}}

data: {"type": "llm_response", "data": {"content": "    \"\"\"\n    Calculate the nth Fibonacci number.\n    \n    Args:\n        n: The position in the Fibonacci sequence (0-indexed)\n    \n    Returns:\n        The nth Fibonacci number\n    \"\"\"\n"}}

data: {"type": "llm_response", "data": {"content": "    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    \n    # Use dynamic programming for efficiency\n    fib_prev, fib_curr = 0, 1\n    \n    for _ in range(2, n + 1):\n        fib_prev, fib_curr = fib_curr, fib_prev + fib_curr\n    \n    return fib_curr\n```\n\n"}}

data: {"type": "llm_response", "data": {"content": "This implementation has O(n) time complexity and O(1) space complexity."}}

data: {"type": "llm_response_stop", "data": {}}
````

### Linear Workflow Execution

**Request:**

```bash
POST /execution/workflows/linear/data_processing_pipeline/run
Content-Type: application/json
X-API-Key: your-api-key

{
  "initial_input": {
    "data_source": "sales_2024.csv",
    "output_format": "summary_report"
  }
}
```

**Response:**

```json
{
  "status": "completed",
  "final_output": {
    "report_url": "https://reports.example.com/sales_2024_summary.pdf",
    "total_sales": 1250000,
    "top_products": ["Product A", "Product B", "Product C"]
  },
  "step_outputs": [
    {
      "step_name": "load_data",
      "output": {
        "rows_loaded": 10000,
        "columns": ["date", "product", "amount"]
      }
    },
    {
      "step_name": "validate_data",
      "output": { "valid_rows": 9950, "errors": 50 }
    },
    {
      "step_name": "analyze_sales",
      "output": { "total": 1250000, "average": 125.63 }
    },
    {
      "step_name": "generate_report",
      "output": {
        "report_url": "https://reports.example.com/sales_2024_summary.pdf"
      }
    }
  ]
}
```

### Custom Workflow Execution

**Request:**

```bash
POST /execution/workflows/custom/ml_training_pipeline/run
Content-Type: application/json
X-API-Key: your-api-key

{
  "initial_input": {
    "dataset": "customer_churn.csv",
    "model_type": "random_forest",
    "hyperparameters": {
      "n_estimators": 100,
      "max_depth": 10
    }
  },
  "session_id": "training-session-2024-01"
}
```

**Response (Dynamic based on workflow):**

```json
{
  "model_id": "rf_model_20240115_143022",
  "metrics": {
    "accuracy": 0.92,
    "precision": 0.89,
    "recall": 0.94,
    "f1_score": 0.91
  },
  "training_time_seconds": 45.3,
  "feature_importance": {
    "account_age": 0.25,
    "monthly_charges": 0.22,
    "total_charges": 0.18,
    "contract_type": 0.15
  },
  "saved_to": "models/rf_model_20240115_143022.pkl"
}
```

## Best Practices

1. **Session Management**:

   - Use consistent session IDs for conversation continuity
   - Include user identifiers in session IDs for multi-user scenarios
   - Consider session expiration policies

2. **Streaming vs Synchronous**:

   - Use streaming for interactive chat interfaces
   - Use synchronous for batch processing or API integrations
   - Handle SSE reconnection in client applications

3. **Error Handling**:

   - Implement retry logic for transient failures
   - Log session IDs for debugging conversation issues
   - Monitor for max iteration warnings

4. **System Prompts**:

   - Use system prompt overrides sparingly
   - Prefer configuring prompts in agent definitions
   - Document prompt changes for debugging

5. **Workflow Design**:
   - Keep linear workflows for linear processes
   - Use custom workflows for complex logic
   - Pass session IDs to maintain workflow state
