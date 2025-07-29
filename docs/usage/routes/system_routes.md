# System Management Routes Documentation

## Overview

The System Management routes (`/system/*`) provide comprehensive system information, monitoring, and health check capabilities for the Aurite Framework. These endpoints enable:

- **System Information**: Hardware, OS, and Python environment details
- **Framework Information**: Version, capabilities, and feature availability
- **Environment Management**: View and update environment variables
- **Dependency Management**: List and check health of Python dependencies
- **Real-time Monitoring**: System metrics, log streaming, and process monitoring
- **Health Checks**: Comprehensive health status of all framework components

### Key Features

- **Security**: Sensitive environment variables are automatically masked
- **Graceful Degradation**: Works with or without optional dependencies (e.g., psutil)
- **Real-time Updates**: SSE-based log streaming for live monitoring
- **Comprehensive Health**: Multi-component health check with detailed status

## API Endpoints

### System Information

#### Get System Info

```http
GET /system/info
```

Returns detailed system information including platform, Python version, and hardware details.

**Response:**

```json
{
  "platform": "Linux",
  "platform_version": "5.15.0-91-generic",
  "python_version": "3.11.7",
  "python_implementation": "CPython",
  "hostname": "aurite-server",
  "cpu_count": 8,
  "architecture": "x86_64",
  "os_details": {
    "system": "Linux",
    "release": "5.15.0-91-generic",
    "version": "#101-Ubuntu SMP",
    "machine": "x86_64",
    "processor": "x86_64"
  }
}
```

#### Get Framework Version

```http
GET /system/version
```

Returns Aurite Framework version and metadata.

**Response:**

```json
{
  "version": "0.3.26",
  "name": "Aurite Agents",
  "description": "Aurite Agents is an agent development and runtime framework.",
  "authors": ["Ryan W", "Blake R", "Patrick W", "Jiten O"],
  "license": "MIT",
  "repository": "https://github.com/Aurite-ai/aurite-agents",
  "python_requirement": ">=3.11,<4.0.0"
}
```

#### Get System Capabilities

```http
GET /system/capabilities
```

Lists available features and supported providers.

**Response:**

```json
{
  "mcp_support": true,
  "api_enabled": true,
  "cli_enabled": true,
  "tui_enabled": true,
  "available_transports": ["stdio", "local", "http_stream"],
  "supported_llm_providers": [
    "openai",
    "anthropic",
    "azure",
    "google",
    "cohere",
    "replicate",
    "huggingface",
    "together_ai",
    "openrouter",
    "vertex_ai",
    "bedrock",
    "ollama",
    "groq",
    "deepseek"
  ],
  "storage_backends": ["sqlite", "json", "redis", "postgresql"],
  "optional_features": {
    "pandas": true,
    "sentence_transformers": false,
    "ml_support": false,
    "redis_cache": false,
    "postgresql": false,
    "mem0_memory": false
  }
}
```

### Environment Management

#### List Environment Variables

```http
GET /system/environment
```

Returns all environment variables with sensitive values masked.

**Response:**

```json
[
  {
    "name": "PATH",
    "value": "/usr/local/bin:/usr/bin:/bin",
    "is_sensitive": false
  },
  {
    "name": "API_KEY",
    "value": "***MASKED***",
    "is_sensitive": true
  }
]
```

**Security Note**: Variables containing patterns like KEY, SECRET, PASSWORD, TOKEN, CREDENTIAL, AUTH, or PRIVATE are automatically masked.

#### Update Environment Variables

```http
PUT /system/environment
```

Updates environment variables (sensitive variables cannot be updated).

**Request Body:**

```json
{
  "variables": {
    "LOG_LEVEL": "DEBUG",
    "CUSTOM_VAR": "value"
  }
}
```

**Response:**

```json
{
  "updated": ["LOG_LEVEL", "CUSTOM_VAR"],
  "errors": [],
  "status": "success"
}
```

**Error Response (attempting to update sensitive variable):**

```json
{
  "updated": ["LOG_LEVEL"],
  "errors": ["Cannot update sensitive variable: API_KEY"],
  "status": "partial"
}
```

### Dependency Management

#### List All Dependencies

```http
GET /system/dependencies
```

Lists all installed Python packages with metadata.

**Response:**

