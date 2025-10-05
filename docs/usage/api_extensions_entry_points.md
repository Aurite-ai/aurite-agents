# Creating Distributable API Extensions with Entry Points

This guide shows how to create **pip-installable** Aurite API extensions using Poetry entry points. This is the recommended approach for creating professional, distributable extensions.

## Why Use Entry Points?

**Benefits:**

- ✅ **Auto-discovery**: Extensions automatically found when installed
- ✅ **Standard Python pattern**: Uses ecosystem-standard plugin system
- ✅ **No configuration needed**: Just `pip install my-aurite-extension`
- ✅ **Version management**: `pip install aurite-rag-extension==1.2.0`
- ✅ **Dependencies**: Extensions can declare their own dependencies
- ✅ **Professional packaging**: Proper Python package structure

## Quick Example

### Extension Package Structure

```
my-aurite-extension/
├── pyproject.toml          # Package configuration with entry point
├── README.md
├── src/
│   └── my_aurite_ext/
│       ├── __init__.py
│       └── extension.py    # Your extension code
└── tests/
    └── test_extension.py
```

### 1. Create Your Extension

**File: `src/my_aurite_ext/extension.py`**

```python
from fastapi import APIRouter, Security, Depends
from aurite.bin.api.extension import Extension, application
from aurite.bin.dependencies import get_api_key, get_execution_facade


class RAGExtension(Extension):
    """
    Custom RAG extension for Aurite.

    Provides a /rag endpoint for retrieval-augmented generation queries.
    """

    def __call__(self, app):
        router = APIRouter(prefix="/rag", tags=["RAG"])

        @router.get("/query")
        async def rag_query(
            question: str,
            agent_name: str = "rag_agent",
            api_key: str = Security(get_api_key),
            engine = Depends(get_execution_facade)
        ):
            """Execute a RAG query using the specified agent."""
            result = await engine.run_agent(
                agent_name=agent_name,
                user_message=question
            )
            return {
                "question": question,
                "answer": result.final_output,
                "agent": agent_name
            }

        app.include_router(router)
```

**File: `src/my_aurite_ext/__init__.py`**

```python
from .extension import RAGExtension

__all__ = ["RAGExtension"]
```

### 2. Configure Entry Point in pyproject.toml

```toml
[project]
name = "my-aurite-extension"
version = "1.0.0"
description = "RAG extension for Aurite API"
authors = [{name = "Your Name", email = "you@example.com"}]
requires-python = ">=3.11"
dependencies = [
    "aurite>=0.3.0",  # Your extension depends on Aurite
]

# Register the entry point for auto-discovery
[project.entry-points."aurite.api.extension"]
rag = "my_aurite_ext.extension:RAGExtension"
```

**Entry Point Breakdown:**

- `aurite.api.extension` - The group name (standard for all Aurite extensions)
- `rag` - Your extension's unique name
- `my_aurite_ext.extension:RAGExtension` - Path to your Extension class

### 3. Install and Use

```bash
# Install your extension
pip install my-aurite-extension

# Start Aurite - extension is automatically discovered!
aurite api start
```

Your extension is now available at `http://localhost:8000/rag/query`

---

## Complete Working Example

Here's a complete, production-ready extension package:

### pyproject.toml

```toml
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "aurite-analytics-extension"
version = "1.0.0"
description = "Analytics and monitoring extension for Aurite API"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
license = "MIT"
keywords = ["aurite", "extension", "analytics"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.11",
]

[tool.poetry.dependencies]
python = "^3.11"
aurite = "^0.3.0"
prometheus-client = "^0.19.0"  # Example additional dependency

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.0.0"
ruff = "^0.1.0"

# Entry point registration
[tool.poetry.plugins."aurite.api.extension"]
analytics = "aurite_analytics_ext.extension:AnalyticsExtension"
```

### Extension Code

**File: `src/aurite_analytics_ext/extension.py`**

```python
from fastapi import APIRouter, Security
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from aurite.bin.api.extension import Extension, application
from aurite.bin.dependencies import get_api_key


# Prometheus metrics
api_requests = Counter('aurite_api_requests_total', 'Total API requests')
agent_executions = Counter('aurite_agent_executions_total', 'Total agent executions', ['agent_name'])


class AnalyticsExtension(Extension):
    """
    Analytics and monitoring extension.

    Provides:
    - Prometheus metrics endpoint
    - Request counting
    - Agent execution tracking
    """

    def __call__(self, app):
        router = APIRouter(prefix="/analytics", tags=["Analytics"])

        @router.get("/metrics")
        def metrics():
            """Prometheus metrics endpoint."""
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

        @router.get("/stats")
        async def stats(api_key: str = Security(get_api_key)):
            """Get current statistics."""
            aurite = application.get()
            config_manager = aurite.get_config_manager()

            return {
                "total_agents": len(config_manager.list_configs("agent")),
                "total_workflows": len(config_manager.list_configs("linear_workflow")),
                "total_mcp_servers": len(config_manager.list_configs("mcp_server")),
            }

        # Add middleware to count requests
        @app.middleware("http")
        async def count_requests(request, call_next):
            api_requests.inc()
            response = await call_next(request)
            return response

        app.include_router(router)
```

---

## Publishing Your Extension

### 1. Build the Package

```bash
poetry build
```

This creates files in `dist/`:

