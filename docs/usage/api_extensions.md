# Aurite API Extensions

Aurite supports custom API extensions that allow you to add your own endpoints to the built-in API server. This feature is inspired by [txtai's extension system](https://neuml.github.io/txtai/) and provides a clean, pythonic way to extend the API.

## Overview

Extensions are useful for:

- Creating custom workflows that combine multiple Aurite components
- Exposing domain-specific business logic as API endpoints
- Integrating Aurite with your existing systems
- Building specialized agent orchestration patterns

## Quick Start

### 1. Create an Extension

Create a Python file with your extension class:

```python
# my_extension.py
from fastapi import APIRouter, Security
from aurite.bin.api import Extension, application
from aurite.bin.dependencies import get_api_key


class MyExtension(Extension):
    """My custom extension."""

    def __call__(self, app):
        router = APIRouter(prefix="/custom", tags=["Custom"])

        @router.get("/hello")
        def hello(api_key: str = Security(get_api_key)):
            aurite = application.get()
            return {"message": "Hello from my extension!"}

        app.include_router(router)
```

### 2. Load the Extension

Set the `AURITE_API_EXTENSIONS` environment variable:

```bash
export AURITE_API_EXTENSIONS="my_extension.MyExtension"
```

Or add it to your `.env` file:

```env
AURITE_API_EXTENSIONS=my_extension.MyExtension
```

### 3. Start the API

```bash
aurite api start
```

Your custom endpoint will now be available at `http://localhost:8000/custom/hello`

## Extension Anatomy

### Base Extension Class

All extensions must inherit from the `Extension` base class:

```python
from aurite.bin.api import Extension

class MyExtension(Extension):
    def __call__(self, app):
        """
        Called when the extension is loaded.

        Args:
            app: The FastAPI application instance
        """
        # Register your routes here
        pass
```

### Accessing Aurite Components

Extensions can access the Aurite instance and all its components:

```python
from aurite.bin.api import application

# Inside your endpoint function
aurite = application.get()

# Access components
config_manager = aurite.get_config_manager()
host = aurite.kernel.host
engine = aurite.kernel.execution
```

### Using Dependency Injection

Extensions can use all Aurite's FastAPI dependencies:

```python
from fastapi import Depends, Security
from aurite.bin.dependencies import (
    get_api_key,           # API authentication
    get_config_manager,    # Configuration access
    get_execution_facade,  # Agent execution
    get_host,              # MCP Host
    get_session_manager,   # Session management
)

@router.get("/my-endpoint")
async def my_endpoint(
    api_key: str = Security(get_api_key),
    config_manager = Depends(get_config_manager),
    engine = Depends(get_execution_facade)
):
    # Your logic here
    pass
```

## Common Patterns

### Pattern 1: Custom RAG Endpoint

```python
from fastapi import APIRouter, Depends, Query, Security
from aurite.bin.api import Extension
from aurite.bin.dependencies import get_api_key, get_execution_facade


class RAGExtension(Extension):
    def __call__(self, app):
        router = APIRouter(prefix="/rag", tags=["RAG"])

        @router.get("/query")
        async def rag_query(
            question: str = Query(...),
            api_key: str = Security(get_api_key),
            engine = Depends(get_execution_facade)
        ):
            result = await engine.run_agent(
                agent_name="rag_agent",
                user_message=question
            )
            return {
                "question": question,
                "answer": result.final_output
            }

        app.include_router(router)
```

### Pattern 2: Batch Processing

```python
from fastapi import APIRouter, Depends, Security
from pydantic import BaseModel
from aurite.bin.api import Extension
from aurite.bin.dependencies import get_api_key, get_execution_facade


class BatchRequest(BaseModel):
    agent_name: str
    queries: list[str]


class BatchExtension(Extension):
    def __call__(self, app):
        router = APIRouter(prefix="/batch", tags=["Batch"])

        @router.post("/process")
        async def batch_process(
            request: BatchRequest,
            api_key: str = Security(get_api_key),
            engine = Depends(get_execution_facade)
        ):
            results = []
            for query in request.queries:
                result = await engine.run_agent(
                    agent_name=request.agent_name,
                    user_message=query
                )
                results.append({
                    "query": query,
                    "answer": result.final_output
                })
            return {"results": results}

        app.include_router(router)
```

### Pattern 3: Custom Workflow Orchestration

```python
from fastapi import APIRouter, Depends, Security
from aurite.bin.api import Extension, application
from aurite.bin.dependencies import get_api_key


class WorkflowExtension(Extension):
    def __call__(self, app):
        router = APIRouter(prefix="/workflow", tags=["Workflow"])

        @router.post("/multi-agent")
        async def multi_agent_workflow(
            task: str,
            api_key: str = Security(get_api_key)
        ):
            aurite = application.get()
            engine = aurite.kernel.execution

            # Step 1: Research agent
            research = await engine.run_agent(
                agent_name="research_agent",
                user_message=f"Research: {task}"
            )

            # Step 2: Analysis agent (uses research output)
            analysis = await engine.run_agent(
                agent_name="analysis_agent",
                user_message=f"Analyze: {research.final_output}"
            )

            # Step 3: Summary agent
            summary = await engine.run_agent(
                agent_name="summary_agent",
                user_message=f"Summarize: {analysis.final_output}"
            )

            return {
                "task": task,
                "research": research.final_output,
                "analysis": analysis.final_output,
                "summary": summary.final_output
            }

        app.include_router(router)
```

## Loading Multiple Extensions

You can load multiple extensions by separating them with commas:

```bash
export AURITE_API_EXTENSIONS="pkg1.Extension1,pkg2.Extension2,pkg3.Extension3"
```

Extensions are loaded in order. If one fails to load, the others will still be loaded (the error will be logged).

## Extension Module Paths

Extensions can be specified using Python module paths:

1. **Full path with class name:**

   ```
   my_package.extensions.MyExtension
   ```

2. **Module path only (will look for class named "Extension"):**

   ```
   my_package.extensions
   ```

3. **Relative imports work if the module is in your Python path:**
   ```
   ..extensions.custom
   ```

## API Documentation Integration

All endpoints defined in extensions automatically appear in:

- Swagger UI: `http://localhost:8000/api-docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI schema: `http://localhost:8000/openapi.json`

Make sure to:

- Add proper docstrings to your endpoints
- Use FastAPI's `tags` parameter to organize endpoints
- Define Pydantic models for request/response bodies

## Security Considerations

### Authentication

Always use the `get_api_key` security dependency for protected endpoints:

```python
from fastapi import Security
from aurite.bin.dependencies import get_api_key

@router.get("/protected")
async def protected_endpoint(api_key: str = Security(get_api_key)):
    # Only accessible with valid API key
    pass
```

### Public Endpoints

If you need public endpoints (no authentication), simply omit the security dependency:

```python
@router.get("/public")
async def public_endpoint():
    # Accessible without API key
    return {"message": "public"}
```

### CORS

Extensions inherit the API's CORS configuration. Endpoints will respect the `ALLOWED_ORIGINS` setting.

## Error Handling

Extensions should handle errors gracefully:

```python
from fastapi import HTTPException

@router.get("/data")
async def get_data(item_id: str):
    try:
        # Your logic
        result = await some_operation(item_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")
```

## Testing Extensions

### Manual Testing

1. Start the API with your extension loaded
2. Visit `http://localhost:8000/api-docs` to see your endpoints
3. Test using the interactive Swagger UI

### Programmatic Testing

```python
from fastapi.testclient import TestClient
from aurite.bin.api import app

# Set environment variable before importing
import os
os.environ["AURITE_API_EXTENSIONS"] = "my_extension.MyExtension"

client = TestClient(app)

def test_my_endpoint():
    response = client.get("/custom/hello")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello!"
```

## Best Practices

1. **Naming Conventions**

   - Use clear, descriptive class names: `RAGExtension`, `BatchProcessingExtension`
   - Use semantic URL prefixes: `/rag`, `/batch`, `/workflow`
   - Group related endpoints with tags

2. **Documentation**

   - Add docstrings to all endpoints
   - Use Pydantic models for complex request/response types
   - Include example values in schema

3. **Error Handling**

   - Always handle exceptions gracefully
   - Return meaningful error messages
   - Use appropriate HTTP status codes

4. **Performance**

   - Use async/await for I/O operations
   - Consider caching for expensive operations
   - Be mindful of resource usage

5. **Organization**
   - Keep extensions focused on a single responsibility
   - Break large extensions into multiple smaller ones
   - Use separate files for complex extensions

## Example: Complete Extension

See [`docs/usage/example_extension.py`](./example_extension.py) for a complete, working example that demonstrates:

- Multiple endpoints
- Dependency injection
- Agent execution
- Batch processing
- Error handling

## Troubleshooting

### Extension Not Loading

Check the API logs for error messages:

```
✗ Failed to load extension 'my_extension.MyExtension': No module named 'my_extension'
```

Common issues:

- Module not in Python path
- Typo in module/class name
- Extension class doesn't inherit from `Extension`

### Import Errors

Ensure all dependencies are installed:

```bash
pip install aurite[api]
```

### Runtime Errors

Check that:

- `application.get()` is called inside endpoint functions (not at module level)
- All required dependencies are injected
- Async functions use `await` for async operations

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Aurite API Reference](./api_reference.md)
- [Example Extension](./example_extension.py)
- [txtai Extensions](https://neuml.github.io/txtai/embeddings/configuration/extensions/)