```json
[
  {
    "name": "fastapi",
    "version": "0.115.14",
    "location": null,
    "summary": "FastAPI framework, high performance, easy to learn"
  },
  {
    "name": "pydantic",
    "version": "2.11.7",
    "location": null,
    "summary": "Data validation using Python type hints"
  }
]
```

#### Check Dependency Health

```http
POST /system/dependencies/check
```

Checks the health of critical framework dependencies.

**Response:**

```json
[
  {
    "name": "mcp",
    "installed": true,
    "version": "1.10.1",
    "importable": true,
    "error": null
  },
  {
    "name": "psutil",
    "installed": false,
    "version": null,
    "importable": false,
    "error": "Package not found"
  }
]
```

### Real-time Monitoring

#### Get System Metrics

```http
GET /system/monitoring/metrics
```

Returns current system metrics including CPU, memory, and disk usage.

**Response (with psutil):**

```json
{
  "timestamp": "2025-01-09T16:45:00Z",
  "cpu_percent": 15.2,
  "memory_usage": {
    "total": 16777216000,
    "available": 8388608000,
    "percent": 50.0,
    "used": 8388608000,
    "free": 8388608000
  },
  "disk_usage": {
    "total": 500000000000,
    "used": 250000000000,
    "free": 250000000000,
    "percent": 50.0
  },
  "process_info": {
    "pid": 12345,
    "cpu_percent": 2.5,
    "memory_percent": 1.2,
    "memory_info": {
      "rss": 104857600,
      "vms": 209715200
    },
    "num_threads": 10
  },
  "python_info": {
    "gc_counts": [700, 70, 7],
    "gc_stats": [...],
    "thread_count": 5
  }
}
```

**Response (without psutil - graceful degradation):**

```json
{
  "timestamp": "2025-01-09T16:45:00Z",
  "cpu_percent": 0.0,
  "memory_usage": {
    "max_rss": 104857600,
    "percent": 0.0
  },
  "disk_usage": {"percent": 0.0},
  "process_info": {
    "pid": 12345,
    "user_time": 1.234,
    "system_time": 0.567
  },
  "python_info": {
    "gc_counts": [700, 70, 7],
    "gc_stats": [...],
    "thread_count": 5
  }
}
```

#### Stream Logs (SSE)

```http
GET /system/monitoring/logs
```

Streams logs in real-time using Server-Sent Events.

**Response Headers:**

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Response Stream:**

```
data: {'type': 'connected', 'message': 'Log stream connected'}

data: {'type': 'log', 'message': '2025-01-09 16:45:00 - aurite.api - INFO - Request received'}

data: {'type': 'heartbeat', 'timestamp': '2025-01-09T16:45:01Z'}

data: {'type': 'log', 'message': '2025-01-09 16:45:02 - aurite.execution - DEBUG - Agent execution started'}
```

**Client Example (JavaScript):**

```javascript
const eventSource = new EventSource("/system/monitoring/logs", {
  headers: { "X-API-Key": "your-api-key" },
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "log") {
    console.log("Log:", data.message);
  }
};
```

#### List Active Processes

```http
GET /system/monitoring/active
```

Lists Aurite-related processes and their children.

**Response:**

```json
[
  {
    "name": "python",
    "pid": 12345,
    "status": "running",
    "cpu_percent": 2.5,
    "memory_percent": 1.2,
    "create_time": "2025-01-09T16:00:00Z",
    "cmdline": ["python", "-m", "aurite.bin.api"]
  },
  {
    "name": "python",
    "pid": 12346,
    "status": "running",
    "cpu_percent": 0.5,
    "memory_percent": 0.8,
    "create_time": "2025-01-09T16:00:05Z",
    "cmdline": ["python", "weather_server.py"]
  }
]
```

### Health Check

#### Comprehensive Health Check

```http
GET /system/health
```

Performs a comprehensive health check of all system components.

**Response (Healthy):**

```json
{
  "status": "healthy",
  "timestamp": "2025-01-09T16:45:00Z",
  "components": {
    "api": {
      "status": "healthy",
      "uptime": 3600.5
    },
    "config_manager": {
      "status": "healthy",
      "project_root": "/home/user/aurite-project",
      "cache_enabled": true
    },
    "mcp_host": {
      "status": "healthy",
      "registered_servers": 3,
      "available_tools": 15
    },
    "execution_facade": {
      "status": "healthy",
      "ready": true
    },
    "database": {
      "status": "healthy",
      "type": "sqlite"
    }
  },
  "issues": []
}
```