- `my-aurite-extension-1.0.0.tar.gz`
- `my_aurite_extension-1.0.0-py3-none-any.whl`

### 2. Test Locally

```bash
# Install in editable mode for development
pip install -e .

# Start Aurite to test
aurite api start
```

### 3. Publish to PyPI

```bash
# Configure PyPI credentials
poetry config pypi-token.pypi <your-token>

# Publish
poetry publish
```

### 4. Users Install

```bash
pip install my-aurite-extension
aurite api start
```

---

## Hybrid Loading: Entry Points + Environment Variables

Aurite supports **both** methods simultaneously:

```bash
# Entry points load automatically
pip install aurite-rag-extension aurite-analytics-extension

# Plus manual/local extensions via env var
export AURITE_API_EXTENSIONS="./local_dev_extension.MyExtension"

# Both types load together!
aurite api start
```

**Loading Order:**

1. Entry points (installed packages) - discovered automatically
2. Environment variable (manual/local) - for development/testing
3. Duplicates skipped (env var takes precedence)

---

## Best Practices

### Naming Conventions

**Package Name:**

```
aurite-<功能>-extension
```

Examples: `aurite-rag-extension`, `aurite-analytics-extension`

**Entry Point Name:**

```
<short-descriptive-name>
```

Examples: `rag`, `analytics`, `monitoring`

**Module Name:**

```
aurite_<功能>_ext
```

Examples: `aurite_rag_ext`, `aurite_analytics_ext`

### Version Compatibility

Specify compatible Aurite versions:

```toml
[tool.poetry.dependencies]
aurite = "^0.3.0"  # Compatible with 0.3.x
```

### Dependencies

Declare all dependencies explicitly:

```toml
[tool.poetry.dependencies]
python = "^3.11"
aurite = "^0.3.0"
redis = "^5.0.0"     # If you use Redis
pandas = "^2.0.0"     # If you use Pandas
```

### Testing

Include tests for your extension:

```python
# tests/test_extension.py
from fastapi.testclient import TestClient
from aurite.bin.api import app
from my_aurite_ext.extension import RAGExtension

def test_extension_loads():
    ext = RAGExtension()
    ext(app)

    client = TestClient(app)
    response = client.get("/rag/query?question=test")
    assert response.status_code in [200, 401]  # 401 if auth required
```

### Documentation

Include clear README:

````markdown
# My Aurite Extension

Brief description of what your extension does.

## Installation

```bash
pip install my-aurite-extension
```
````

## Usage

```bash
aurite api start
```

Your endpoints are now available at:

- `/your-endpoint` - Description

## Configuration

Optional environment variables:

- `MY_EXT_OPTION` - Description

````

---

## Listing Available Extensions

Users can list all installed extensions:

```python
from aurite.bin.api.extension import list_available_extensions

# Get all available extensions
extensions = list_available_extensions()
print(f"Available extensions: {extensions}")
````

Or programmatically discover them:

```python
from aurite.bin.api.extension import discover_entry_point_extensions

# Get extension classes
discovered = discover_entry_point_extensions()
for name, ext_class in discovered.items():
    print(f"{name}: {ext_class.__doc__}")
```

---

## Comparison: Entry Points vs Environment Variable

| Feature             | Entry Points        | Environment Variable |
| ------------------- | ------------------- | -------------------- |
| **Installation**    | `pip install`       | Local file/path      |
| **Distribution**    | PyPI/private repos  | Copy files           |
| **Auto-discovery**  | Yes                 | No                   |
| **Configuration**   | pyproject.toml      | `.env` or shell      |
| **Version control** | pip versions        | Git/manual           |
| **Dependencies**    | Declared in package | Manual install       |
| **Use Case**        | Production, sharing | Development, testing |

**Recommendation:** Use entry points for production and distribution, environment variables for local development.

---

## Troubleshooting

### Extension Not Discovered

**Check installation:**

```bash
pip list | grep aurite
```

**Verify entry point:**

```python
from importlib.metadata import entry_points

eps = entry_points()
# Python 3.10+
aurite_exts = eps.select(group='aurite.api.extension')
# Python 3.9
aurite_exts = eps.get('aurite.api.extension', [])

for ep in aurite_exts:
    print(f"{ep.name}: {ep.value}")
```

### Circular Import Errors

Remember to import from the extension submodule:

```python
# ✅ Correct
from aurite.bin.api.extension import Extension, application

# ❌ Wrong - causes circular import
from aurite.bin.api import Extension
```

### Version Conflicts

Check Aurite version compatibility:

```bash
pip show aurite
pip show my-aurite-extension
```

---

## Example Extension Packages

Here are some example extension packages you could create:

1. **aurite-monitoring-extension** - Prometheus metrics, health checks
2. **aurite-auth-extension** - OAuth2, JWT authentication
3. **aurite-cache-extension** - Redis caching for agent responses
4. **aurite-webhook-extension** - Webhook endpoints for external systems
5. **aurite-export-extension** - Export execution history, analytics
6. **aurite-scheduler-extension** - Scheduled agent/workflow execution

Each would be pip-installable and auto-discovered!

---

## Next Steps

1. Create your extension following the structure above
2. Test locally with `pip install -e .`
3. Publish to PyPI with `poetry publish`
4. Share with the community!

For more examples, see:

- [Basic Extension Guide](./api_extensions.md)
- [Example Extension Code](./example_extension.py)