**Response (Degraded):**

```json
{
  "status": "degraded",
  "timestamp": "2025-01-09T16:45:00Z",
  "components": {
    "api": {
      "status": "healthy",
      "uptime": 3600.5
    },
    "config_manager": {
      "status": "healthy",
      "project_root": "/home/user/aurite-project",
      "cache_enabled": true
    },
    "mcp_host": {
      "status": "degraded",
      "error": "MCPHost not initialized"
    },
    "execution_facade": {
      "status": "healthy",
      "ready": true
    },
    "database": {
      "status": "healthy",
      "type": "sqlite"
    }
  },
  "issues": ["MCPHost not initialized"]
}
```

## Error Handling

### Common Error Responses

#### 401 Unauthorized

Missing or invalid API key:

```json
{
  "detail": "API key required either in X-API-Key header or as 'api_key' query parameter for streaming endpoints."
}
```

#### 403 Forbidden

Invalid API key:

```json
{
  "detail": "Invalid API Key"
}
```

#### 500 Internal Server Error

System operation failures:

```json
{
  "detail": "Failed to get system info: [error details]"
}
```

## Implementation Notes

### Graceful Degradation

The system routes are designed to work with or without optional dependencies:

1. **psutil**: When not available, metrics fallback to basic Python resource module
2. **ML dependencies**: Capabilities endpoint reports availability of pandas, sentence_transformers
3. **Storage backends**: Reports which backends are actually available

### Security Considerations

1. **Environment Variables**:

   - Sensitive patterns are automatically detected and masked
   - Only non-sensitive variables can be updated via API
   - Patterns include: KEY, SECRET, PASSWORD, TOKEN, CREDENTIAL, AUTH, PRIVATE

2. **System Information**:

   - No sensitive system details are exposed
   - Process command lines may contain sensitive data - use with caution

3. **Log Streaming**:
   - Logs may contain sensitive information
   - Ensure proper access controls are in place
   - Consider filtering sensitive data before streaming

### Performance Optimization

1. **Metrics Collection**:

   - CPU percent uses 0.1s interval to get accurate reading
   - Process metrics are collected for current process and children only
   - Consider caching metrics if called frequently

2. **Dependency Listing**:

   - Can be slow with many packages installed
   - Results are sorted for consistency
   - Consider caching if called frequently

3. **Log Streaming**:
   - Uses queue with max size to prevent memory issues
   - Heartbeat every 1 second to keep connection alive
   - Handler is properly removed on disconnect

## Testing & Debugging

### Example Test Script

```python
import httpx
import asyncio
import json

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"

async def test_system_routes():
    async with httpx.AsyncClient() as client:
        headers = {"X-API-Key": API_KEY}

        # 1. Get system info
        response = await client.get(f"{BASE_URL}/system/info", headers=headers)
        print(f"System Info: {json.dumps(response.json(), indent=2)}")

        # 2. Get framework version
        response = await client.get(f"{BASE_URL}/system/version", headers=headers)
        print(f"Framework Version: {response.json()}")

        # 3. Check capabilities
        response = await client.get(f"{BASE_URL}/system/capabilities", headers=headers)
        capabilities = response.json()
        print(f"Optional features: {capabilities['optional_features']}")

        # 4. List environment (first 5)
        response = await client.get(f"{BASE_URL}/system/environment", headers=headers)
        env_vars = response.json()[:5]
        print(f"Environment (first 5): {env_vars}")

        # 5. Check dependency health
        response = await client.post(
            f"{BASE_URL}/system/dependencies/check",
            headers=headers
        )
        health = response.json()
        failed = [d for d in health if not d["installed"]]
        print(f"Missing dependencies: {[d['name'] for d in failed]}")

        # 6. Get metrics
        response = await client.get(
            f"{BASE_URL}/system/monitoring/metrics",
            headers=headers
        )
        metrics = response.json()
        print(f"CPU: {metrics['cpu_percent']}%, Memory: {metrics['memory_usage']['percent']}%")

        # 7. Health check
        response = await client.get(f"{BASE_URL}/system/health", headers=headers)
        health = response.json()
        print(f"System health: {health['status']}")
        if health['issues']:
            print(f"Issues: {health['issues']}")

asyncio.run(test_system_routes())
```

### Streaming Logs Example

```python
import httpx
import json

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"

def stream_logs():
    headers = {"X-API-Key": API_KEY}

    with httpx.stream("GET", f"{BASE_URL}/system/monitoring/logs", headers=headers) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])  # Skip "data: " prefix
                    if data['type'] == 'log':
                        print(f"LOG: {data['message']}")
                    elif data['type'] == 'heartbeat':
                        print(f"HEARTBEAT: {data['timestamp']}")
                except json.JSONDecodeError:
                    pass

stream_logs()
```

### Common Issues and Solutions

#### Missing psutil

**Issue**: Metrics show 0% for CPU/memory
**Solution**: Install psutil for detailed metrics: `pip install psutil`

#### Environment Variable Not Updating

**Issue**: PUT /environment returns error for certain variables
**Solution**: Only non-sensitive variables can be updated. Check the error message for details.

#### Log Stream Disconnects

**Issue**: SSE connection drops after some time
**Solution**: Implement reconnection logic in client. The server sends heartbeats to detect disconnections.

## Best Practices

### Monitoring

1. **Health Checks**: Run periodic health checks to monitor system status
2. **Metrics Collection**: Collect metrics at reasonable intervals (e.g., every 30s)
3. **Log Streaming**: Use for debugging, not for production log aggregation
4. **Process Monitoring**: Check active processes when debugging resource issues

### Security

1. **Environment Variables**: Never log or expose sensitive environment variables
2. **Access Control**: Restrict system endpoints to admin users only
3. **Log Filtering**: Consider filtering sensitive data from log streams
4. **Metrics Access**: Be cautious about exposing detailed system metrics

### Performance

1. **Caching**: Cache relatively static data (version, capabilities)
2. **Throttling**: Implement rate limiting for expensive operations
3. **Async Operations**: All endpoints are async for better performance
4. **Resource Cleanup**: Ensure SSE connections are properly closed

## Integration Examples

### Dashboard Integration

```javascript
// Real-time system dashboard
class SystemDashboard {
  constructor(apiKey, baseUrl) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.metrics = {};
  }

  async updateMetrics() {
    const response = await fetch(`${this.baseUrl}/system/monitoring/metrics`, {
      headers: { "X-API-Key": this.apiKey },
    });
    this.metrics = await response.json();
    this.renderMetrics();
  }

  startLogStream() {
    const eventSource = new EventSource(
      `${this.baseUrl}/system/monitoring/logs`,
      { headers: { "X-API-Key": this.apiKey } }
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "log") {
        this.addLogEntry(data.message);
      }
    };
  }

  async checkHealth() {
    const response = await fetch(`${this.baseUrl}/system/health`, {
      headers: { "X-API-Key": this.apiKey },
    });
    const health = await response.json();
    this.updateHealthStatus(health);
  }
}
```

### Monitoring Script

```python
# System monitoring script
import asyncio
import httpx
from datetime import datetime

class SystemMonitor:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}

    async def monitor_loop(self):
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    # Check health
                    health = await self.check_health(client)
                    if health['status'] != 'healthy':
                        await self.alert_unhealthy(health)

                    # Get metrics
                    metrics = await self.get_metrics(client)
                    if metrics['cpu_percent'] > 80:
                        await self.alert_high_cpu(metrics)

                    # Check critical dependencies
                    deps = await self.check_dependencies(client)
                    missing = [d for d in deps if not d['installed']]
                    if missing:
                        await self.alert_missing_deps(missing)

                except Exception as e:
                    print(f"Monitor error: {e}")

                await asyncio.sleep(60)  # Check every minute

    async def check_health(self, client):
        response = await client.get(
            f"{self.base_url}/system/health",
            headers=self.headers
        )
        return response.json()

    async def get_metrics(self, client):
        response = await client.get(
            f"{self.base_url}/system/monitoring/metrics",
            headers=self.headers
        )
        return response.json()
```

## Related Documentation

- [API Reference](../api_reference.md) - Complete API overview
- [Configuration Manager Routes](./config_manager_routes.md) - Configuration management
- [MCP Host Routes](./mcp_host_routes.md) - Tool and server management
- [Execution Facade Routes](./facade_routes.md) - Agent execution endpoints
